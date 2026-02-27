#!/usr/bin/env python3
"""
inbox.py — Mnemo Muse Inbox: capture, sort, inject, and lifecycle-manage
           pedagogical quick-captures for muse agents.

CLI usage:
    python inbox.py prep      --muse-dir DIR --limit N --inject-out FILE --ids-out FILE
    python inbox.py done      --muse-dir DIR --ids ID1 ID2 ...
    python inbox.py capture   --muse-dir DIR --text TEXT --lifecycle L --priority P --source S
    python inbox.py list      --muse-dir DIR
    python inbox.py show      --muse-dir DIR --id ID
    python inbox.py set-status --muse-dir DIR --id ID --status STATUS
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── Frontmatter parser (stdlib-only) ─────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (fields_dict, body_text). Returns ({}, text) if no frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw_fm, body = m.group(1), m.group(2)
    fields: dict = {}
    for line in raw_fm.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "[]":
            fields[key] = []
        else:
            # Try integer
            try:
                fields[key] = int(val)
            except ValueError:
                fields[key] = val
    return fields, body


def _render_frontmatter(fields: dict) -> str:
    """Render fields dict back to YAML frontmatter block."""
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, list):
            lines.append(f"{k}: []")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _rewrite_frontmatter_field(path: Path, key: str, value) -> None:
    """Read file, update one frontmatter field, write back."""
    text = path.read_text(encoding="utf-8")
    fields, body = _parse_frontmatter(text)
    fields[key] = value
    path.write_text(_render_frontmatter(fields) + body, encoding="utf-8")


# ── InboxItem ─────────────────────────────────────────────────────────────────

@dataclass
class InboxItem:
    path: Path
    fields: dict
    body: str

    @property
    def item_id(self) -> str:
        return self.path.stem

    @property
    def title(self) -> str:
        """First heading line from body, or item_id as fallback."""
        for line in self.body.splitlines():
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip()
        return self.item_id

    @property
    def priority(self) -> str:
        return str(self.fields.get("priority", "P3"))

    @property
    def priority_int(self) -> int:
        p = self.priority
        if p == "P1":
            return 1
        if p == "P2":
            return 2
        return 3

    @property
    def date(self) -> str:
        return str(self.fields.get("date", ""))

    @property
    def session_count(self) -> int:
        return int(self.fields.get("session_count", 0))

    @property
    def lifecycle(self) -> str:
        return str(self.fields.get("lifecycle", "durable"))

    @property
    def status(self) -> str:
        return str(self.fields.get("status", "active"))

    def sort_key(self):
        # priority ASC, date ASC, session_count DESC
        return (self.priority_int, self.date, -self.session_count)


# ── Core functions ────────────────────────────────────────────────────────────

def _inbox_dir(muse_dir: str) -> Path:
    return Path(muse_dir) / "inbox"


def scan_inbox(muse_dir: str, status: str = "active") -> list[InboxItem]:
    """Return items with the given status, sorted by (priority, date, -sessions)."""
    d = _inbox_dir(muse_dir)
    if not d.is_dir():
        return []
    items = []
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("."):
            continue
        text = p.read_text(encoding="utf-8")
        fields, body = _parse_frontmatter(text)
        item = InboxItem(path=p, fields=fields, body=body)
        if item.status == status:
            items.append(item)
    return sorted(items, key=lambda i: i.sort_key())


def prep_injection(
    muse_dir: str,
    limit: int,
    inject_out_path: str,
    ids_out_path: str,
) -> int:
    """
    Write formatted Markdown to inject_out_path and space-separated IDs to
    ids_out_path. Returns count of items written (0 if inbox empty).
    """
    items = scan_inbox(muse_dir)[:limit]
    if not items:
        return 0

    lines = [
        "# Mnemo Inbox — Items for This Session",
        "",
        "The following items were captured for your consideration during artifact",
        "generation. Look for natural opportunities to address them; do not force them.",
        "",
    ]
    for item in items:
        sc = item.session_count
        session_label = f"{sc} session{'s' if sc != 1 else ''}"
        header = f"## [{item.priority} · {item.lifecycle} · {session_label}] {item.title}"
        lines.append(header)
        lines.append("")
        lines.append(item.body.strip())
        lines.append("")

    Path(inject_out_path).write_text("\n".join(lines), encoding="utf-8")
    Path(ids_out_path).write_text(
        " ".join(i.item_id for i in items), encoding="utf-8"
    )
    return len(items)


def done_injection(muse_dir: str, ids: list[str]) -> None:
    """
    Increment session_count on each item. Auto-archive ephemeral items
    whose session_count >= 1 after increment.
    """
    d = _inbox_dir(muse_dir)
    for item_id in ids:
        # Find the file — item_id is the stem
        matches = list(d.glob(f"{item_id}.md"))
        if not matches:
            continue
        p = matches[0]
        text = p.read_text(encoding="utf-8")
        fields, body = _parse_frontmatter(text)
        new_count = int(fields.get("session_count", 0)) + 1
        fields["session_count"] = new_count
        # Auto-archive ephemeral items after first injection
        if fields.get("lifecycle", "durable") == "ephemeral" and new_count >= 1:
            fields["status"] = "archived"
        p.write_text(_render_frontmatter(fields) + body, encoding="utf-8")


def capture_item(
    muse_dir: str,
    text: str,
    lifecycle: str = "durable",
    priority: str = "P2",
    source: str = "cli",
) -> Path:
    """Create a new inbox item file. Returns the path of the created file."""
    d = _inbox_dir(muse_dir)
    d.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")

    # Derive slug from first line of text (first 4 words)
    first_line = text.strip().splitlines()[0] if text.strip() else "note"
    words = re.sub(r"[^\w\s]", "", first_line).split()[:4]
    slug = "_".join(w.lower() for w in words) if words else "note"
    filename = f"{timestamp}_{slug}.md"

    # Derive muse name from directory
    muse_name = Path(muse_dir).name.lower()

    fields = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "muse": muse_name,
        "lifecycle": lifecycle,
        "status": "active",
        "priority": priority,
        "session_count": 0,
        "source": source,
        "tags": [],
    }

    # Body: title is first line; rest is body
    lines = text.strip().splitlines()
    title = lines[0]
    rest = "\n".join(lines[1:]).strip()
    body_lines = [f"# {title}", ""]
    if rest:
        body_lines.append(rest)

    content = _render_frontmatter(fields) + "\n".join(body_lines) + "\n"
    p = d / filename
    p.write_text(content, encoding="utf-8")
    return p


def set_status(muse_dir: str, item_id: str, status: str) -> None:
    """Update the status field of an inbox item."""
    d = _inbox_dir(muse_dir)
    matches = list(d.glob(f"{item_id}.md"))
    if not matches:
        raise FileNotFoundError(f"inbox item not found: {item_id}")
    _rewrite_frontmatter_field(matches[0], "status", status)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cmd_prep(args) -> None:
    count = prep_injection(
        args.muse_dir, args.limit, args.inject_out, args.ids_out
    )
    if count:
        print(f"inbox: {count} item(s) prepared for injection", file=sys.stderr)


def _cmd_done(args) -> None:
    done_injection(args.muse_dir, args.ids)


def _cmd_capture(args) -> None:
    p = capture_item(
        args.muse_dir,
        args.text,
        lifecycle=args.lifecycle,
        priority=args.priority,
        source=args.source,
    )
    # Print relative path from muse_dir for friendly display
    try:
        rel = p.relative_to(Path(args.muse_dir).parent)
    except ValueError:
        rel = p
    print(f"Captured → {rel}")


def _cmd_list(args) -> None:
    items = scan_inbox(args.muse_dir)
    if not items:
        print("  (inbox empty — no active items)")
        return
    print(f"  {'ID':<32}  {'PRI':<4}  {'DATE':<12}  {'SC':<4}  TITLE")
    print(f"  {'-'*32}  {'-'*4}  {'-'*12}  {'-'*4}  -----")
    for item in items:
        sc = str(item.session_count)
        print(
            f"  {item.item_id:<32}  {item.priority:<4}  {item.date:<12}  {sc:<4}  {item.title}"
        )


def _cmd_show(args) -> None:
    d = _inbox_dir(args.muse_dir)
    matches = list(d.glob(f"{args.id}.md"))
    if not matches:
        print(f"inbox: item not found: {args.id}", file=sys.stderr)
        sys.exit(1)
    print(matches[0].read_text(encoding="utf-8"))


def _cmd_set_status(args) -> None:
    try:
        set_status(args.muse_dir, args.id, args.status)
        print(f"  {args.id} → status: {args.status}")
    except FileNotFoundError as e:
        print(f"inbox: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_count(args) -> None:
    """Print count of active items (for shell scripting)."""
    print(len(scan_inbox(args.muse_dir)))


def main() -> None:
    parser = argparse.ArgumentParser(prog="inbox.py", description="Mnemo Muse Inbox")
    sub = parser.add_subparsers(dest="command", required=True)

    # prep
    p_prep = sub.add_parser("prep", help="Prepare inbox injection for a chat session")
    p_prep.add_argument("--muse-dir", required=True)
    p_prep.add_argument("--limit", type=int, default=1)
    p_prep.add_argument("--inject-out", required=True)
    p_prep.add_argument("--ids-out", required=True)

    # done
    p_done = sub.add_parser("done", help="Post-session: increment session counts, auto-archive")
    p_done.add_argument("--muse-dir", required=True)
    p_done.add_argument("--ids", nargs="+", default=[])

    # capture
    p_cap = sub.add_parser("capture", help="Capture a new inbox item")
    p_cap.add_argument("--muse-dir", required=True)
    p_cap.add_argument("--text", required=True)
    p_cap.add_argument("--lifecycle", default="durable", choices=["durable", "ephemeral"])
    p_cap.add_argument("--priority", default="P2", choices=["P1", "P2", "P3"])
    p_cap.add_argument("--source", default="cli")

    # list
    p_list = sub.add_parser("list", help="List active inbox items")
    p_list.add_argument("--muse-dir", required=True)

    # show
    p_show = sub.add_parser("show", help="Show full content of an item")
    p_show.add_argument("--muse-dir", required=True)
    p_show.add_argument("--id", required=True)

    # set-status
    p_ss = sub.add_parser("set-status", help="Update status of an item")
    p_ss.add_argument("--muse-dir", required=True)
    p_ss.add_argument("--id", required=True)
    p_ss.add_argument("--status", required=True, choices=["active", "resolved", "archived"])

    # count (for shell scripting)
    p_cnt = sub.add_parser("count", help="Print count of active items")
    p_cnt.add_argument("--muse-dir", required=True)

    args = parser.parse_args()
    dispatch = {
        "prep": _cmd_prep,
        "done": _cmd_done,
        "capture": _cmd_capture,
        "list": _cmd_list,
        "show": _cmd_show,
        "set-status": _cmd_set_status,
        "count": _cmd_count,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()

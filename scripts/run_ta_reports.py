#!/usr/bin/env python3
"""Scheduled full-report sweeps for the TA bundles (C291 + SE1).

Kurt ruling 2026-11-15: he drives the downloads (new files or same-URL
resubmissions of past assignments, typically Monday mornings); this
sweep runs Fridays and Mondays at noon via the Hermes cron job
'ta-report-sweeps'. It re-runs EVERY known lane on each class share
against the share roster and regenerates report.html + TA-reports/ in
place (overwrite-with-timestamp; every lane run rebuilds the shared
index from ALL lane manifests).

The lane -> rubric map mirrors references/moj-batch-commands.md (SE1 MoJ
lanes) plus the greyfield/p465-set rubrics as they exist, and the c291
rubric set. Lanes with NO known rubric (the in-class ICEX_MJ checkpoint
lanes, pending the roster-driven repo-window checker) are SKIPPED with a
surfaced reason, never guessed. Lane dirs are discovered wherever they
sit: submissions/canvas/<lane> (SE1's 2026-11 layout) or flat
submissions/<lane> (C291 today) — a lane is any directory holding
*_link.html Canvas downloads.

Exit code 1 iff at least one lane FAILED; SKIP is expected and calm.
Run log: ~/.hermes/profiles/mnemo/cache/report-runs/<class>-<ts>.log
"""
import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys
import time

MNEMO = pathlib.Path("/Users/seiffert/devops/teaching/SE1/mnemo")
CHECKER = MNEMO / "tools" / "icex_checker" / "icex_checker.py"
PY = MNEMO / ".venv" / "bin" / "python"
RUNS_DIR = pathlib.Path.home() / ".hermes" / "profiles" / "mnemo" / "cache" / "report-runs"

SHARES = {
    "c291": pathlib.Path(
        "/Users/seiffert/Library/CloudStorage/OneDrive-IndianaUniversity/"
        "Teaching/C291 - C and UNIX/FA26-C291/submissions"),
    "se1": pathlib.Path(
        "/Users/seiffert/Library/CloudStorage/OneDrive-IndianaUniversity/"
        "Teaching/P465 - Project Management/FA26-P465/submissions"),
}
ROSTERS = {
    "c291": "FA26_C291_Roster.csv",
    "se1": "FA26_P465_Team_Roster_v2.csv",
}
# lane-name regex -> rubric filename template (rubrics/<class>/<file>)
MAPS = {
    "c291": [
        (re.compile(r"^ICEX(\d+)-fa26$"), "icex{0:02d}_fa26.yaml"),
        (re.compile(r"^PASN(\d+)-fa26$"), "pasn{0:02d}_fa26.yaml"),
        (re.compile(r"^WEVL(\d+)-fa26$"), "wevl{0:02d}_fa26.yaml"),
    ],
    "se1": [
        (re.compile(r"^A_MJ01-A$"), "a_mj01a_fa26.yaml"),
        (re.compile(r"^A_MJ01-B$"), "a_mj01b_fa26.yaml"),
        (re.compile(r"^A_MJ(\d+)$"), "a_mj{0:02d}_fa26.yaml"),
        (re.compile(r"^AGR_MJ0(\d)$"), "agr_mj0{0}_fa26.yaml"),
        (re.compile(r"^ICEX01-fa26$"), "team_icex01_fa26.yaml"),
        (re.compile(r"^ICEX02-fa26$"), "team_icex02_fa26.yaml"),
        (re.compile(r"^ICEX0(\d)-fa26$"), "icex0{0}_fa26.yaml"),
        (re.compile(r"^SR0(\d)-fa26$"), "sr_fa26.yaml"),
        (re.compile(r"^A01-fa26$"), "asn01_fa26.yaml"),
        (re.compile(r"^wk(\d+)_englog$"), "englog{int:02d}_fa26.yaml"),
        (re.compile(r"^wk(\d+)_team_pr$"), "team_pr_wk{0:02d}_fa26.yaml"),
    ],
}
SKIP_KNOWN = {
    # in-class ICEX_MJ checkpoint lanes: graded from the class+15-min
    # checkpoint window by the (still-to-build) repo-window checker,
    # not from Canvas downloads — surface, never guess (2026-11-02 ruling)
    re.compile(r"^ICEX-MJ\d+$"): "ICEX_MJ checkpoint lane — checker not built",
}
ENGLISH_SHIFT = 7   # wk08_englog <-> englog01 (verified mapping)


def discover_lanes(share):
    """Lane dirs = any subdir of share or share/canvas holding *_link.html."""
    seen = []
    for base in (share / "canvas", share):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if not d.is_dir() or d.name in seen:
                continue
            if d.name.endswith("-analyzed") or d.name in ("canvas", "TA-reports"):
                continue
            links = list(d.glob("*_link.html"))
            if links:
                seen.append(d)
    return seen


def rubric_for(cls, lane_name):
    """(rubric_path, None) or (None, skip_reason) — never guess."""
    path = pathlib.Path(lane_name).name
    for rx, needle in SKIP_KNOWN.items():
        if rx.match(path):
            return None, needle
    for rx, tmpl in MAPS[cls]:
        m = rx.match(path)
        if not m:
            continue
        args = tuple(int(g) if g.isdigit() else g for g in m.groups())
        kwargs = ({"int": int(m.group(1)) - ENGLISH_SHIFT}
                  if "{int:" in tmpl else {})
        rel = "rubrics/%s/%s" % (cls, tmpl.format(*args, **kwargs))
        cand = MNEMO / "tools" / "icex_checker" / rel
        if cand.is_file():
            return cand, None
        return None, "rubric file missing: %s" % rel
    return None, "no rubric known for lane"


def probe_readable(lane, probe=3):
    """Cheap OneDrive-placeholder check: 16-byte read of a few files."""
    for f in sorted(lane.glob("*_link.html"))[:probe]:
        try:
            with open(f, "rb") as fh:
                fh.read(16)
        except OSError:
            return False
    return True


def run_lane(cls, lane, rubric, logf, lane_timeout):
    share = SHARES[cls]
    cmd = [str(PY), str(CHECKER),
           "--batch", str(lane),
           "--rubric", str(rubric),
           "--roster", str(share / ROSTERS[cls]),
           "--html-out", str(share)]
    if not probe_readable(lane):
        print("WARN: cold (unreadable) files in %s — OneDrive placeholder; "
              "hydrate with the skill hydrate.swift script, then re-run "
              "this lane" % lane.name, file=logf)
    env = os.environ.copy()
    env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=str(MNEMO / "tools"), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace")
    html_lines = []
    try:
        for line in proc.stdout:
            logf.write(line.rstrip("\n") + "\n")
            logf.flush()
            if line.startswith("HTML:"):
                html_lines.append(line.strip())
        proc.wait(timeout=lane_timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return 124, [], time.time() - t0
    rc = proc.returncode
    return rc, html_lines, time.time() - t0


def sweep(cls, only, lane_timeout, logf):
    share = SHARES[cls]
    print("=== %s sweep — share %s" % (cls.upper(), share), file=logf)
    lanes = discover_lanes(share)
    if only:
        lanes = [d for d in lanes if d.name in only]
    if not lanes:
        print("no lanes discovered (or --only matched nothing)", file=logf)
        return []
    rows = []
    for lane in lanes:
        rubric, skip = rubric_for(cls, lane.name)
        n_links = len(list(lane.glob("*_link.html")))
        if skip:
            print("=== SKIP %s/%s (%d links) — %s"
                  % (cls, lane.name, n_links, skip), file=logf)
            rows.append({"cls": cls, "lane": lane.name, "rc": "SKIP",
                         "note": skip, "pages": "", "exc": "",
                         "status": "SKIP"})
            continue
        print("=== RUN %s/%s rubric=%s (%d links) start=%s"
              % (cls, lane.name, rubric.name, n_links,
                 datetime.datetime.now().strftime("%H:%M:%S")), file=logf)
        rc, html_lines, elapsed = run_lane(cls, lane, rubric, logf,
                                           lane_timeout)
        pages = exc = "?"
        for h in html_lines:
            m = re.search(r"\((\d+) pages, (\d+) exception\(s\)\)", h)
            if m:
                pages, exc = m.group(1), m.group(2)
        # rc=2 = per-file failures with the bundle WRITTEN (exception
        # rows surface them to the TA; a re-run can't fix student data)
        if rc == 0 or (rc == 2 and pages not in ("?", "0")):
            status = "PASS-EXC" if rc == 2 else "PASS"
        else:
            status = "FAIL"
        print("=== DONE %s/%s rc=%d %s (%.1f min) pages=%s exc=%s"
              % (cls, lane.name, rc, status, elapsed / 60.0, pages, exc),
              file=logf)
        rows.append({"cls": cls, "lane": lane.name, "rc": rc, "note": "",
                     "pages": pages, "exc": exc, "status": status})
    failed = sum(1 for r in rows if r["status"] == "FAIL")
    print("=== %s SUMMARY: %d lanes, %d failed, %d pass-exc, %d skipped"
          % (cls.upper(), len(rows), failed,
             sum(1 for r in rows if r["status"] == "PASS-EXC"),
             sum(1 for r in rows if r["rc"] == "SKIP")), file=logf)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--class", dest="cls", default="both",
                    choices=["c291", "se1", "both"])
    ap.add_argument("--only", action="append", default=[],
                    help="restrict to named lane(s); repeatable")
    ap.add_argument("--list", action="store_true",
                    help="discovery dry run: lanes + rubric assignment")
    ap.add_argument("--lane-timeout", type=int, default=1800,
                    help="per-lane subprocess timeout seconds")
    args = ap.parse_args()

    classes = ["c291", "se1"] if args.cls == "both" else [args.cls]
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    if args.list:
        for cls in classes:
            print("-- %s (%s):" % (cls.upper(), SHARES[cls]))
            for lane in discover_lanes(SHARES[cls]):
                rubric, skip = rubric_for(cls, lane.name)
                n = len(list(lane.glob("*_link.html")))
                state = "SKIP: " + skip if skip else rubric.name
                print("   %-14s %3d links  %s" % (lane.name, n, state))
        return 0
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RUNS_DIR / ("%s-%s.log" % ("+".join(classes), ts))
    all_rows = []
    with open(log_path, "w") as logf:
        for cls in classes:
            all_rows += sweep(cls, set(args.only) if args.only else None,
                              args.lane_timeout, logf)
    print("=== run log: %s" % log_path)
    print("%-10s %-16s %-6s %-9s %-7s %-5s %s" % (
        "class", "lane", "rc", "status", "pages", "exc", "note"))
    for r in all_rows:
        print("%-10s %-16s %-6s %-9s %-7s %-5s %s" % (
            r["cls"], r["lane"], str(r["rc"]), r["status"], r["pages"],
            r["exc"], r["note"]))
    failed = [r for r in all_rows if r["status"] == "FAIL"]
    print("=== FAILED LANES: %d" % len(failed))
    print("(rc=2 = per-file exceptions, surfaced in the bundle; "
          "only rc=0/2 lanes with pages are normal completions)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

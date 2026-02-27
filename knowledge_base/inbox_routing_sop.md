# Mnemo Inbox Routing SOP

How pedagogical quick-captures travel from Lore Forge into a muse agent's
session context.

---

## Overview

Two systems involved:

- **Lore Forge** — personal PKM (Obsidian vault). Quick ideas are captured here
  first, often on Vulcan/Faber during class or at events.
- **Mnemo Muse Inbox** — per-muse directory (`{Muse}/inbox/`) holding items
  that the muse agent will see automatically at `chat` time.

The connection is **manual by design** — no vault automation, no dependency on
Obsidian being open. A human runs one `capture` command and marks the Lore
Forge note processed.

---

## Routing a Lore Forge item to a muse

### 1. Lore Forge note has `assigned_to: Clio` (or Calliope, etc.)

The note appears in the inbox display with `→ Clio` in the Notes column.

### 2. Run `capture` in the Mnemo shell

```bash
capture --priority P3 "Explore Mentimeter for classroom use

Explore menti.com for live audience engagement. Saw it used at AI
pedagogy panel — word cloud to surface audience attitudes quickly.

Use cases: entry ticket, exit ticket, team health check in SE."
```

Defaults: `--lifecycle durable`, `--priority P2`, `--source cli`.

The `capture` command requires a persona to be set (`MNEMO_PERSONA`). If not
set, run `chat with clio` first (or set the persona alias).

### 3. Mark the Lore Forge note `processed: true`

Edit the frontmatter of the source note:
```yaml
processed: true
```

It will disappear from the inbox display on next query.

### 4. Item injects automatically at next `chat`

No further action needed. The item appears in the muse's context with:

```
## [P3 · durable · 0 sessions] Explore Mentimeter for classroom use
...
```

The muse looks for natural opportunities to reference it; does not force it.

---

## Muse inbox directories

| Muse | Inbox path | Status |
|------|-----------|--------|
| Clio (SE1) | `Clio/inbox/` | ✓ Active |
| Calliope (C291) | `Calliope/inbox/` | ✓ Active |

To add a new muse inbox: create `{Muse}/inbox/.gitkeep` in the mnemo repo.

---

## Lifecycle

| `lifecycle` | Behaviour |
|-------------|-----------|
| `durable` | Stays active across sessions; inject on every `chat` until resolved |
| `ephemeral` | Auto-archived after first injection (session_count ≥ 1) |

Use `ephemeral` for one-shot reminders. Use `durable` (default) for ideas to
surface repeatedly until tried or discarded.

---

## Item management

```bash
inbox                    # list active items
inbox show <id>          # full content
inbox resolve <id>       # tried it / acted on it
inbox archive <id>       # suppress without resolving
MNEMO_INBOX_LIMIT=3      # inject more items this session (default: 1)
```

---

## Edge cases

- **Typo in muse dir:** `capture` validates that the muse directory exists
  before creating the inbox subdir. An invalid path produces an error rather
  than silently creating a phantom directory.
- **No inbox dir yet:** `capture` auto-creates `{muse_dir}/inbox/` on first
  use, as long as the muse directory itself exists.
- **session_count drift:** If `session_count` is non-zero on a fresh item due
  to dev/test runs, reset it by editing the frontmatter directly. Durable
  items are unaffected functionally; only the header label changes.

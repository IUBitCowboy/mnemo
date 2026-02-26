# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

Mnemo is a two-tier AI agent system for university course material generation:

- **Mnemo** — the meta-layer: tools, shell helpers, shared assets, and the framework for creating Muse agents
- **Muse agents** — course-specific personas (Clio = SE1/P465, Calliope = C291)

Mnemo is intended for open-source distribution. It must not depend on Lore Forge, Obsidian, or any personal workflow infrastructure.

## Repository Structure

```
mnemo/
  Clio/
    clio_persona.md          # SE1 instructional architect persona
  Calliope/
    calliope_persona.md      # C291 instructional architect persona
    KB/                      # C291 course knowledge base files
  tools/
    chat.py                  # CLI entry point
    providers.py             # Anthropic / Gemini / Ollama adapters
    session.py               # Session file recorder
    mnemo_activate.sh        # Shell helpers (source to activate)
    mnemo_config.example     # Config template — copy to ~/.mnemo_config
    modes/
      mode_generate.md       # Injected KB: full artifact generation mode
      mode_chat.md           # Injected KB: conversational mode
  knowledge_base/
    decisions_log.md         # Cross-course design decisions and rationale
  SHARED_ASSETS/             # Shared CSS, bootstrap scripts, workflow diagram
  requirements.txt
```

## CLI Chat Tool

```bash
# Setup (one-time)
python -m venv .venv && .venv/bin/pip install -r requirements.txt

# Run
.venv/bin/python tools/chat.py \
  --persona Clio/clio_persona.md \
  --context /path/to/kb_file.md \
  --provider anthropic \
  --sessions-dir /path/to/sessions/
```

**Providers:** `anthropic` (default), `gemini`, `ollama`
**Model inference:** model names starting with `claude` → anthropic, `gemini` → gemini, else → ollama
**KB injection:** context files are injected as a priming message exchange (not appended to system prompt) — keeps system prompt cacheable
**In-session commands:** `/new` saves current session and starts a fresh one; `//` escapes a literal `/`

## Shell Helpers

```bash
source tools/mnemo_activate.sh   # or via direnv .envrc in project dir

chat with clio       # resolve alias, set persona, start chat
add kb <file>        # add KB context file for this session
kb clear             # clear KB list
provider anthropic   # switch provider (resets model to default)
model <name>         # override model
generation on|off    # toggle full artifact vs conversational mode
access anthropic     # load ANTHROPIC_API_KEY from 1Password (requires op CLI)
mnemo                # show current session state
mnemo reset          # reset to config defaults
```

API key op references go in `~/.mnemo_config` (never commit):
```bash
MNEMO_OP_ANTHROPIC="op://VaultName/ItemName/field"
```

## Muse Agent Conventions

Each muse lives in its own directory: `MmuseName/musename_persona.md`

Persona files are standalone and complete — no runtime composition yet. Decomposition into base + artifact-specific layers is planned (next phase after structural cleanup).

Course-instance KB files (e.g., `clio_kb_SP26.md`) live in the **course repo**, not here — they are course-instance specific and not part of the open-source distribution.

## Key Constraints

- Mnemo must remain independent of Lore Forge and Obsidian
- Never read, process, or pass student data to any API (FERPA)
- Never echo or print API key values — use existence checks only

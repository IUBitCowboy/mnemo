# Mnemo

Mnemo is a two-tier AI agent system for university course material generation.

- **Mnemo** — the framework: CLI tools, shell helpers, and the scaffolding for creating Muse agents.
- **Muse agents** — course-specific personas. The most capable muse is **Clio**, the instructional architect for CSCI-P465/565 (Software Engineering) at Indiana University.

Mnemo is designed for open-source distribution and has no dependency on any personal workflow infrastructure (Obsidian, Lore Forge, etc.).

> **FERPA:** This tool processes only instructor-written persona files and the instructor's own prompts. It never reads, processes, or transmits student data.

---

## Setup

**Requirements:** Python 3.11+

```bash
# Clone and create a virtual environment
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Configuration:** Copy the example config and fill in your values.

```bash
cp tools/mnemo_config.example ~/.mnemo_config
```

Key settings in `~/.mnemo_config`:

```bash
MNEMO_PROVIDER="anthropic"          # anthropic | gemini | ollama
MNEMO_SESSIONS_DIR="./sessions/"    # where session transcripts are saved

# Persona aliases — used by: chat with <name>
MNEMO_PERSONA_CLIO="/path/to/mnemo/Clio/clio_base.md"

# API key references (1Password op CLI — value never echoed)
MNEMO_OP_ANTHROPIC="op://VaultName/Anthropic API Key/credential"
```

A project-level `.mnemo_config` in your working directory overrides `~/.mnemo_config`.

---

## Activating the Shell Helpers

```bash
source /path/to/mnemo/tools/mnemo_activate.sh
```

Use [direnv](https://direnv.net/) with an `.envrc` to source this automatically when you enter your project directory.

---

## CLI Command Reference

### Starting a session

```bash
chat with clio          # set persona to Clio and start chatting
chat                    # start with whatever persona is already set
```

The `chat with <name>` step is required before any `generation` or `capture` commands — it sets the active muse.

### Knowledge base

```bash
add kb <file>           # inject a KB file into the next session's context
kb show                 # list current KB files
kb clear                # remove all KB files
```

KB files are injected as a priming exchange (not appended to the system prompt), keeping the system prompt cacheable.

### Artifact generation (Clio)

Clio supports three artifact layers. Load one before starting a session:

```bash
generation icex         # In-Class Exercises + TA roles + 10-pt rubrics
generation slides       # slide deck template
generation project      # project assignments + 100-pt rubrics + MoJ template
generation clear        # unload the artifact layer
```

Toggle full-output vs. conversational mode:

```bash
generation focus on     # full artifact generation mode
generation focus off    # conversational / exploratory mode
generation on           # alias: focus on
generation off          # alias: clear layer + focus off
generation              # show current artifact layer and focus state
```

**For Anthropic and Gemini providers**, all discovered artifact layers are assembled into the system prompt by default (layer scope `*`). For Ollama, only the explicitly selected layer is used (`focused`).

### Provider and model

```bash
provider anthropic      # switch to Anthropic (resets model to default)
provider gemini         # switch to Gemini
provider ollama         # switch to local Ollama
model claude-opus-4-6   # override model for this session
model                   # show current model
```

Default models: `claude-sonnet-4-6` (Anthropic), `gemini-3.0-flash-thinking` (Gemini), `llama3.2` (Ollama).

### API key access (1Password)

```bash
access anthropic        # load ANTHROPIC_API_KEY from 1Password
access gemini           # load GEMINI_API_KEY from 1Password
```

Requires the `op` CLI and `MNEMO_OP_*` references set in `~/.mnemo_config`.

### Inbox — quick-capture ideas

```bash
capture "Add a Docker warm-up exercise before the compose lab"
capture --priority P1 --lifecycle ephemeral "Reminder: push SP26 ICEX draft"

inbox                   # list active inbox items
inbox show <id>         # show full item text
inbox resolve <id>      # mark as acted on
inbox archive <id>      # suppress without resolving
```

One inbox item is automatically injected into Clio's context at the start of each session.

### HIL (Human-in-the-Loop) provenance

```bash
hil galley <file> --session <session-file>   # stamp a galley with session provenance
hil galley <file> --session <s> --turns Q3,Q7  # record specific turns
hil review <file>       # mark as human-reviewed
hil approve <file>      # mark as approved
hil status [<dir>]      # show HIL status of artifacts in a directory
hil show <file>         # print the HIL block for a file
```

Requires `MNEMO_HIL_SCRIPT` set in your project `.envrc`.

### Session state

```bash
mnemo                   # show full session configuration
mnemo reset             # reset all state to config defaults
help                    # print command reference
```

---

## Typical Workflow with Clio

```bash
# 1. Activate helpers (or let direnv do it)
source tools/mnemo_activate.sh

# 2. Load API key
access anthropic

# 3. Add course KB for the current semester
add kb /path/to/clio_kb_SP26.md

# 4. Set the artifact type you want to generate
generation icex
generation focus on

# 5. Start the session
chat with clio

# 6. Inside the session:
#    /new  — save current session and start a fresh one
#    quit  — exit and save
```

---

## Repository Structure

```
mnemo/
  Clio/
    clio_base.md          # SE1 system prompt (always loaded)
    clio_icex.md          # Artifact layer: ICEXs, TA roles, rubrics
    clio_slides.md        # Artifact layer: slide decks
    clio_project.md       # Artifact layer: project assignments, MoJ template
    inbox/                # Captured quick-ideas for Clio
  Calliope/
    calliope_persona.md   # C291 instructional architect (monolith)
    KB/                   # C291 knowledge base files
  tools/
    chat.py               # CLI entry point
    providers.py          # Anthropic / Gemini / Ollama adapters
    session.py            # Session file recorder
    inbox.py              # Quick-capture tool
    mnemo_activate.sh     # Shell helpers (source to activate)
    mnemo_config.example  # Config template
    modes/
      mode_generate.md    # Injected KB: full artifact generation mode
      mode_chat.md        # Injected KB: conversational mode
  knowledge_base/
    decisions_log.md      # Cross-course design decisions and rationale
  SHARED_ASSETS/          # Shared CSS, bootstrap scripts, workflow diagram
  requirements.txt
```

Course-instance KB files (e.g., `clio_kb_SP26.md`) live in the **course repo**, not here — they are course-instance specific and not part of this distribution.

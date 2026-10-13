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
```

**API keys** — two methods:

```bash
# Method 1: Standard environment variables (recommended for most users)
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="AIza..."

# Method 2: 1Password CLI (optional convenience)
# Set op:// references in ~/.mnemo_config; use `access anthropic` to load
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

Clio supports four artifact layers. Load one before starting a session:

```bash
generation icex         # In-Class Exercises + TA roles + 10-pt rubrics
generation slides       # slide deck template
generation project      # project assignments + 100-pt rubrics + MoJ template
generation pages        # LMS page content: weekly overviews, reference
                        # pages, lecture-notes shells, announcements
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

### API key access

```bash
# If using standard env vars (ANTHROPIC_API_KEY / GEMINI_API_KEY), no action needed.

# If using 1Password CLI:
access anthropic        # load ANTHROPIC_API_KEY from 1Password
access gemini           # load GEMINI_API_KEY from 1Password
```

The `access` command requires the `op` CLI and `MNEMO_OP_*` references in `~/.mnemo_config`. Standard environment variables work without any additional setup.

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
    clio_pages.md         # Artifact layer: LMS pages (overviews, reference
                          # pages, lecture-notes shells, announcements)
    clio_persona.md       # Deprecated monolith — do not use for new work
    inbox/                # Captured quick-ideas for Clio
  Calliope/
    calliope_base.md      # C291 system prompt (always loaded)
    calliope_icex.md      # Artifact layer: Bug in the Path, Quest Rewards
    calliope_slides.md    # Artifact layer: Cliffhanger, AI Prompts
    calliope_project.md   # Artifact layer: Hero's Debugging Log, skeleton code
    calliope_persona.md   # Deprecated monolith — do not use for new work
    KB/                   # C291 knowledge base files
  skills/                  # Mnemo skills (cross-course, auto-loaded)
    pedagogy/             # 20 pedagogical principles (evidence-reviewed)
    techniques/           # 14 reusable workflow patterns
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
    instructor_principles.md  # Instructor AI-use principles (not auto-loaded)
  SHARED_ASSETS/          # Shared CSS, bootstrap scripts, workflow diagram
  requirements.txt
```

Course-instance KB files (e.g., `clio_kb_SP26.md`) live in the **course repo**, not here — they are course-instance specific and not part of this distribution.

---

## Creating a New Muse

A muse is a course-specific persona built on the three-layer architecture:

1. **Create a muse directory** (e.g., `Euterpe/`):
   ```
   Euterpe/
     euterpe_base.md       # ROLE + COURSE CONTEXT + course-specific pillars + tone
     euterpe_icex.md        # ICEX conventions specific to the course
     euterpe_slides.md      # Slide deck conventions specific to the course
     euterpe_project.md     # Project conventions (if applicable)
   ```

2. **Write `euterpe_base.md`** — define the muse identity, course context
   (course number, audience, class period, arc, submission method), and any
   course-specific pedagogical pillars. Add a `## PEDAGOGICAL ANALYSIS —
   COURSE DIMENSIONS` section listing course-specific analysis items. The
   generic analysis format comes from the `pedagogical-analysis` skill.

3. **Write artifact layers** — each layer contains only course-specific
   conventions. Generic patterns (DoD format, SBP, rubric HTML, slide deck
   structure) come from Mnemo skills automatically.

4. **Decide the candidate-proposal checkpoints** ("Clio proposes, instructor
   disposes") — for each generated element the muse will produce, ask:

   - Does this element shape a pedagogical outcome the instructor should own?
   - Would the instructor want to review or override it before it reaches
     students?
   - Is the muse's first guess likely to need adjustment?

   If yes to any of these, the element is a **candidate-proposal checkpoint**:
   the muse proposes N candidates and the instructor selects, rejects, or
   provides their own — the muse never presents a recommended favorite (see
   the Avoid Sycophancy skill). Configure a count per element and encode it
   in the muse's `candidates.manifest` (no manifest → default 4) as well as
   in the artifact layer where those conventions live. Elements
   that are mechanical formatting (fixed template sections, file names,
   structure the instructor has already standardized) do not need the pattern.

5. **Add a persona alias** in `~/.mnemo_config`:
   ```bash
   MNEMO_PERSONA_EUTERPE="/path/to/mnemo/Euterpe/euterpe_base.md"
   ```

6. **Test:** `chat with euterpe` → `generation icex` → `generation focus on`
   → verify output quality and that skills are present in the assembled prompt.

**Key rules:**
- No muse file should reference personal infrastructure (Lore Forge, Obsidian,
  1Password).
- No muse file should duplicate content that lives in a Mnemo skill.
- Course-specific pedagogical analysis dimensions go in the base file; the
  format template comes from the skill.
- Artifact layers are mutually exclusive — only one is active at a time.
- Candidate proposals are a **pre-galley checkpoint**; they happen during
  generation, before the artifact exists. The HIL provenance lifecycle
  (`hil galley` → `hil review` → `hil approve`) picks up afterward as the
  post-generation record.

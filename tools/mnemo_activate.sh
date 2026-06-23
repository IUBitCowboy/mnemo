#!/usr/bin/env bash
# mnemo_activate.sh — Load Mnemo shell helpers into the current session.
#
# Usage:
#   source /path/to/mnemo/tools/mnemo_activate.sh
#
# After sourcing, the following commands are available:
#   chat [with <persona>]  — start a chat session (optionally set persona first)
#   add kb <file>          — add a KB context file for this session
#   kb clear               — clear all KB context files
#   provider <name>        — set provider: anthropic | gemini | ollama
#   model <name>           — set model (empty = provider default)
#   generation [icex|slides|project]  — set artifact context layer
#   generation [clear|focus on|off]   — clear layer or toggle full-output mode
#   generation [on|off]               — aliases: on=focus on, off=clear+focus off
#   generation                        — show current artifact and focus state
#   access anthropic       — load ANTHROPIC_API_KEY from 1Password (requires op CLI)
#   access gemini          — load GEMINI_API_KEY from 1Password (requires op CLI)
#   capture [opts] "<text>"— capture a quick-idea to the current muse's inbox
#   inbox [list|show|resolve|archive]  — manage inbox items
#   hil [stamp|review|approve|status|show]  — HIL provenance tagging
#   help                   — show command reference (also: mnemo help)
#   mnemo                  — show current session configuration
#   mnemo reset            — reset all session state to config defaults
#
# Config files (both optional; local overrides global):
#   ~/.mnemo_config          — global/machine defaults
#   .mnemo_config            — per-project overrides (put this in your project root)
#
# Persona aliases are defined in config as:
#   MNEMO_PERSONA_<NAME>=/path/to/persona.md   (NAME is case-insensitive)
#
# API key op references (set in ~/.mnemo_config — never commit these):
#   MNEMO_OP_ANTHROPIC="op://VaultName/ItemName/field"
#   MNEMO_OP_GEMINI="op://VaultName/ItemName/field"
#
# Provider layer scope (override in ~/.mnemo_config to change defaults):
#   MNEMO_LAYER_SCOPE_ANTHROPIC="*"       # assemble all artifact layers (default)
#   MNEMO_LAYER_SCOPE_GEMINI="*"          # assemble all artifact layers (default)
#   MNEMO_LAYER_SCOPE_OLLAMA="focused"    # use selected layer only (default)
#   Values: "*" = all layers; "focused" = MNEMO_ARTIFACT_LAYER only
#
# Skill loading scope (override in ~/.mnemo_config):
#   MNEMO_SKILLS_SCOPE="all"              # auto-load all skills (default)
#   MNEMO_SKILLS_SCOPE="manifest"         # read muse_dir/skills.manifest
#   MNEMO_SKILLS_SCOPE="none"             # no skills (bare muse)

# ── Internal bookkeeping ──────────────────────────────────────────────────────

_MNEMO_TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load global config for machine-level defaults (Python path, etc.).
# Project-specific config (persona paths, sessions dir) is handled by direnv .envrc.
[[ -f "$HOME/.mnemo_config" ]] && source "$HOME/.mnemo_config"

# Resolve Python and chat script (config can override)
MNEMO_PYTHON="${MNEMO_PYTHON:-$_MNEMO_TOOLS_DIR/../.venv/bin/python}"
MNEMO_CHAT_SCRIPT="${MNEMO_CHAT_SCRIPT:-$_MNEMO_TOOLS_DIR/chat.py}"

# Session-level state (set from config defaults, then mutable per session)
MNEMO_PROVIDER="${MNEMO_PROVIDER:-anthropic}"
MNEMO_MODEL="${MNEMO_MODEL:-}"
MNEMO_SESSIONS_DIR="${MNEMO_SESSIONS_DIR:-./sessions/}"
MNEMO_PERSONA="${MNEMO_PERSONA:-}"
MNEMO_ARTIFACT_LAYER=""                    # path to artifact layer file, or empty
MNEMO_FOCUS="${MNEMO_FOCUS:-off}"          # "on" → inject mode_generate.md; "off" → inject mode_chat.md
MNEMO_KB=()  # Always start with empty KB; use 'add kb' to populate
MNEMO_INBOX_LIMIT=1                        # max inbox items injected per chat session

# Derive inbox script path from chat script location (no config needed)
MNEMO_INBOX_SCRIPT="${MNEMO_CHAT_SCRIPT%/chat.py}/inbox.py"

# HIL provenance script — set MNEMO_HIL_SCRIPT in clio .envrc (not derived here)
# because hil.py lives in the clio repo, not the mnemo tools dir.
MNEMO_HIL_SCRIPT="${MNEMO_HIL_SCRIPT:-}"

# Provider layer scope defaults (override in ~/.mnemo_config)
# "*" = assemble all artifact layers at launch; "focused" = MNEMO_ARTIFACT_LAYER only
MNEMO_LAYER_SCOPE_ANTHROPIC="${MNEMO_LAYER_SCOPE_ANTHROPIC:-*}"
MNEMO_LAYER_SCOPE_GEMINI="${MNEMO_LAYER_SCOPE_GEMINI:-*}"
MNEMO_LAYER_SCOPE_OLLAMA="${MNEMO_LAYER_SCOPE_OLLAMA:-focused}"

# Skill loading scope (v1: auto-load all)
# MNEMO_SKILLS_SCOPE="all"      # load all skills (default)
# MNEMO_SKILLS_SCOPE="manifest" # read skills.manifest from muse directory
# MNEMO_SKILLS_SCOPE="none"     # no skills (bare muse)
MNEMO_SKILLS_SCOPE="${MNEMO_SKILLS_SCOPE:-all}"

# ── Internal helpers ──────────────────────────────────────────────────────────

_mnemo_resolve_persona() {
    # Resolve a name or path to a persona file path.
    # Checks MNEMO_PERSONA_<NAME> alias first, then treats arg as a direct path.
    local name="$1"
    local upper
    upper=$(echo "$name" | tr '[:lower:]' '[:upper:]')
    local alias_var="MNEMO_PERSONA_${upper}"
    local resolved="${!alias_var}"
    if [[ -n "$resolved" ]]; then
        echo "$resolved"
    elif [[ -f "$name" ]]; then
        echo "$name"
    else
        echo ""
    fi
}

_mnemo_discover_layers() {
    # Find all artifact layer files for the current muse persona directory.
    # Convention: <muse>_<type>.md — excludes *_base.md and *_persona*.md
    # (any file with _persona in the name is a deprecated monolith or preserved original).
    # Prints one absolute path per line, alphabetically sorted.
    local muse_dir muse_name
    muse_dir="$(dirname "$MNEMO_PERSONA")"
    muse_name="$(basename "$muse_dir" | tr '[:upper:]' '[:lower:]')"
    for f in "$muse_dir"/${muse_name}_*.md; do
        [[ "$f" == *_base.md ]] && continue
        [[ "$f" == *_persona* ]] && continue
        [[ -f "$f" ]] && echo "$f"
    done | sort
}

_mnemo_list_personas() {
    # Print known persona aliases from shell variables (not just exported env).
    local found=0
    for varname in $(compgen -v MNEMO_PERSONA_); do
        [[ "$varname" == "MNEMO_PERSONA" ]] && continue
        local raw="${varname#MNEMO_PERSONA_}"
        local alias_name
        alias_name=$(echo "$raw" | tr '[:upper:]' '[:lower:]')
        printf "    %-12s %s\n" "$alias_name" "${!varname}"
        found=1
    done
    [[ $found -eq 0 ]] && echo "    (no aliases defined — set MNEMO_PERSONA_<NAME> in config)"
}

# ── Public commands ───────────────────────────────────────────────────────────

chat() {
    # chat                                    — start with current defaults
    # chat with <name>                        — set persona by alias then start
    # chat --context <file> [--context <file> ...] [with <name>]
    #                                         — inject extra context files

    # Pre-process: pull out --context FILE pairs; leave everything else in $@
    local extra_ctx=() remaining_args=()
    while [[ $# -gt 0 ]]; do
        if [[ "$1" == "--context" ]]; then
            shift
            if [[ $# -eq 0 ]]; then
                echo "mnemo: --context requires a file argument" >&2; return 1
            fi
            if [[ ! -f "$1" ]]; then
                echo "mnemo: context file not found: $1" >&2; return 1
            fi
            extra_ctx+=("$1"); shift
        else
            remaining_args+=("$1"); shift
        fi
    done
    set -- "${remaining_args[@]+"${remaining_args[@]}"}"

    if [[ "$1" == "with" ]]; then
        if [[ -z "$2" ]]; then
            echo "usage: chat with <persona>" >&2; return 1
        fi
        local path
        path="$(_mnemo_resolve_persona "$2")"
        if [[ -z "$path" ]]; then
            echo "mnemo: unknown persona '$2'" >&2
            echo "       Known aliases:" >&2
            _mnemo_list_personas >&2
            return 1
        fi
        MNEMO_PERSONA="$path"
        echo "  Persona → $path"
    fi

    if [[ -z "$MNEMO_PERSONA" ]]; then
        echo "mnemo: no persona set. Use: chat with <name>" >&2
        return 1
    fi
    if [[ ! -f "$MNEMO_PERSONA" ]]; then
        echo "mnemo: persona file not found: $MNEMO_PERSONA" >&2
        return 1
    fi

    # Assemble system prompt: [Mnemo skills] + [base persona] + [artifact layer(s)]
    # Skills are prepended before the persona so cross-course pedagogy and
    # techniques load first, then course-specific identity, then artifact layer.
    # Resolution order:
    #   1. Explicit MNEMO_ARTIFACT_LAYER → focused (one layer, overrides provider scope)
    #   2. Provider scope "*"            → all discovered layers assembled
    #   3. Provider scope "focused"/other → base only
    local assembled_persona base_name
    base_name="$(basename "$MNEMO_PERSONA" .md)"

    # Discover Mnemo skills (respect MNEMO_SKILLS_SCOPE)
    local mnemo_skills_dir="$_MNEMO_TOOLS_DIR/../skills"
    local skill_files=() skill_count=0
    if [[ -d "$mnemo_skills_dir" && "$MNEMO_SKILLS_SCOPE" != "none" ]]; then
        if [[ "$MNEMO_SKILLS_SCOPE" == "manifest" ]]; then
            # Read skills.manifest from the muse directory
            local muse_dir; muse_dir="$(dirname "$MNEMO_PERSONA")"
            local manifest="$muse_dir/skills.manifest"
            if [[ -f "$manifest" ]]; then
                while IFS= read -r line; do
                    [[ -z "$line" || "$line" == \#* ]] && continue
                    local sf="$mnemo_skills_dir/${line}.md"
                    [[ -f "$sf" ]] && skill_files+=("$sf")
                done < "$manifest"
            fi
        else
            # Default: auto-load all skills
            for f in "$mnemo_skills_dir"/pedagogy/*.md "$mnemo_skills_dir"/techniques/*.md; do
                [[ -f "$f" ]] && skill_files+=("$f")
            done
        fi
        skill_count=${#skill_files[@]}
    fi
    if [[ $skill_count -gt 0 ]]; then
        echo "  Skills → $skill_count files loaded [pedagogy + techniques]"
    fi

    if [[ -n "$MNEMO_ARTIFACT_LAYER" ]]; then
        # Explicit selection: one layer, overrides provider scope default
        local layer_name
        layer_name="$(basename "$MNEMO_ARTIFACT_LAYER" .md)"
        assembled_persona="/tmp/${base_name}+${layer_name}.md"
        if [[ $skill_count -gt 0 ]]; then
            cat "${skill_files[@]}" "$MNEMO_PERSONA" "$MNEMO_ARTIFACT_LAYER" > "$assembled_persona"
        else
            cat "$MNEMO_PERSONA" "$MNEMO_ARTIFACT_LAYER" > "$assembled_persona"
        fi
        echo "  Assembled → $assembled_persona"
    else
        local pvar="MNEMO_LAYER_SCOPE_$(echo "$MNEMO_PROVIDER" | tr '[:lower:]' '[:upper:]')"
        local layer_scope="${!pvar:-focused}"
        if [[ "$layer_scope" == "*" ]]; then
            # Provider scope: assemble all discovered artifact layers
            local all_layers=() layer_names=""
            while IFS= read -r f; do
                all_layers+=("$f")
                layer_names+="$(basename "$f" .md) "
            done < <(_mnemo_discover_layers)
            if [[ ${#all_layers[@]} -gt 0 ]]; then
                assembled_persona="/tmp/${base_name}+all.md"
                if [[ $skill_count -gt 0 ]]; then
                    cat "${skill_files[@]}" "$MNEMO_PERSONA" "${all_layers[@]}" > "$assembled_persona"
                else
                    cat "$MNEMO_PERSONA" "${all_layers[@]}" > "$assembled_persona"
                fi
                echo "  Assembled → $assembled_persona  [${#all_layers[@]} layers: ${layer_names% }]"
            else
                if [[ $skill_count -gt 0 ]]; then
                    assembled_persona="/tmp/${base_name}+skills.md"
                    cat "${skill_files[@]}" "$MNEMO_PERSONA" > "$assembled_persona"
                    echo "  Assembled → $assembled_persona  [skills only, no artifact layers found]"
                else
                    assembled_persona="$MNEMO_PERSONA"
                    echo "  Assembled → (no layers or skills found — using base only)"
                fi
            fi
        else
            # Provider scope "focused" with no explicit selection: skills + base only
            if [[ $skill_count -gt 0 ]]; then
                assembled_persona="/tmp/${base_name}+skills.md"
                cat "${skill_files[@]}" "$MNEMO_PERSONA" > "$assembled_persona"
                echo "  Assembled → $assembled_persona  [focused: skills + base only]"
            else
                assembled_persona="$MNEMO_PERSONA"
            fi
        fi
    fi

    # Build --context args: mode file, inbox inject (if any), then user KB files
    local ctx_args=()
    local mode_file
    if [[ "$MNEMO_FOCUS" == "on" ]]; then
        mode_file="$_MNEMO_TOOLS_DIR/modes/mode_generate.md"
    else
        mode_file="$_MNEMO_TOOLS_DIR/modes/mode_chat.md"
    fi
    ctx_args+=(--context "$mode_file")

    # Inbox injection prep
    local _inbox_inject="" _inbox_ids=""
    local _muse_dir; _muse_dir="$(dirname "$MNEMO_PERSONA")"
    if [[ -f "$MNEMO_INBOX_SCRIPT" && -d "$_muse_dir/inbox" ]]; then
        local _inject_tmp; _inject_tmp="/tmp/mnemo_inbox_$(date +%Y%m%d%H%M%S).md"
        local _ids_tmp;    _ids_tmp="/tmp/mnemo_inbox_ids_$(date +%Y%m%d%H%M%S).txt"
        "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" prep \
            --muse-dir "$_muse_dir" \
            --limit "${MNEMO_INBOX_LIMIT:-1}" \
            --inject-out "$_inject_tmp" \
            --ids-out "$_ids_tmp" 2>/dev/null
        [[ -s "$_inject_tmp" ]] && _inbox_inject="$_inject_tmp"
        [[ -s "$_ids_tmp"    ]] && _inbox_ids="$(cat "$_ids_tmp")"
    fi
    [[ -n "$_inbox_inject" ]] && ctx_args+=(--context "$_inbox_inject")

    for kb in "${MNEMO_KB[@]}"; do
        ctx_args+=("$kb")
    done

    # Append any --context files passed directly on the command line
    for ctx in "${extra_ctx[@]+"${extra_ctx[@]}"}"; do
        ctx_args+=(--context "$ctx")
    done

    local model_args=()
    [[ -n "$MNEMO_MODEL" ]] && model_args=(--model "$MNEMO_MODEL")

    echo ""
    "$MNEMO_PYTHON" "$MNEMO_CHAT_SCRIPT" \
        --persona "$assembled_persona" \
        --provider "$MNEMO_PROVIDER" \
        --sessions-dir "$MNEMO_SESSIONS_DIR" \
        "${model_args[@]}" \
        "${ctx_args[@]}"

    # Post-session: update session counts and auto-archive ephemerals
    if [[ -n "$_inbox_ids" ]]; then
        # shellcheck disable=SC2086
        "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" done \
            --muse-dir "$_muse_dir" \
            --ids $_inbox_ids 2>/dev/null
    fi
}

add() {
    # add kb <file>
    if [[ "$1" != "kb" ]]; then
        echo "usage: add kb <filepath>" >&2; return 1
    fi
    if [[ -z "$2" ]]; then
        echo "usage: add kb <filepath>" >&2; return 1
    fi
    if [[ ! -f "$2" ]]; then
        echo "mnemo: file not found: $2" >&2; return 1
    fi
    MNEMO_KB+=("$2")
    echo "  KB +  $2  (${#MNEMO_KB[@]} file(s) total)"
}

kb() {
    # kb clear   — remove all KB files
    # kb show    — list current KB files (also shown in 'mnemo')
    case "$1" in
        clear)
            MNEMO_KB=()
            echo "  KB cleared"
            ;;
        show|"")
            if [[ ${#MNEMO_KB[@]} -eq 0 ]]; then
                echo "  KB: (empty)"
            else
                for f in "${MNEMO_KB[@]}"; do echo "  KB: $f"; done
            fi
            ;;
        *)
            echo "usage: kb [clear|show]" >&2; return 1
            ;;
    esac
}

provider() {
    if [[ -z "$1" ]]; then
        echo "  Provider: $MNEMO_PROVIDER"; return
    fi
    case "$1" in
        anthropic|gemini|ollama)
            MNEMO_PROVIDER="$1"
            MNEMO_MODEL=""   # reset to provider default
            echo "  Provider → $MNEMO_PROVIDER  (model reset to provider default)"
            ;;
        *)
            echo "mnemo: unknown provider '$1'. Choose: anthropic, gemini, ollama" >&2
            return 1
            ;;
    esac
}

model() {
    if [[ -z "$1" ]]; then
        echo "  Model: ${MNEMO_MODEL:-<provider default>}"; return
    fi
    MNEMO_MODEL="$1"
    echo "  Model → $MNEMO_MODEL"
}

generation() {
    case "$1" in
        icex|slides|project)
            # Resolve artifact layer from persona directory
            if [[ -z "$MNEMO_PERSONA" ]]; then
                echo "mnemo: no persona set — run 'chat with <name>' first" >&2; return 1
            fi
            local muse_dir artifact_type layer_file
            muse_dir="$(dirname "$MNEMO_PERSONA")"
            artifact_type="$1"
            local muse_name
            muse_name="$(basename "$muse_dir" | tr '[:upper:]' '[:lower:]')"
            layer_file="$muse_dir/${muse_name}_${artifact_type}.md"
            if [[ ! -f "$layer_file" ]]; then
                echo "mnemo: artifact layer not found: $layer_file" >&2; return 1
            fi
            MNEMO_ARTIFACT_LAYER="$layer_file"
            echo "  Artifact → $layer_file"
            ;;
        clear)
            MNEMO_ARTIFACT_LAYER=""
            echo "  Artifact layer cleared"
            ;;
        focus)
            case "$2" in
                on)
                    MNEMO_FOCUS="on"
                    echo "  Focus → on (generation mode)"
                    ;;
                off)
                    MNEMO_FOCUS="off"
                    echo "  Focus → off (conversational)"
                    ;;
                *)
                    echo "usage: generation focus on|off" >&2; return 1
                    ;;
            esac
            ;;
        on)
            # Alias: focus on (no artifact layer change)
            MNEMO_FOCUS="on"
            echo "  Focus → on (generation mode)"
            ;;
        off)
            # Alias: clear artifact layer + focus off
            MNEMO_ARTIFACT_LAYER=""
            MNEMO_FOCUS="off"
            echo "  Artifact layer cleared, Focus → off (conversational)"
            ;;
        "")
            # Status display
            local artifact_label focus_label scope_label
            artifact_label="${MNEMO_ARTIFACT_LAYER:-(none)}"
            focus_label="off (conversational)"
            [[ "$MNEMO_FOCUS" == "on" ]] && focus_label="on (generation mode)"
            local pvar="MNEMO_LAYER_SCOPE_$(echo "$MNEMO_PROVIDER" | tr '[:lower:]' '[:upper:]')"
            local scope="${!pvar:-focused}"
            if [[ -n "$MNEMO_ARTIFACT_LAYER" ]]; then
                scope_label="focused (explicit — overrides ${MNEMO_PROVIDER} default: ${scope})"
            else
                scope_label="${scope} (${MNEMO_PROVIDER} default)"
            fi
            echo "  Artifact   : $artifact_label"
            echo "  Layer scope: $scope_label"
            echo "  Focus      : $focus_label"
            ;;
        *)
            echo "usage: generation [icex|slides|project|clear|focus on|off|on|off]" >&2; return 1
            ;;
    esac
}

access() {
    # access anthropic  — load ANTHROPIC_API_KEY from 1Password
    # access gemini     — load GEMINI_API_KEY from 1Password
    #
    # Requires op (1Password CLI) and the corresponding MNEMO_OP_* reference
    # set in ~/.mnemo_config. The key value is never printed.
    local provider="$1"
    if [[ -z "$provider" ]]; then
        echo "usage: access anthropic|gemini" >&2; return 1
    fi

    if ! command -v op &>/dev/null; then
        echo "mnemo: 'op' not found. Install: brew install 1password-cli" >&2
        return 1
    fi

    local op_ref env_var
    case "$provider" in
        anthropic)
            op_ref="$MNEMO_OP_ANTHROPIC"
            env_var="ANTHROPIC_API_KEY"
            ;;
        gemini)
            op_ref="$MNEMO_OP_GEMINI"
            env_var="GEMINI_API_KEY"
            ;;
        *)
            echo "mnemo: unknown provider '$provider'. Choose: anthropic, gemini" >&2
            return 1
            ;;
    esac

    if [[ -z "$op_ref" ]]; then
        echo "mnemo: MNEMO_OP_$(echo "$provider" | tr '[:lower:]' '[:upper:]') not set." >&2
        echo "       Add to ~/.mnemo_config:  MNEMO_OP_$(echo "$provider" | tr '[:lower:]' '[:upper:]')=\"op://Vault/Item/field\"" >&2
        return 1
    fi

    # Read from 1Password — value goes directly into env var, never echoed
    local _key
    if ! _key="$(op read "$op_ref" 2>&1)"; then
        echo "mnemo: op read failed: $_key" >&2
        return 1
    fi
    export "$env_var"="$_key"
    unset _key
    echo "  $env_var set"
}

capture() {
    # capture [--lifecycle durable|ephemeral] [--priority P1|P2|P3] [--source S] "<text>"
    # Capture a quick-idea item to the current muse's inbox.
    local _lifecycle="durable" _priority="P2" _source="cli" _text=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --lifecycle) _lifecycle="$2"; shift 2 ;;
            --priority)  _priority="$2";  shift 2 ;;
            --source)    _source="$2";    shift 2 ;;
            *)           _text="$1";      shift   ;;
        esac
    done
    if [[ -z "$_text" ]]; then
        echo "usage: capture [--lifecycle durable|ephemeral] [--priority P1|P2|P3] [--source S] \"<text>\"" >&2
        return 1
    fi
    if [[ -z "$MNEMO_PERSONA" ]]; then
        echo "mnemo: no persona set — run 'chat with <name>' first" >&2
        return 1
    fi
    local _muse_dir; _muse_dir="$(dirname "$MNEMO_PERSONA")"
    if [[ ! -f "$MNEMO_INBOX_SCRIPT" ]]; then
        echo "mnemo: inbox.py not found at $MNEMO_INBOX_SCRIPT" >&2
        return 1
    fi
    "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" capture \
        --muse-dir "$_muse_dir" \
        --text "$_text" \
        --lifecycle "$_lifecycle" \
        --priority "$_priority" \
        --source "$_source"
}

inbox() {
    # inbox                — list active items
    # inbox list           — alias
    # inbox show <id>      — print full item content
    # inbox resolve <id>   — status → resolved
    # inbox archive <id>   — status → archived
    if [[ -z "$MNEMO_PERSONA" ]]; then
        echo "mnemo: no persona set — run 'chat with <name>' first" >&2
        return 1
    fi
    if [[ ! -f "$MNEMO_INBOX_SCRIPT" ]]; then
        echo "mnemo: inbox.py not found at $MNEMO_INBOX_SCRIPT" >&2
        return 1
    fi
    local _muse_dir; _muse_dir="$(dirname "$MNEMO_PERSONA")"
    case "${1:-list}" in
        list|"")
            "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" list --muse-dir "$_muse_dir"
            ;;
        show)
            if [[ -z "$2" ]]; then echo "usage: inbox show <id>" >&2; return 1; fi
            "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" show --muse-dir "$_muse_dir" --id "$2"
            ;;
        resolve)
            if [[ -z "$2" ]]; then echo "usage: inbox resolve <id>" >&2; return 1; fi
            "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" set-status --muse-dir "$_muse_dir" --id "$2" --status resolved
            ;;
        archive)
            if [[ -z "$2" ]]; then echo "usage: inbox archive <id>" >&2; return 1; fi
            "$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" set-status --muse-dir "$_muse_dir" --id "$2" --status archived
            ;;
        *)
            echo "usage: inbox [list|show <id>|resolve <id>|archive <id>]" >&2; return 1
            ;;
    esac
}

hil() {
    # hil galley <file> --session S [--turns Q3,Q7] [--model M]
    # hil stamp <file> [--session S] [--model M]
    # hil review <file> [--reviewer R]
    # hil approve <file>
    # hil status [<dir>]
    # hil show <file>
    if [[ -z "$MNEMO_HIL_SCRIPT" ]]; then
        echo "mnemo: MNEMO_HIL_SCRIPT not set — add it to your project .envrc" >&2
        return 1
    fi
    if [[ ! -f "$MNEMO_HIL_SCRIPT" ]]; then
        echo "mnemo: hil.py not found at $MNEMO_HIL_SCRIPT" >&2
        return 1
    fi
    python3 "$MNEMO_HIL_SCRIPT" "$@"
}

help() {
    cat <<'EOF'
Mnemo commands
──────────────────────────────────────────────────────
chat [with <name>]          start chat session; optionally set persona
  chat --context <file>     inject an extra KB file (repeatable)
add kb <file>               append a KB file to session context
kb [clear|show]             manage KB file list
provider anthropic|gemini|ollama   switch provider (resets model)
model [<name>]              set or show model override
generation icex|slides|project     load an artifact layer
  generation clear          clear artifact layer
  generation focus on|off   toggle full-output mode
  generation on|off         aliases for focus on / clear+off
access anthropic|gemini     load API key from 1Password
capture "<text>" [opts]     capture a quick-idea to muse inbox
  --lifecycle durable|ephemeral
  --priority P1|P2|P3
inbox [list]                list active inbox items
  inbox show <id>           show full item
  inbox resolve <id>        mark tried / acted on
  inbox archive <id>        suppress without resolving
hil galley <file> --session S   stamp galley with required session provenance
  hil galley ... --turns Q3,Q7  record specific turns that produced the artifact
hil stamp <file> [opts]     stamp artifact (no session validation — legacy)
  hil review <file>         mark human-reviewed
  hil approve <file>        mark approved
  hil status [<dir>]        show HIL status of artifacts
  hil show <file>           print HIL block for a file
mnemo [status]              show session configuration
  mnemo reset               reset all state to defaults
  mnemo help                show this help  (also: help)
──────────────────────────────────────────────────────
EOF
}

mnemo() {
    case "$1" in
        help)
            help
            ;;
        reset)
            MNEMO_PROVIDER="${MNEMO_PROVIDER_DEFAULT:-anthropic}"
            MNEMO_MODEL=""
            MNEMO_PERSONA=""
            MNEMO_ARTIFACT_LAYER=""
            MNEMO_FOCUS="off"
            MNEMO_KB=()
            MNEMO_INBOX_LIMIT=1
            echo "  Session state reset to defaults"
            ;;
        ""|status)
            local focus_label="off (conversational)"
            [[ "$MNEMO_FOCUS" == "on" ]] && focus_label="on (generation mode)"
            local artifact_label="${MNEMO_ARTIFACT_LAYER:-(none)}"
            local pvar="MNEMO_LAYER_SCOPE_$(echo "$MNEMO_PROVIDER" | tr '[:lower:]' '[:upper:]')"
            local scope="${!pvar:-focused}"
            local scope_label
            if [[ -n "$MNEMO_ARTIFACT_LAYER" ]]; then
                scope_label="focused (explicit — overrides ${MNEMO_PROVIDER} default: ${scope})"
            else
                scope_label="${scope} (${MNEMO_PROVIDER} default)"
            fi
            echo ""
            local key_status="not set — run: access anthropic"
            [[ -n "$ANTHROPIC_API_KEY" ]] && key_status="set"
            local hil_status="not set — add MNEMO_HIL_SCRIPT to .envrc"
            [[ -n "$MNEMO_HIL_SCRIPT" ]] && hil_status="set"
            echo "  ┌─ Mnemo Session ──────────────────────────────"
            echo "  │  Persona    : ${MNEMO_PERSONA:-<not set>}"
            echo "  │  Provider   : $MNEMO_PROVIDER"
            echo "  │  Model      : ${MNEMO_MODEL:-<provider default>}"
            echo "  │  API key    : $key_status"
            echo "  │  Sessions   : $MNEMO_SESSIONS_DIR"
            echo "  │  Layer scope: $scope_label"
            echo "  │  Skills     : ${MNEMO_SKILLS_SCOPE:-all}"
            echo "  │  Artifact   : $artifact_label"
            echo "  │  Focus      : $focus_label"
            echo "  │  HIL script : $hil_status"
            echo "  │  KB files   :"
            if [[ ${#MNEMO_KB[@]} -eq 0 ]]; then
                echo "  │    (none)"
            else
                for kb in "${MNEMO_KB[@]}"; do echo "  │    $kb"; done
            fi
            echo "  │  Inbox limit: ${MNEMO_INBOX_LIMIT:-1}"
            # Show inbox status if persona is set and inbox.py exists
            if [[ -n "$MNEMO_PERSONA" && -f "$MNEMO_INBOX_SCRIPT" ]]; then
                local _muse_dir; _muse_dir="$(dirname "$MNEMO_PERSONA")"
                if [[ -d "$_muse_dir/inbox" ]]; then
                    local _active_count
                    _active_count=$("$MNEMO_PYTHON" "$MNEMO_INBOX_SCRIPT" count \
                        --muse-dir "$_muse_dir" 2>/dev/null)
                    local _inject_count="${MNEMO_INBOX_LIMIT:-1}"
                    [[ $_active_count -lt $_inject_count ]] && _inject_count=$_active_count
                    echo "  │  Inbox      : $_active_count active → $_inject_count will inject"
                else
                    echo "  │  Inbox      : (no inbox)"
                fi
            else
                echo "  │  Inbox      : (no persona set)"
            fi
            echo "  │  Known personas:"
            _mnemo_list_personas | sed 's/^/  │/'
            echo "  └──────────────────────────────────────────────"
            echo ""
            ;;
        *)
            echo "usage: mnemo [status|reset]" >&2
            ;;
    esac
}

# Helpers loaded silently. Type 'mnemo' to see current session state.

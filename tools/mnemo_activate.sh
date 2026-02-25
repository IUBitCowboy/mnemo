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
#   generation on|off      — toggle artifact generation mode (default: off)
#   mnemo                  — show current session configuration
#   mnemo reset            — reset all session state to config defaults
#
# Config files (both optional; local overrides global):
#   ~/.mnemo_config          — global/machine defaults
#   .mnemo_config            — per-project overrides (put this in your project root)
#
# Persona aliases are defined in config as:
#   MNEMO_PERSONA_<NAME>=/path/to/persona.md   (NAME is case-insensitive)

# ── Internal bookkeeping ──────────────────────────────────────────────────────

_MNEMO_TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load global config, then local config (local wins)
[[ -f "$HOME/.mnemo_config" ]]  && source "$HOME/.mnemo_config"
[[ -f ".mnemo_config" ]]        && source ".mnemo_config"

# Resolve Python and chat script (config can override)
MNEMO_PYTHON="${MNEMO_PYTHON:-$_MNEMO_TOOLS_DIR/../.venv/bin/python}"
MNEMO_CHAT_SCRIPT="${MNEMO_CHAT_SCRIPT:-$_MNEMO_TOOLS_DIR/chat.py}"

# Session-level state (set from config defaults, then mutable per session)
MNEMO_PROVIDER="${MNEMO_PROVIDER:-anthropic}"
MNEMO_MODEL="${MNEMO_MODEL:-}"
MNEMO_SESSIONS_DIR="${MNEMO_SESSIONS_DIR:-./sessions/}"
MNEMO_PERSONA="${MNEMO_PERSONA:-}"
MNEMO_GENERATION="${MNEMO_GENERATION:-off}"
MNEMO_KB=()  # Always start with empty KB; use 'add kb' to populate

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
    # chat              — start with current defaults
    # chat with <name>  — set persona by alias then start
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

    # Build --context args: mode file first, then user KB files
    local ctx_args=()
    local mode_file
    if [[ "$MNEMO_GENERATION" == "on" ]]; then
        mode_file="$_MNEMO_TOOLS_DIR/modes/mode_generate.md"
    else
        mode_file="$_MNEMO_TOOLS_DIR/modes/mode_chat.md"
    fi
    ctx_args+=(--context "$mode_file")
    for kb in "${MNEMO_KB[@]}"; do
        ctx_args+=("$kb")
    done

    local model_args=()
    [[ -n "$MNEMO_MODEL" ]] && model_args=(--model "$MNEMO_MODEL")

    echo ""
    "$MNEMO_PYTHON" "$MNEMO_CHAT_SCRIPT" \
        --persona "$MNEMO_PERSONA" \
        --provider "$MNEMO_PROVIDER" \
        --sessions-dir "$MNEMO_SESSIONS_DIR" \
        "${model_args[@]}" \
        "${ctx_args[@]}"
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
        on)
            MNEMO_GENERATION="on"
            echo "  Generation mode ON — Clio will produce complete artifacts"
            ;;
        off)
            MNEMO_GENERATION="off"
            echo "  Generation mode OFF — Clio will work conversationally"
            ;;
        "")
            echo "  Generation: $MNEMO_GENERATION"
            ;;
        *)
            echo "usage: generation on|off" >&2; return 1
            ;;
    esac
}

mnemo() {
    case "$1" in
        reset)
            MNEMO_PROVIDER="${MNEMO_PROVIDER_DEFAULT:-anthropic}"
            MNEMO_MODEL=""
            MNEMO_PERSONA=""
            MNEMO_GENERATION="off"
            MNEMO_KB=()
            echo "  Session state reset to defaults"
            ;;
        ""|status)
            local gen_label="off (chat mode)"
            [[ "$MNEMO_GENERATION" == "on" ]] && gen_label="ON (generation mode)"
            echo ""
            echo "  ┌─ Mnemo Session ──────────────────────────────"
            echo "  │  Persona    : ${MNEMO_PERSONA:-<not set>}"
            echo "  │  Provider   : $MNEMO_PROVIDER"
            echo "  │  Model      : ${MNEMO_MODEL:-<provider default>}"
            echo "  │  Sessions   : $MNEMO_SESSIONS_DIR"
            echo "  │  Generation : $gen_label"
            echo "  │  KB files   :"
            if [[ ${#MNEMO_KB[@]} -eq 0 ]]; then
                echo "  │    (none)"
            else
                for kb in "${MNEMO_KB[@]}"; do echo "  │    $kb"; done
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

# ── Activation banner ─────────────────────────────────────────────────────────

echo "  Mnemo shell helpers loaded. Type 'mnemo' to see current state."

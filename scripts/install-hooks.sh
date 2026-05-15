#!/usr/bin/env bash
set -euo pipefail

# Install CodingAgentIM hooks for AI coding tools.
# Usage: ./install-hooks.sh [--tool claude-code|codex|gemini|all]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$(cd "$SCRIPT_DIR/../hooks" && pwd)"
TOOL="${1:---tool}"
TOOL_NAME="${2:-all}"

if [[ "$TOOL" == "--tool" ]]; then
    TOOL_NAME="${TOOL_NAME}"
else
    TOOL_NAME="$TOOL"
fi

install_claude_code() {
    local target="$HOME/.claude/settings.json"
    local dir="$(dirname "$target")"
    mkdir -p "$dir"

    if [[ -f "$target" ]]; then
        if grep -q "codingagentim" "$target" 2>/dev/null; then
            echo "[claude-code] Hook already installed in $target"
            return
        fi
        echo "[claude-code] WARNING: $target exists. Please merge manually from:"
        echo "  $HOOKS_DIR/claude-code.json"
        return
    fi

    cp "$HOOKS_DIR/claude-code.json" "$target"
    echo "[claude-code] Hook installed to $target"
}

install_codex() {
    local target="$HOME/.codex/config.toml"
    local dir="$(dirname "$target")"
    mkdir -p "$dir"

    if [[ -f "$target" ]]; then
        if grep -q "codingagentim" "$target" 2>/dev/null; then
            echo "[codex] Hook already installed in $target"
            return
        fi
        echo "[codex] Appending hook to $target"
        echo "" >> "$target"
        cat "$HOOKS_DIR/codex-cli.toml" >> "$target"
    else
        cp "$HOOKS_DIR/codex-cli.toml" "$target"
    fi
    echo "[codex] Hook installed to $target"
}

install_gemini() {
    local target="$HOME/.gemini/config.json"
    local dir="$(dirname "$target")"
    mkdir -p "$dir"

    if [[ -f "$target" ]]; then
        if grep -q "codingagentim" "$target" 2>/dev/null; then
            echo "[gemini] Hook already installed in $target"
            return
        fi
        echo "[gemini] WARNING: $target exists. Please merge manually from:"
        echo "  $HOOKS_DIR/gemini-cli.json"
        return
    fi

    cp "$HOOKS_DIR/gemini-cli.json" "$target"
    echo "[gemini] Hook installed to $target"
}

detect_and_install() {
    local installed=0
    if command -v claude &>/dev/null; then
        install_claude_code
        installed=1
    fi
    if command -v codex &>/dev/null; then
        install_codex
        installed=1
    fi
    if command -v gemini &>/dev/null; then
        install_gemini
        installed=1
    fi
    if [[ $installed -eq 0 ]]; then
        echo "No supported AI coding tools detected (claude, codex, gemini)."
        echo "Install one first, then re-run this script."
    fi
}

case "$TOOL_NAME" in
    claude-code|claude) install_claude_code ;;
    codex)              install_codex ;;
    gemini)             install_gemini ;;
    all)                detect_and_install ;;
    *)
        echo "Usage: $0 [--tool claude-code|codex|gemini|all]"
        exit 1
        ;;
esac

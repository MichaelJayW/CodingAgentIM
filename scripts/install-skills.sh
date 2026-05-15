#!/usr/bin/env bash
set -euo pipefail

# Install CodingAgentIM skills for AI coding agents.
# Usage: ./install-skills.sh [--local]
#
# --local   Install to current project's .claude/ directory
# (default) Install to global ~/.claude/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$(cd "$SCRIPT_DIR/../skills" && pwd)"
MODE="${1:-global}"

install_skills() {
    local target_dir="$1"
    local skills_target="$target_dir/skills/codingagentim"

    mkdir -p "$skills_target/references/products"

    cp "$SKILLS_DIR/SKILL.md" "$skills_target/SKILL.md"

    if [[ -f "$SKILLS_DIR/references/products/dingtalk.md" ]]; then
        cp "$SKILLS_DIR/references/products/dingtalk.md" "$skills_target/references/products/dingtalk.md"
    fi

    echo "Skills installed to $skills_target"
}

case "$MODE" in
    --local|-l)
        if [[ ! -d ".git" ]]; then
            echo "ERROR: Not in a git repository root. Run from your project root."
            exit 1
        fi
        install_skills ".claude"
        echo "Local install complete. Skills available in .claude/skills/codingagentim/"
        ;;
    global|--global|-g|*)
        install_skills "$HOME/.claude"
        echo "Global install complete. Skills available in ~/.claude/skills/codingagentim/"
        ;;
esac

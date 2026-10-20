#!/usr/bin/env bash
# SweetClaude context budget benchmark suite
# Run before and after any disable-model-invocation changes.
# Usage: ./scripts/benchmark.sh [project-dir]
# Exit 0 = all passed. Exit 1 = one or more failed.

set -euo pipefail

PROJECT_DIR="${1:-$(pwd)}"
PASS=0
FAIL=0
RESULTS=()

run_prompt() {
    local id="$1"
    local prompt="$2"
    local expected_patterns="$3"  # pipe-separated list

    echo -n "  $id: "
    response=$(cd "$PROJECT_DIR" && claude -p "$prompt" 2>/dev/null) || {
        echo "ERROR (claude CLI failed)"
        ((FAIL++)) || true
        RESULTS+=("ERROR | $id | $prompt")
        return
    }

    local matched=false
    IFS='|' read -ra patterns <<< "$expected_patterns"
    for pattern in "${patterns[@]}"; do
        if echo "$response" | grep -qi "$pattern"; then
            matched=true
            break
        fi
    done

    if $matched; then
        echo "PASS"
        ((PASS++)) || true
        RESULTS+=("PASS | $id | $prompt")
    else
        echo "FAIL"
        echo "    Expected one of: $expected_patterns"
        echo "    Response (first 2 lines): $(echo "$response" | head -2)"
        ((FAIL++)) || true
        RESULTS+=("FAIL | $id | $prompt")
    fi
}

echo "SweetClaude Benchmark Suite"
echo "==========================="
echo "Project: $PROJECT_DIR"
echo "Date: $(date)"
echo ""

echo "Navigation & session orientation:"
run_prompt "P1" "Where are we in this project?" "status|recap|sweetclaude:status|sweetclaude:utils"
run_prompt "P2" "Help me decide what to work on next." "sweetclaude:go|/go|backlog|priorit"

echo ""
echo "Intent-based skill triggering:"
run_prompt "P3" "There is a bug in production right now. What do I do?" "something-broke|hotfix|incident|sweetclaude:something"
run_prompt "P4" "I want to build a new feature. Where do I start?" "sweetclaude:build|feature|brainstorm|code-feature"
run_prompt "P5" "How do I review my code before submitting a PR?" "sweetclaude:build|code-review|review"

echo ""
echo "Discovery (ambient skill knowledge):"
run_prompt "P6" "How do I set up product milestones in SweetClaude?" "milestones|sweetclaude:plan|product-milestones"
run_prompt "P7" "What testing skills does SweetClaude have?" "testing|sweetclaude:testing|test"
run_prompt "P8" "How do I use SweetClaude? I am new to it." "sweetclaude:help|sweetclaude:bootstrap|help|bootstrap"

echo ""
echo "==========================="
echo "Results: $PASS passed, $FAIL failed out of 8"
echo ""

if [ $FAIL -gt 0 ]; then
    echo "FAILED:"
    for r in "${RESULTS[@]}"; do
        [[ "$r" == FAIL* || "$r" == ERROR* ]] && echo "  $r"
    done
    exit 1
fi

echo "All 8 prompts passed."
exit 0

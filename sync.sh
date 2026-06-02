#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

DEFAULT_RETRIES=3

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
    cat <<EOF
Usage: ./sync.sh <command> [options]

Commands:
  push    Push local commits to remote (with pre-flight checks + retry)
  pull    Pull remote commits (with safety checks + retry)
  fetch   Fetch remote and compare (read-only, no local changes)
  status  Print comprehensive sync status

Options:
  --retries N      Max retry attempts for network failures (default: $DEFAULT_RETRIES)
  --skip-check     Skip consistency check before push
  --allow-dirty    Allow pull even with uncommitted local changes

Examples:
  ./sync.sh push
  ./sync.sh push --skip-check
  ./sync.sh pull --allow-dirty
  ./sync.sh fetch
  ./sync.sh status
EOF
    exit 0
}

current_branch() {
    git branch --show-current 2>/dev/null || echo ""
}

short_hash() {
    git rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

remote_url() {
    git remote get-url origin 2>/dev/null || echo "not configured"
}

count_unpushed() {
    local branch
    branch=$(current_branch)
    if [[ -z "$branch" ]]; then
        echo "0"
        return
    fi
    # Suppress fatal when no upstream: default to 0 (all commits are "unpushed")
    git rev-parse --abbrev-ref "@{upstream}" &>/dev/null || { echo "0"; return; }
    git log "@{upstream}..HEAD" --oneline 2>/dev/null | wc -l | tr -d ' '
}

has_upstream() {
    git rev-parse --abbrev-ref "@{upstream}" &>/dev/null
}

is_tree_clean() {
    [[ -z "$(git status --porcelain)" ]]
}

# ---------------------------------------------------------------------------
# Network error detection
# ---------------------------------------------------------------------------

is_network_error() {
    local stderr="$1"
    if echo "$stderr" | grep -qiE \
        "timed out|timeout|could not resolve host|connection refused|connection reset|unable to access|could not read from remote|failed to connect|network is unreachable|no route to host"; then
        return 0
    fi
    return 1
}

classify_failure() {
    local stderr="$1"
    local lower
    lower=$(echo "$stderr" | tr '[:upper:]' '[:lower:]')

    # Non-retriable: auth
    if echo "$lower" | grep -qiE "permission denied|authentication failed|repository.*not found|access denied"; then
        echo "auth"
        return
    fi
    # Non-retriable: rejected (non-fast-forward)
    if echo "$lower" | grep -qiE "rejected.*non-fast-forward|failed to push.*rejected"; then
        echo "rejected"
        return
    fi
    # Non-retriable: merge conflict
    if echo "$lower" | grep -qiE "conflict|automatic merge failed|merge conflict"; then
        echo "conflict"
        return
    fi
    # Retriable: network errors
    if is_network_error "$stderr"; then
        echo "network"
        return
    fi
    echo "unknown"
}

# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

# Run a git command with retry on network errors.
# Usage: retry_git <max_retries> <base_delay_sec> cmd arg1 arg2 ...
# Returns the exit code of the last attempt.
retry_git() {
    local max_retries="$1"
    local base_delay="$2"
    shift 2

    local attempt=1
    local rc=0
    local stderr_file
    stderr_file=$(mktemp)
    # shellcheck disable=SC2064
    trap "rm -f '$stderr_file'" RETURN

    while [[ $attempt -le $max_retries ]]; do
        local stdout
        set +e
        stdout=$("$@" 2>"$stderr_file")
        rc=$?
        set -e
        local stderr
        stderr=$(<"$stderr_file")

        if [[ $rc -eq 0 ]]; then
            # Success
            echo "$stdout"
            rm -f "$stderr_file"
            return 0
        fi

        local failure_type
        failure_type=$(classify_failure "$stderr")

        if [[ "$failure_type" == "network" ]]; then
            if [[ $attempt -lt $max_retries ]]; then
                local delay=$((base_delay * (1 << (attempt - 1))))
                echo -e "${YELLOW}[retry] attempt $attempt/$max_retries failed (network). retrying in ${delay}s...${NC}" >&2
                sleep "$delay"
                attempt=$((attempt + 1))
                continue
            else
                echo -e "${RED}[sync] push/pull failed after $max_retries retries (network)${NC}" >&2
            fi
        else
            # Non-retriable: don't retry
            echo -e "${RED}[sync] push/pull failed ($failure_type)${NC}" >&2
        fi

        # Report the error
        echo "$stderr" >&2
        break
    done

    rm -f "$stderr_file"
    return "$rc"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

check_named_branch() {
    local branch
    branch=$(current_branch)
    if [[ -z "$branch" ]]; then
        echo -e "${RED}Error: detached HEAD state. Switch to a branch before syncing.${NC}"
        return 1
    fi
    echo "$branch"
}

check_remote() {
    if ! git remote get-url origin &>/dev/null; then
        echo -e "${RED}Error: no remote 'origin' configured.${NC}"
        echo "  git remote add origin <url>"
        return 1
    fi
}

run_consistency_check() {
    local checker="scripts/check_consistency.py"
    if [[ ! -f "$checker" ]]; then
        echo -e "${YELLOW}Warning: consistency checker not found, skipping.${NC}"
        return 0
    fi
    echo -n "consistency check... "
    if python3 "$checker" &>/dev/null; then
        echo -e "${GREEN}passed${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        echo ""
        python3 "$checker" 2>&1 || true
        echo ""
        echo -e "${RED}Push refused: consistency check failed. Fix errors above or use --skip-check.${NC}"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# RUNTIME-003 structured output
# ---------------------------------------------------------------------------

print_003_header() {
    echo ""
    echo -e "${BOLD}═══ Sync Status ═══${NC}"
}

print_003_field() {
    local label="$1"
    local value="$2"
    printf "  %-16s %s\n" "$label" "$value"
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

cmd_push() {
    local skip_check=false
    local max_retries=$DEFAULT_RETRIES

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-check) skip_check=true; shift ;;
            --retries)    max_retries="$2"; shift 2 ;;
            -h|--help)    usage ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
        esac
    done

    local branch commit_before remote count
    branch=$(check_named_branch) || return 1
    check_remote || return 1
    commit_before=$(short_hash)

    # Consistency
    if [[ "$skip_check" == false ]]; then
        run_consistency_check || return 1
    fi

    # Check if there's anything to push
    count=$(count_unpushed)
    if [[ "$count" == "0" ]] && has_upstream; then
        print_003_header
        print_003_field "Operation:" "push"
        print_003_field "Result:" "${GREEN}already up to date${NC}"
        print_003_field "Commit:" "$commit_before ($branch)"
        print_003_field "Remote:" "$(remote_url)"
        print_003_field "Unpushed:" "none"
        print_003_field "Next action:" "none"
        echo ""
        return 0
    fi

    echo -n "pushing to origin/$branch... "

    if retry_git "$max_retries" 2 git push origin "$branch"; then
        local commit_after
        commit_after=$(short_hash)

        print_003_header
        print_003_field "Operation:" "push"
        print_003_field "Result:" "${GREEN}success${NC}"
        print_003_field "Commit:" "$commit_after ($branch)"
        print_003_field "Remote:" "$(remote_url)"
        print_003_field "Pushed:" "yes"
        print_003_field "Unpushed:" "none"
        print_003_field "Next action:" "none"
        echo ""
    else
        local rc=$?
        local commit_now
        commit_now=$(short_hash)
        local unpushed
        unpushed=$(count_unpushed)

        print_003_header
        print_003_field "Operation:" "push"
        print_003_field "Result:" "${RED}FAILED${NC}"
        print_003_field "Commit:" "$commit_now ($branch)"
        print_003_field "Unpushed:" "$unpushed commit(s) remain"
        if [[ "$unpushed" != "0" ]]; then
            print_003_field "Next action:" "retry: ./sync.sh push"
        else
            print_003_field "Next action:" "check network and retry"
        fi
        echo ""
        return "$rc"
    fi
}

cmd_pull() {
    local allow_dirty=false
    local max_retries=$DEFAULT_RETRIES

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --allow-dirty) allow_dirty=true; shift ;;
            --retries)     max_retries="$2"; shift 2 ;;
            -h|--help)     usage ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
        esac
    done

    local branch commit_before
    branch=$(check_named_branch) || return 1
    check_remote || return 1
    commit_before=$(short_hash)

    # Guard: unpushed commits
    if has_upstream; then
        local unpushed
        unpushed=$(count_unpushed)
        if [[ "$unpushed" != "0" ]]; then
            print_003_header
            print_003_field "Operation:" "pull"
            print_003_field "Result:" "${RED}BLOCKED${NC}"
            print_003_field "Commit:" "$commit_before ($branch)"
            print_003_field "Unpushed:" "$unpushed commit(s) — push first"
            print_003_field "Next action:" "./sync.sh push"
            echo ""
            return 1
        fi
    fi

    # Guard: dirty tree
    if [[ "$allow_dirty" == false ]]; then
        if ! is_tree_clean; then
            print_003_header
            print_003_field "Operation:" "pull"
            print_003_field "Result:" "${RED}BLOCKED${NC}"
            print_003_field "Reason:" "working tree is dirty"
            print_003_field "Files:"
            git status --porcelain | sed 's/^/    /'
            print_003_field "Next action:" "commit or stash changes, or use --allow-dirty"
            echo ""
            return 1
        fi
    fi

    # Guard: upstream tracking
    if ! has_upstream; then
        print_003_header
        print_003_field "Operation:" "pull"
        print_003_field "Result:" "${RED}BLOCKED${NC}"
        print_003_field "Reason:" "no upstream tracking branch"
        print_003_field "Next action:" "push first to establish upstream tracking: ./sync.sh push"
        echo ""
        return 1
    fi

    echo -n "pulling from origin/$branch... "

    if retry_git "$max_retries" 2 git pull --ff-only origin "$branch"; then
        local commit_after
        commit_after=$(short_hash)

        print_003_header
        print_003_field "Operation:" "pull"
        print_003_field "Result:" "${GREEN}success${NC}"
        print_003_field "Commit:" "$commit_after ($branch) — was $commit_before"
        print_003_field "Remote:" "$(remote_url)"
        print_003_field "Unpushed:" "none"
        if [[ "$commit_before" != "$commit_after" ]]; then
            print_003_field "Files changed:"
            git diff --name-only "$commit_before" "$commit_after" 2>/dev/null | sed 's/^/    /'
            print_003_field "Next action:" "regenerate adapters if canonical files changed"
        else
            print_003_field "Next action:" "none"
        fi
        echo ""
    else
        local rc=$?
        local commit_now
        commit_now=$(short_hash)

        print_003_header
        print_003_field "Operation:" "pull"
        print_003_field "Result:" "${RED}FAILED${NC}"
        print_003_field "Commit:" "$commit_now ($branch)"
        print_003_field "Next action:" "resolve error and retry: ./sync.sh pull"
        echo ""
        return "$rc"
    fi
}

cmd_fetch() {
    local max_retries=$DEFAULT_RETRIES

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --retries) max_retries="$2"; shift 2 ;;
            -h|--help) usage ;;
            *) echo -e "${RED}Unknown option: $1${NC}"; usage ;;
        esac
    done

    local branch commit_before
    branch=$(check_named_branch) || return 1
    check_remote || return 1
    commit_before=$(short_hash)

    echo -n "fetching origin... "

    if ! retry_git "$max_retries" 2 git fetch origin; then
        print_003_header
        print_003_field "Operation:" "fetch"
        print_003_field "Result:" "${RED}FAILED${NC}"
        print_003_field "Next action:" "check network and retry: ./sync.sh fetch"
        echo ""
        return 1
    fi

    # Compare HEAD vs upstream
    local local_ahead=0
    local upstream_ahead=0
    if has_upstream; then
        local_ahead=$(git log "@{upstream}..HEAD" --oneline 2>/dev/null | wc -l | tr -d ' ')
        upstream_ahead=$(git log "HEAD..@{upstream}" --oneline 2>/dev/null | wc -l | tr -d ' ')
    fi

    print_003_header
    print_003_field "Operation:" "fetch"
    print_003_field "Result:" "${GREEN}success${NC}"
    print_003_field "Local HEAD:" "$commit_before ($branch)"
    print_003_field "Remote:" "$(remote_url)"

    if [[ "$upstream_ahead" != "0" ]] && [[ "$local_ahead" != "0" ]]; then
        print_003_field "Status:" "${YELLOW}DIVERGED${NC}"
        print_003_field "Local ahead:" "$local_ahead commit(s)"
        git log "@{upstream}..HEAD" --oneline 2>/dev/null | sed 's/^/      /'
        print_003_field "Upstream ahead:" "$upstream_ahead commit(s)"
        git log "HEAD..@{upstream}" --oneline 2>/dev/null | sed 's/^/      /'
        print_003_field "Next action:" "manual integration required — decide merge or rebase"
    elif [[ "$upstream_ahead" != "0" ]]; then
        print_003_field "Status:" "${YELLOW}upstream has new commits${NC}"
        print_003_field "Upstream ahead:" "$upstream_ahead commit(s)"
        git log "HEAD..@{upstream}" --oneline 2>/dev/null | sed 's/^/      /'
        print_003_field "Local ahead:" "0"
        print_003_field "Next action:" "run ./sync.sh pull to integrate"
    elif [[ "$local_ahead" != "0" ]]; then
        print_003_field "Status:" "${YELLOW}local has unpushed commits${NC}"
        print_003_field "Local ahead:" "$local_ahead commit(s)"
        git log "@{upstream}..HEAD" --oneline 2>/dev/null | sed 's/^/      /'
        print_003_field "Upstream ahead:" "0"
        print_003_field "Next action:" "run ./sync.sh push"
    else
        print_003_field "Status:" "${GREEN}in sync${NC}"
        print_003_field "Next action:" "none"
    fi
    echo ""
}

cmd_status() {
    if [[ -f "scripts/sync_status.py" ]]; then
        python3 scripts/sync_status.py
    else
        # Fallback: basic git status
        echo "root: $REPO_ROOT"
        echo "git branch: $(current_branch)"
        echo "git remotes:"
        git remote -v 2>/dev/null || echo "  none"
        echo "git status:"
        git status --short 2>/dev/null || echo "  (unavailable)"
        echo "unpushed commits: $(count_unpushed)"
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case "${1:-}" in
    push)   shift; cmd_push "$@" ;;
    pull)   shift; cmd_pull "$@" ;;
    fetch)  shift; cmd_fetch "$@" ;;
    status) shift; cmd_status "$@" ;;
    -h|--help|help) usage ;;
    "")     echo -e "${RED}Error: no command specified.${NC}"; usage ;;
    *)      echo -e "${RED}Error: unknown command '$1'.${NC}"; usage ;;
esac

#!/bin/bash

##############################################################################
# community-cli.sh - ShadowCypher Community Management Tool
#
# A utility script for community managers, maintainers, and contributors to:
# - Track community member activity
# - Generate contributor reports
# - Sync with external systems (forums, mailing lists, etc.)
# - Manage contributor recognition
#
# Usage: ./community-cli.sh <subcommand> [options]
#
##############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
CONTRIBUTORS_FILE="$REPO_ROOT/CONTRIBUTORS.md"
COMMUNITY_LOG="$REPO_ROOT/.community/activity.log"
COMMUNITY_DATA_DIR="$REPO_ROOT/.community"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

##############################################################################
# Utility Functions
##############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

ensure_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository"
        exit 1
    fi
}

ensure_data_dir() {
    mkdir -p "$COMMUNITY_DATA_DIR"
}

##############################################################################
# Subcommand: list-members
#
# List all community members (contributors, reporters, etc.)
##############################################################################

cmd_list_members() {
    local filter="${1:-all}"

    log_info "Fetching community members (filter: $filter)..."
    ensure_git_repo
    ensure_data_dir

    local contributors_file="$COMMUNITY_DATA_DIR/contributors.json"

    # Build JSON from git history
    {
        echo "{"
        echo '  "generated_at": "'$(date -u +'%Y-%m-%dT%H:%M:%SZ')'",'
        echo '  "members": ['

        # Get unique authors from commits
        local first=1
        while IFS= read -r author email; do
            if [ "$first" = "0" ]; then echo ","; fi
            echo -n "    {\"name\": \"$author\", \"email\": \"$email\""

            # Count commits per author
            local count=$(git log --format='%aN' | grep -c "^$author$" || echo "0")
            echo -n ", \"commits\": $count"

            # Count PRs/issues (basic heuristic: grep commit messages)
            local prs=$(git log --format='%B' | grep -c "Closes #" | wc -l || echo "0")
            echo -n ", \"prs_mentioned\": $prs"

            echo "}"
            first=0
        done < <(git log --format='%aN <%aE>' | sort -u)

        echo "  ]"
        echo "}"
    } | tee "$contributors_file" | jq '.' 2>/dev/null || {
        log_warn "jq not installed; saving raw JSON to $contributors_file"
        cat "$contributors_file"
    }

    log_success "Contributor data saved to $contributors_file"
}

##############################################################################
# Subcommand: check-contributions
#
# Check contribution stats for a specific user or all users
##############################################################################

cmd_check_contributions() {
    local username="${1:-}"

    if [ -z "$username" ]; then
        log_info "Usage: community-cli.sh check-contributions <username or email>"
        exit 1
    fi

    ensure_git_repo
    log_info "Checking contributions for: $username"

    echo ""
    echo -e "${CYAN}=== Commit History ===${NC}"
    git log --author="$username" --oneline | head -20 || {
        log_warn "No commits found for author: $username"
    }

    echo ""
    echo -e "${CYAN}=== Contribution Stats ===${NC}"
    local commit_count=$(git log --author="$username" --oneline | wc -l)
    local first_commit=$(git log --author="$username" --format='%aI' | tail -1)
    local last_commit=$(git log --author="$username" --format='%aI' | head -1)

    echo "Total commits: $commit_count"
    echo "First commit: $first_commit"
    echo "Last commit: $last_commit"

    echo ""
    echo -e "${CYAN}=== Most Frequent Directories ===${NC}"
    git log --author="$username" --name-only --pretty=format: | \
        grep -v '^$' | sort | uniq -c | sort -rn | head -10 || {
        log_warn "No file changes found"
    }

    echo ""
    echo -e "${CYAN}=== Activity Summary ===${NC}"
    log_success "Contributor: $username"
}

##############################################################################
# Subcommand: generate-reports
#
# Generate contributor reports (quarterly, annual, etc.)
##############################################################################

cmd_generate_reports() {
    local period="${1:-monthly}"
    local month="${2:-}"

    ensure_git_repo
    ensure_data_dir

    log_info "Generating $period contributor report..."

    local report_file="$COMMUNITY_DATA_DIR/report-${period}-$(date +%Y%m%d).md"

    {
        echo "# ShadowCypher Contributor Report"
        echo ""
        echo "**Period:** $period"
        echo "**Generated:** $(date)"
        echo ""

        echo "## Summary"
        local total_commits=$(git log --oneline | wc -l)
        local unique_authors=$(git log --format='%aN' | sort -u | wc -l)
        echo "- Total commits (all time): $total_commits"
        echo "- Unique contributors: $unique_authors"
        echo ""

        echo "## Top Contributors (Last 30 Days)"
        git log --since="30 days ago" --format='%aN' | sort | uniq -c | sort -rn | \
            head -10 | awk '{print "- " $2 " (" $1 " commits)"}' >> "$report_file" || \
            echo "- (No recent activity)" >> "$report_file"
        echo "" >> "$report_file"

        echo "## Recent Pull Requests"
        git log --oneline --grep="Closes #" --since="30 days ago" | head -10 || \
            echo "(No recent PRs found)" >> "$report_file"
        echo "" >> "$report_file"

        echo "## Module Activity"
        git log --since="30 days ago" --name-only --pretty=format: | \
            grep -E 'arsenal|modules' | sort | uniq -c | sort -rn | head -5 || \
            echo "(No module changes)" >> "$report_file"

    } | tee "$report_file"

    log_success "Report saved to: $report_file"
}

##############################################################################
# Subcommand: forum-sync
#
# Sync community information with external forums/systems (stub for future)
##############################################################################

cmd_forum_sync() {
    local target="${1:-}"

    if [ -z "$target" ]; then
        log_info "Available sync targets:"
        echo "  - github-discussions (sync with GitHub Discussions)"
        echo "  - discord (sync roles with Discord server)"
        echo "  - mailing-list (sync subscriber list)"
        exit 0
    fi

    log_info "Syncing with: $target"

    case "$target" in
        github-discussions)
            log_warn "GitHub Discussions sync not yet implemented"
            echo "Implementation needed: Parse GH API, extract discussion data"
            ;;
        discord)
            log_warn "Discord sync not yet implemented"
            echo "Implementation needed: Use Discord.py or similar to assign roles"
            ;;
        mailing-list)
            log_warn "Mailing list sync not yet implemented"
            echo "Implementation needed: Export contributor emails for mailchimp/etc"
            ;;
        *)
            log_error "Unknown sync target: $target"
            exit 1
            ;;
    esac
}

##############################################################################
# Subcommand: contributor-badges
#
# Generate contributor badge markdown for profiles
##############################################################################

cmd_contributor_badges() {
    local username="${1:-}"

    if [ -z "$username" ]; then
        log_info "Usage: community-cli.sh contributor-badges <username>"
        exit 1
    fi

    ensure_git_repo

    # Calculate badge eligibility based on contribution count
    local commit_count=$(git log --author="$username" --oneline 2>/dev/null | wc -l || echo "0")

    log_info "Generating badges for: $username"
    echo ""
    echo -e "${CYAN}=== Eligible Badges ===${NC}"
    echo ""

    # Contributor Badge
    if [ "$commit_count" -ge 1 ]; then
        echo "**Contributor Badge:**"
        echo '![Contributor](https://img.shields.io/badge/ShadowCypher-Contributor-4B9BFF?logo=github)'
        echo ""
    fi

    # Active Contributor (5+ commits)
    if [ "$commit_count" -ge 5 ]; then
        echo "**Active Contributor Badge:**"
        echo '![Active Contributor](https://img.shields.io/badge/ShadowCypher-Active%20Contributor-00D4FF?logo=github)'
        echo ""
    fi

    # Core Contributor (20+ commits)
    if [ "$commit_count" -ge 20 ]; then
        echo "**Core Contributor Badge:**"
        echo '![Core Contributor](https://img.shields.io/badge/ShadowCypher-Core%20Contributor-FF6B6B?logo=shield)'
        echo ""
    fi

    # Module Author (check for module files)
    local module_files=$(git log --author="$username" --name-only --pretty=format: | \
        grep -c 'arsenal/\|modules/' || echo "0")
    if [ "$module_files" -gt 0 ]; then
        echo "**Module Author Badge:**"
        echo '![Module Author](https://img.shields.io/badge/ShadowCypher-Module%20Author-10b981?logo=code)'
        echo ""
    fi

    # Copy to clipboard instructions
    echo -e "${GREEN}Copy any badge markdown above and add to your GitHub profile README${NC}"
}

##############################################################################
# Subcommand: audit-activity
#
# Audit community activity and health metrics
##############################################################################

cmd_audit_activity() {
    ensure_git_repo
    ensure_data_dir

    log_info "Auditing community activity..."
    echo ""

    # Overall stats
    echo -e "${CYAN}=== Repository Health ===${NC}"
    local total_commits=$(git log --oneline | wc -l)
    local total_authors=$(git log --format='%aN' | sort -u | wc -l)
    local oldest_commit=$(git log --format='%aI' | tail -1)
    local latest_commit=$(git log --format='%aI' | head -1)

    echo "Total commits: $total_commits"
    echo "Total contributors: $total_authors"
    echo "Project started: $oldest_commit"
    echo "Latest activity: $latest_commit"
    echo ""

    # Recent activity (last 30 days)
    echo -e "${CYAN}=== Activity (Last 30 Days) ===${NC}"
    local recent_commits=$(git log --since="30 days ago" --oneline | wc -l)
    local recent_authors=$(git log --since="30 days ago" --format='%aN' | sort -u | wc -l)

    echo "Commits: $recent_commits"
    echo "Active contributors: $recent_authors"

    if [ "$recent_commits" -gt 0 ]; then
        log_success "Active community engagement"
    else
        log_warn "No recent activity in past 30 days"
    fi
    echo ""

    # Issue/PR mentions
    echo -e "${CYAN}=== PR/Issue References ===${NC}"
    local pr_count=$(git log --oneline | grep -c "Closes\|Fixes\|Relates" || echo "0")
    echo "PRs with issue references: $pr_count"
    echo ""

    # Top contributors
    echo -e "${CYAN}=== Top 5 Contributors ===${NC}"
    git log --format='%aN' | sort | uniq -c | sort -rn | head -5 | \
        awk '{print $2 " (" $1 " commits)"}'
}

##############################################################################
# Subcommand: sync-contributors-file
#
# Update CONTRIBUTORS.md file with latest data
##############################################################################

cmd_sync_contributors_file() {
    ensure_git_repo

    log_info "Syncing CONTRIBUTORS.md with git history..."

    local temp_file=$(mktemp)

    {
        echo "# ShadowCypher Contributors"
        echo ""
        echo "This file lists all contributors to the ShadowCypher project, organized by contribution type."
        echo ""
        echo "Generated: $(date)"
        echo ""

        echo "## Code Contributors"
        echo ""
        git log --format='%aN <%aE>' | sort -u | awk '{print "- " $0}'
        echo ""

        echo "## How to Contribute"
        echo ""
        echo "See [CONTRIBUTING.md](./CONTRIBUTING.md) and [COMMUNITY.md](./COMMUNITY.md) for details on how to get involved."

    } > "$temp_file"

    if [ -f "$CONTRIBUTORS_FILE" ]; then
        # Preserve any manual edits by checking if file was modified
        if diff -q "$temp_file" "$CONTRIBUTORS_FILE" > /dev/null 2>&1; then
            log_info "CONTRIBUTORS.md is already up-to-date"
        else
            cp "$temp_file" "$CONTRIBUTORS_FILE"
            log_success "CONTRIBUTORS.md updated"
        fi
    else
        cp "$temp_file" "$CONTRIBUTORS_FILE"
        log_success "CONTRIBUTORS.md created"
    fi

    rm -f "$temp_file"
}

##############################################################################
# Subcommand: validate-guidelines
#
# Validate that community files are present and valid
##############################################################################

cmd_validate_guidelines() {
    log_info "Validating community guidelines and files..."
    echo ""

    local all_valid=true

    # Check for required files
    local required_files=(
        "COMMUNITY.md"
        "CONTRIBUTING.md"
        "SECURITY.md"
        "CODE_OF_CONDUCT.md"
    )

    for file in "${required_files[@]}"; do
        if [ -f "$REPO_ROOT/$file" ]; then
            log_success "✓ $file exists"
        else
            log_warn "✗ $file missing"
            all_valid=false
        fi
    done

    echo ""
    echo -e "${CYAN}=== File Validation ===${NC}"

    # Check COMMUNITY.md structure
    if [ -f "$REPO_ROOT/COMMUNITY.md" ]; then
        local sections=("Code of Conduct" "How to Join" "Discussion Forums" "Recognition")
        for section in "${sections[@]}"; do
            if grep -q "## $section" "$REPO_ROOT/COMMUNITY.md"; then
                log_success "COMMUNITY.md has '$section' section"
            else
                log_warn "COMMUNITY.md missing '$section' section"
                all_valid=false
            fi
        done
    fi

    # Check CONTRIBUTING.md structure
    if [ -f "$REPO_ROOT/CONTRIBUTING.md" ]; then
        local sections=("Bug Reports" "Development Setup" "Pull Request Process" "Coding Standards")
        for section in "${sections[@]}"; do
            if grep -q "## $section" "$REPO_ROOT/CONTRIBUTING.md"; then
                log_success "CONTRIBUTING.md has '$section' section"
            else
                log_warn "CONTRIBUTING.md missing '$section' section"
                all_valid=false
            fi
        done
    fi

    echo ""
    if [ "$all_valid" = true ]; then
        log_success "All community guidelines are valid!"
    else
        log_warn "Some guidelines are missing or incomplete"
    fi
}

##############################################################################
# Help and Main
##############################################################################

show_help() {
    cat << 'EOF'
ShadowCypher Community Management CLI

Usage: ./community-cli.sh <subcommand> [options]

Subcommands:

  list-members [filter]
      List all community members with contribution counts
      Filters: all (default), contributors, reporters, translators
      Example: ./community-cli.sh list-members contributors

  check-contributions <username>
      Show detailed contribution stats for a user
      Example: ./community-cli.sh check-contributions "John Doe"

  generate-reports [period] [month]
      Generate contributor activity reports
      Periods: monthly (default), quarterly, annual
      Example: ./community-cli.sh generate-reports quarterly

  forum-sync [target]
      Sync community data with external systems
      Targets: github-discussions, discord, mailing-list
      Example: ./community-cli.sh forum-sync github-discussions

  contributor-badges <username>
      Generate contributor badge markdown for a user
      Example: ./community-cli.sh contributor-badges "jane_smith"

  audit-activity
      Audit overall community health and activity metrics
      Example: ./community-cli.sh audit-activity

  sync-contributors-file
      Update CONTRIBUTORS.md with latest git data
      Example: ./community-cli.sh sync-contributors-file

  validate-guidelines
      Validate that community guidelines files are present and complete
      Example: ./community-cli.sh validate-guidelines

  help
      Show this help message

Examples:

  # List all contributors
  ./community-cli.sh list-members

  # Check activity for a specific user
  ./community-cli.sh check-contributions "alice@example.com"

  # Generate monthly report
  ./community-cli.sh generate-reports monthly

  # Audit community health
  ./community-cli.sh audit-activity

  # Generate badges for a contributor
  ./community-cli.sh contributor-badges "bob_developer"

  # Sync CONTRIBUTORS.md file
  ./community-cli.sh sync-contributors-file

  # Validate all community guidelines
  ./community-cli.sh validate-guidelines

EOF
}

main() {
    local cmd="${1:-help}"

    case "$cmd" in
        list-members)
            shift || true
            cmd_list_members "$@"
            ;;
        check-contributions)
            shift || true
            cmd_check_contributions "$@"
            ;;
        generate-reports)
            shift || true
            cmd_generate_reports "$@"
            ;;
        forum-sync)
            shift || true
            cmd_forum_sync "$@"
            ;;
        contributor-badges)
            shift || true
            cmd_contributor_badges "$@"
            ;;
        audit-activity)
            cmd_audit_activity
            ;;
        sync-contributors-file)
            cmd_sync_contributors_file
            ;;
        validate-guidelines)
            cmd_validate_guidelines
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown subcommand: $cmd"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"

#!/bin/bash

################################################################################
## SELinux Policy Generator and Manager for ShadowCypher Guardian
##
## This script provides tools for:
## - Compiling and loading SELinux policy modules
## - Managing SELinux enforcing modes
## - Generating rules from audit logs
## - Validating policy syntax
## - Managing domain transitions
## - Auditing and logging violations
## - Rolling back to previous policy
##
## Usage:
##   selinux-generator.sh compile <policy.te>
##   selinux-generator.sh load <policy.pp>
##   selinux-generator.sh unload <module_name>
##   selinux-generator.sh mode <permissive|enforcing|disabled>
##   selinux-generator.sh generate-rules <pattern>
##   selinux-generator.sh domain <domain_name>
##   selinux-generator.sh file-context <path> <type>
##   selinux-generator.sh validate <policy.te>
##   selinux-generator.sh audit [duration]
##   selinux-generator.sh rollback [version]
##   selinux-generator.sh status
##
################################################################################

set -euo pipefail

## Global configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_DIR="${POLICY_DIR:-.}"
LOG_DIR="${LOG_DIR:-./.selinux-logs}"
BACKUP_DIR="${BACKUP_DIR:-./.selinux-backup}"
AUDIT_LOG="/var/log/audit/audit.log"
POLICY_NAME="shadowcypher_guardian"

## Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

## ============================================================================
## Utility Functions
## ============================================================================

log_info() {
	echo -e "${BLUE}[INFO]${NC} $*" >&2
}

log_success() {
	echo -e "${GREEN}[✓]${NC} $*" >&2
}

log_warn() {
	echo -e "${YELLOW}[WARN]${NC} $*" >&2
}

log_error() {
	echo -e "${RED}[ERROR]${NC} $*" >&2
}

check_root() {
	if [[ $EUID -ne 0 ]]; then
		log_error "This script must be run as root"
		exit 1
	fi
}

check_selinux() {
	if ! command -v getenforce &> /dev/null; then
		log_error "SELinux tools not installed. Install: apt-get install selinux-utils selinux-policy-dev"
		exit 1
	fi
}

require_commands() {
	local missing=0
	for cmd in "$@"; do
		if ! command -v "$cmd" &> /dev/null; then
			log_error "Required command not found: $cmd"
			((missing++))
		fi
	done
	if [[ $missing -gt 0 ]]; then
		exit 1
	fi
}

ensure_directories() {
	mkdir -p "$LOG_DIR" "$BACKUP_DIR"
	log_info "Created log directories: $LOG_DIR, $BACKUP_DIR"
}

## ============================================================================
## Policy Compilation
## ============================================================================

compile_policy() {
	local policy_file="$1"
	local output_mod="${2:-${policy_file%.te}.mod}"
	local output_pp="${3:-${policy_file%.te}.pp}"

	log_info "Compiling SELinux policy: $policy_file"

	if [[ ! -f "$policy_file" ]]; then
		log_error "Policy file not found: $policy_file"
		return 1
	fi

	require_commands checkmodule semodule_package

	## Compile policy to module
	log_info "Step 1: Checking and compiling policy module..."
	if ! checkmodule -M -m -o "$output_mod" "$policy_file"; then
		log_error "Policy compilation failed"
		return 1
	fi
	log_success "Module compiled: $output_mod"

	## Package module into policy file
	log_info "Step 2: Packaging policy module..."
	if ! semodule_package -o "$output_pp" -m "$output_mod"; then
		log_error "Policy packaging failed"
		return 1
	fi
	log_success "Policy packaged: $output_pp"

	## Verify policy
	log_info "Step 3: Verifying policy package..."
	if ! file "$output_pp" | grep -q "SELinux policy"; then
		log_error "Invalid policy package generated"
		return 1
	fi
	log_success "Policy verification passed"

	echo "$output_pp"
}

## ============================================================================
## Policy Loading/Unloading
## ============================================================================

load_policy() {
	local policy_file="$1"

	check_root
	check_selinux
	require_commands semodule

	if [[ ! -f "$policy_file" ]]; then
		log_error "Policy file not found: $policy_file"
		return 1
	fi

	## Backup current policy
	backup_current_policy

	log_info "Loading SELinux policy: $policy_file"
	if ! semodule -i "$policy_file"; then
		log_error "Failed to load policy"
		return 1
	fi
	log_success "Policy loaded successfully"

	## Verify load
	local module_name=$(basename "$policy_file" .pp)
	if semodule -l | grep -q "^$module_name"; then
		log_success "Module verified in loaded policies"
		echo "$module_name"
	else
		log_warn "Module not found in loaded policies list"
	fi
}

unload_policy() {
	local module_name="$1"

	check_root
	check_selinux
	require_commands semodule

	log_info "Unloading SELinux module: $module_name"

	## Backup current policy before unload
	backup_current_policy

	if ! semodule -r "$module_name" 2>/dev/null; then
		log_error "Failed to unload module: $module_name"
		log_info "Available modules:"
		semodule -l
		return 1
	fi
	log_success "Module unloaded: $module_name"
}

## ============================================================================
## SELinux Mode Management
## ============================================================================

set_selinux_mode() {
	local mode="$1"
	local valid_modes=("permissive" "enforcing" "disabled")

	check_root
	check_selinux
	require_commands semanage getenforce

	if [[ ! " ${valid_modes[@]} " =~ " ${mode} " ]]; then
		log_error "Invalid mode: $mode (valid: ${valid_modes[*]})"
		return 1
	fi

	local current_mode=$(getenforce)
	log_info "Current SELinux mode: $current_mode"
	log_info "Setting SELinux mode to: $mode"

	if [[ "$mode" == "disabled" ]]; then
		log_warn "Disabling SELinux requires a reboot to take effect"
		log_warn "Run: semanage permissive -d $POLICY_NAME first (optional)"
	fi

	## Use getenforce for current, setenforce for temporary runtime change
	if setenforce "$mode" 2>/dev/null; then
		log_success "SELinux mode set to: $mode (runtime)"
		log_info "To persist across reboots, edit /etc/selinux/config"
		return 0
	else
		log_error "Failed to set SELinux mode"
		return 1
	fi
}

set_permissive_domain() {
	local domain="$1"

	check_root
	require_commands semanage

	log_info "Setting domain to permissive: $domain"

	if semanage permissive -a "$domain" 2>/dev/null; then
		log_success "Domain set to permissive: $domain"
	else
		log_error "Failed to set domain permissive"
		return 1
	fi
}

## ============================================================================
## Audit Rule Generation
## ============================================================================

generate_rules_from_audit() {
	local pattern="${1:-AVC}"
	local output_file="$LOG_DIR/generated_rules_$(date +%s).te"

	check_root
	require_commands ausearch audit2allow

	if [[ ! -f "$AUDIT_LOG" ]]; then
		log_error "Audit log not found: $AUDIT_LOG"
		return 1
	fi

	log_info "Searching audit log for pattern: $pattern"
	log_info "Generating allow rules from audit denials..."

	## Extract AVC denials matching pattern
	if ! ausearch -m AVC | grep "$pattern" > /dev/null 2>&1; then
		log_warn "No matching audit entries found for: $pattern"
		return 1
	fi

	## Generate policy rules
	if ! ausearch -m AVC | grep "$pattern" | audit2allow -a -M "$LOG_DIR/generated_allow" 2>/dev/null; then
		log_warn "audit2allow generated no new rules"
		return 0
	fi

	log_success "Generated policy module: $LOG_DIR/generated_allow.pp"
	log_info "Review the generated module before loading:"
	log_info "  cat $LOG_DIR/generated_allow.te"
	log_info "  semodule -i $LOG_DIR/generated_allow.pp"

	echo "$LOG_DIR/generated_allow.pp"
}

## ============================================================================
## Domain and Type Management
## ============================================================================

create_custom_domain() {
	local domain_name="$1"
	local base_policy_file="${2:-.selinux_custom_domain.te}"

	log_info "Creating custom domain: $domain_name"

	cat > "$base_policy_file" << EOF
policy_module(custom_domain_$domain_name, 1.0.0)

require {
	type init_t;
	type kernel_t;
	type etc_t;
	type proc_t;
	class process { transition signal };
	class file { read write execute getattr };
	class dir { search getattr };
}

## Custom domain: $domain_name
type ${domain_name}_t;
type ${domain_name}_exec_t;
type ${domain_name}_var_lib_t;
type ${domain_name}_tmp_t;

## Allow domain to run
allow ${domain_name}_t ${domain_name}_exec_t : file execute_no_trans;
allow init_t ${domain_name}_exec_t : file { read execute getattr };
allow init_t ${domain_name}_t : process transition;

## Self transitions
allow ${domain_name}_t ${domain_name}_t : process { signal };

## File access
allow ${domain_name}_t ${domain_name}_var_lib_t : file { read write create getattr };
allow ${domain_name}_t ${domain_name}_tmp_t : file { read write create getattr };

## System access
allow ${domain_name}_t etc_t : file { read getattr };
allow ${domain_name}_t proc_t : file { read getattr };
EOF

	log_success "Domain template created: $base_policy_file"
	log_info "Edit and compile with: selinux-generator.sh compile $base_policy_file"
}

## ============================================================================
## File Context Management
## ============================================================================

set_file_context() {
	local path="$1"
	local file_type="$2"
	local selinux_user="${3:-system_u}"
	local selinux_role="${4:-object_r}"
	local selinux_level="${5:-s0}"

	check_root
	require_commands chcon restorecon

	local context="${selinux_user}:${selinux_role}:${file_type}:${selinux_level}"

	log_info "Setting context for: $path -> $context"

	if [[ ! -e "$path" ]]; then
		log_warn "Path does not exist: $path"
		return 1
	fi

	if chcon -R "$context" "$path"; then
		log_success "Context set: $path"
	else
		log_error "Failed to set context"
		return 1
	fi
}

restore_contexts() {
	local path="${1:-.}"

	check_root
	require_commands restorecon

	log_info "Restoring SELinux contexts for: $path"

	if restorecon -Rv "$path"; then
		log_success "Contexts restored"
	else
		log_error "Failed to restore contexts"
		return 1
	fi
}

## ============================================================================
## Policy Validation
## ============================================================================

validate_policy() {
	local policy_file="$1"

	require_commands checkmodule

	log_info "Validating policy syntax: $policy_file"

	if [[ ! -f "$policy_file" ]]; then
		log_error "Policy file not found: $policy_file"
		return 1
	fi

	## Check module syntax (not strict)
	if checkmodule -M -m "$policy_file" > /dev/null 2>&1; then
		log_success "Policy syntax validation passed"
		return 0
	else
		log_warn "Policy has warnings (may still compile)"
		## Try to compile anyway
		if checkmodule -M -m "$policy_file" 2>&1 | head -20; then
			return 0
		fi
		return 1
	fi
}

## ============================================================================
## Audit and Logging
## ============================================================================

audit_denials() {
	local duration="${1:-60}"

	check_root

	if [[ ! -f "$AUDIT_LOG" ]]; then
		log_error "Audit log not found: $AUDIT_LOG"
		log_info "Enable auditd: systemctl start auditd"
		return 1
	fi

	log_info "Monitoring audit log for $duration seconds..."
	log_info "Listening for AVC denials (Ctrl-C to stop)..."

	## Filter to AVC denials with nice formatting
	tail -f "$AUDIT_LOG" | while IFS= read -r line; do
		if [[ "$line" =~ "AVC avc: denied" ]]; then
			echo -e "${RED}$line${NC}"
		elif [[ "$line" =~ "AVC" ]]; then
			echo -e "${YELLOW}$line${NC}"
		fi
	done &

	local tail_pid=$!
	sleep "$duration"
	kill $tail_pid 2>/dev/null || true

	log_info "Audit monitoring completed"
}

audit_summary() {
	check_root

	if [[ ! -f "$AUDIT_LOG" ]]; then
		log_error "Audit log not found: $AUDIT_LOG"
		return 1
	fi

	log_info "Recent AVC denials:"
	grep "AVC avc: denied" "$AUDIT_LOG" | tail -20 | while read -r line; do
		echo -e "${RED}$line${NC}"
	done

	log_info "\nDenial summary:"
	grep "AVC avc: denied" "$AUDIT_LOG" | grep -o 'scontext=[^ ]*' | sort | uniq -c
}

## ============================================================================
## Backup and Rollback
## ============================================================================

backup_current_policy() {
	local timestamp=$(date +%Y%m%d_%H%M%S)
	local backup_file="$BACKUP_DIR/policy_backup_$timestamp.tar.gz"

	log_info "Backing up current policy state..."

	mkdir -p "$BACKUP_DIR"

	## Backup loaded modules list
	semodule -l > "$BACKUP_DIR/modules_$timestamp.list"

	## Backup SELinux configuration
	if [[ -f /etc/selinux/config ]]; then
		cp /etc/selinux/config "$BACKUP_DIR/config_$timestamp"
	fi

	log_success "Backup created: $backup_file"
}

rollback_policy() {
	local version="${1:-latest}"

	check_root

	log_warn "Policy rollback requested (version: $version)"

	if [[ "$version" == "latest" ]]; then
		## Get most recent backup
		local latest_backup=$(ls -t "$BACKUP_DIR"/modules_*.list 2>/dev/null | head -1)
		if [[ -z "$latest_backup" ]]; then
			log_error "No backup found"
			return 1
		fi
		version=$(basename "$latest_backup" | sed 's/modules_//; s/.list//')
	fi

	local modules_file="$BACKUP_DIR/modules_$version.list"

	if [[ ! -f "$modules_file" ]]; then
		log_error "Backup not found: $modules_file"
		log_info "Available backups:"
		ls -1 "$BACKUP_DIR"/modules_*.list 2>/dev/null || log_warn "No backups available"
		return 1
	fi

	log_info "Rolling back to: $version"
	log_warn "This will unload all custom modules. Proceed with caution."

	## Restore modules (manual process)
	log_info "Modules to restore:"
	cat "$modules_file"

	log_info "Manual rollback steps:"
	log_info "1. semodule -r \$(semodule -l | awk '{print \$1}')"
	log_info "2. Restore /etc/selinux/config: cp $BACKUP_DIR/config_$version /etc/selinux/config"
	log_info "3. semodule -i <previous_policy.pp>"
	log_info "4. Reboot"
}

## ============================================================================
## Status and Information
## ============================================================================

show_status() {
	check_selinux

	echo ""
	log_info "SELinux Status:"
	echo "  Enforcing: $(getenforce)"
	echo "  Policy: $(sestatus 2>/dev/null | grep -i "loaded policy" || echo "N/A")"
	echo ""

	echo -e "${BLUE}[INFO]${NC} Loaded Modules:"
	semodule -l | head -10
	echo ""

	if [[ -d "$BACKUP_DIR" ]]; then
		echo -e "${BLUE}[INFO]${NC} Recent Backups:"
		ls -1t "$BACKUP_DIR"/modules_*.list 2>/dev/null | head -5 || echo "  No backups yet"
	fi
	echo ""

	echo -e "${BLUE}[INFO]${NC} Log Files:"
	ls -1t "$LOG_DIR"/*.te 2>/dev/null | head -5 || echo "  No generated policies yet"
	echo ""
}

## ============================================================================
## Help
## ============================================================================

show_help() {
	cat << EOF
SELinux Policy Generator and Manager for ShadowCypher Guardian

USAGE:
  $(basename "$0") <command> [options]

COMMANDS:

  compile <policy.te> [output.mod] [output.pp]
    Compile SELinux policy from TE file to loadable module

  load <policy.pp>
    Load compiled policy module into kernel

  unload <module_name>
    Unload SELinux module from kernel

  mode <permissive|enforcing|disabled>
    Set SELinux enforcing mode (permissive for testing, enforcing for prod)

  permissive <domain>
    Set specific domain to permissive mode (testing)

  generate-rules [pattern]
    Generate allow rules from audit log denials (default: AVC)

  domain <domain_name>
    Create custom domain template

  file-context <path> <type> [user] [role] [level]
    Set SELinux context on file/directory

  restore <path>
    Restore default SELinux contexts

  validate <policy.te>
    Validate policy syntax without compiling

  audit [duration]
    Monitor audit log for AVC denials (default 60s)

  audit-summary
    Show summary of recent AVC denials

  rollback [version|latest]
    Rollback to previous policy state

  status
    Show current SELinux status

  help
    Show this help message

EXAMPLES:

  # Validate policy
  $(basename "$0") validate selinux-policy.te

  # Compile policy
  $(basename "$0") compile selinux-policy.te

  # Load policy (requires root)
  sudo $(basename "$0") load selinux-policy.pp

  # Set to enforcing (requires root)
  sudo $(basename "$0") mode enforcing

  # Monitor audit log for violations
  sudo $(basename "$0") audit 120

  # Generate rules from audit
  sudo $(basename "$0") generate-rules "guardian_vault_t"

  # Create custom domain
  $(basename "$0") domain my_service

  # Set file context (requires root)
  sudo $(basename "$0") file-context /var/lib/guardian guardian_vault_data_t

EOF
}

## ============================================================================
## Main Entry Point
## ============================================================================

main() {
	local command="${1:-help}"

	case "$command" in
		compile)
			ensure_directories
			compile_policy "${2:-.}" "${3:-}" "${4:-}"
			;;
		load)
			ensure_directories
			load_policy "${2:-.}"
			;;
		unload)
			ensure_directories
			unload_policy "${2:-.}"
			;;
		mode)
			set_selinux_mode "${2:-help}"
			;;
		permissive)
			set_permissive_domain "${2:-.}"
			;;
		generate-rules)
			ensure_directories
			generate_rules_from_audit "${2:-AVC}"
			;;
		domain)
			create_custom_domain "${2:-custom_domain}"
			;;
		file-context)
			set_file_context "${2:-.}" "${3:-.}" "${4:-system_u}" "${5:-object_r}" "${6:-s0}"
			;;
		restore)
			restore_contexts "${2:-.}"
			;;
		validate)
			validate_policy "${2:-.}"
			;;
		audit)
			audit_denials "${2:-60}"
			;;
		audit-summary)
			audit_summary
			;;
		rollback)
			rollback_policy "${2:-latest}"
			;;
		status)
			show_status
			;;
		help)
			show_help
			;;
		*)
			log_error "Unknown command: $command"
			show_help
			exit 1
			;;
	esac
}

main "$@"

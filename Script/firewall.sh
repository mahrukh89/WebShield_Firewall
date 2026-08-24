#!/bin/bash
#
# WebShield Firewall - firewall.sh
# Core packet-filtering engine built on iptables.
# Provides init, status, rule management, blocking, and logging.
#
# Usage:
#   sudo ./firewall.sh init
#   sudo ./firewall.sh status
#   sudo ./firewall.sh allow-port <port> [tcp|udp]
#   sudo ./firewall.sh block-ip <ip>
#   sudo ./firewall.sh unblock-ip <ip>
#   sudo ./firewall.sh block-port <port> [tcp|udp]
#   sudo ./firewall.sh list
#   sudo ./firewall.sh list-json
#   sudo ./firewall.sh flush
#   sudo ./firewall.sh save
#   sudo ./firewall.sh restore

set -euo pipefail

LOG_FILE="/var/log/webshield_firewall.log"
RULES_BACKUP="/etc/webshield/rules.v4"
LAN_IF="eth1"
WAN_IF="eth0"

# ---------- helpers ----------

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Error: must be run as root (use sudo)." >&2
    exit 1
  fi
}

log_action() {
  local msg="$1"
  mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
  echo "$(date '+%Y-%m-%d %H:%M:%S') | $msg" >> "$LOG_FILE"
}

validate_ip() {
  local ip="$1"
  if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "Error: '$ip' is not a valid IPv4 address." >&2
    exit 1
  fi
}

validate_port() {
  local port="$1"
  if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
    echo "Error: '$port' is not a valid port (1-65535)." >&2
    exit 1
  fi
}

# ---------- core actions ----------

init_firewall() {
  require_root

  # default policies: deny by default
  iptables -P INPUT DROP
  iptables -P FORWARD DROP
  iptables -P OUTPUT ACCEPT

  iptables -F
  iptables -X

  # loopback always allowed
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A OUTPUT -o lo -j ACCEPT

  # keep existing connections alive
  iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

  # baseline services
  iptables -A INPUT -p tcp --dport 22  -j ACCEPT   # SSH
  iptables -A INPUT -p tcp --dport 80  -j ACCEPT   # HTTP
  iptables -A INPUT -p tcp --dport 443 -j ACCEPT   # HTTPS

  # anti scan / spoof protections
  iptables -A INPUT -p tcp --tcp-flags ALL NONE -j DROP        # null scan
  iptables -A INPUT -p tcp --tcp-flags SYN,FIN SYN,FIN -j DROP # syn-fin
  iptables -A INPUT -p tcp --tcp-flags ALL FIN,SYN,RST,ACK -j DROP

  # LAN <-> WAN forwarding, stateful
  iptables -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT
  iptables -A FORWARD -i "$WAN_IF" -o "$LAN_IF" -m state --state ESTABLISHED,RELATED -j ACCEPT

  # NAT so LAN clients can reach the internet
  iptables -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE

  # log dropped packets before the implicit DROP (rate-limited)
  iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "WEBSHIELD-DROP: " --log-level 4

  log_action "Firewall initialized with default policy DROP (INPUT/FORWARD)."
  echo "Firewall initialized."
}

allow_port() {
  local port="$1" proto="${2:-tcp}"
  require_root; validate_port "$port"
  iptables -A INPUT -p "$proto" --dport "$port" -j ACCEPT
  log_action "ALLOW port $port/$proto"
  echo "Allowed $proto/$port"
}

block_port() {
  local port="$1" proto="${2:-tcp}"
  require_root; validate_port "$port"
  iptables -I INPUT 1 -p "$proto" --dport "$port" -j DROP
  log_action "BLOCK port $port/$proto"
  echo "Blocked $proto/$port"
}

block_ip() {
  local ip="$1"
  require_root; validate_ip "$ip"
  iptables -I INPUT 1 -s "$ip" -j DROP -m comment --comment "Blocked IP"
  log_action "BLOCK ip $ip"
  echo "Blocked $ip"
}

unblock_ip() {
  local ip="$1"
  require_root; validate_ip "$ip"
  iptables -D INPUT -s "$ip" -j DROP -m comment --comment "Blocked IP" 2>/dev/null \
    || { echo "No matching block rule found for $ip"; return 1; }
  log_action "UNBLOCK ip $ip"
  echo "Unblocked $ip"
}

list_rules() {
  iptables -L -n -v --line-numbers
}

# machine-readable output the Flask app can parse
list_rules_json() {
  echo "["
  local first=1
  iptables -S INPUT | tail -n +2 | while read -r rule; do
    [[ $first -eq 0 ]] && echo ","
    first=0
    printf '  {"chain": "INPUT", "rule": "%s"}' "$(echo "$rule" | sed 's/"/\\"/g')"
  done
  echo ""
  echo "]"
}

status() {
  echo "=== WebShield Firewall Status ==="
  echo "Policy INPUT:   $(iptables -L INPUT   -n | head -1)"
  echo "Policy FORWARD: $(iptables -L FORWARD -n | head -1)"
  echo "Policy OUTPUT:  $(iptables -L OUTPUT  -n | head -1)"
  echo "Active rules (INPUT): $(iptables -S INPUT | tail -n +2 | wc -l)"
  echo "IP forwarding: $(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo unknown)"
}

flush_all() {
  require_root
  iptables -F
  iptables -X
  iptables -t nat -F
  iptables -P INPUT ACCEPT
  iptables -P FORWARD ACCEPT
  log_action "Flushed all rules, policies reset to ACCEPT."
  echo "All rules flushed."
}

save_rules() {
  require_root
  mkdir -p "$(dirname "$RULES_BACKUP")"
  iptables-save > "$RULES_BACKUP"
  log_action "Rules saved to $RULES_BACKUP"
  echo "Saved to $RULES_BACKUP"
}

restore_rules() {
  require_root
  [[ -f "$RULES_BACKUP" ]] || { echo "No backup found at $RULES_BACKUP"; exit 1; }
  iptables-restore < "$RULES_BACKUP"
  log_action "Rules restored from $RULES_BACKUP"
  echo "Restored from $RULES_BACKUP"
}

# ---------- dispatch ----------

case "${1:-}" in
  init)         init_firewall ;;
  status)       status ;;
  allow-port)   allow_port "${2:?port required}" "${3:-tcp}" ;;
  block-port)   block_port "${2:?port required}" "${3:-tcp}" ;;
  block-ip)     block_ip "${2:?ip required}" ;;
  unblock-ip)   unblock_ip "${2:?ip required}" ;;
  list)         list_rules ;;
  list-json)    list_rules_json ;;
  flush)        flush_all ;;
  save)         save_rules ;;
  restore)      restore_rules ;;
  *)
    cat <<EOF
WebShield Firewall - firewall.sh

Usage: $0 <command> [args]

Commands:
  init                       Set up default DROP policy + baseline rules
  status                     Show current policy and rule counts
  allow-port <port> [proto]  Allow inbound traffic on a port (default tcp)
  block-port <port> [proto]  Block inbound traffic on a port
  block-ip <ip>              Block all traffic from an IP
  unblock-ip <ip>            Remove a block rule for an IP
  list                       List active rules (human readable)
  list-json                  List active rules (JSON, for the web UI)
  flush                      Remove all rules, reset policy to ACCEPT
  save                       Persist current rules to $RULES_BACKUP
  restore                    Reload rules from $RULES_BACKUP
EOF
    exit 1
    ;;
esac

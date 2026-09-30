#!/usr/bin/env bash
# ============================================================================
# Perennia v4 — deployment check. Read-only: changes nothing.
#
#   ./diagnose.sh                 local checks only
#   ./diagnose.sh 169.58.13.213   also test http://IP:PORT from this server
#
# Walks the path a browser request takes — pm2 process → listening
# socket → app on 127.0.0.1 → app on the public IP → host firewall —
# and prints where it breaks, with the command that fixes it.
# ============================================================================
set -uo pipefail

APP_NAME="perennia4"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/backend/.env"
PUBLIC_IP="${1:-}"
HINT_IP="${PUBLIC_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
HINT_IP="${HINT_IP:-<server-ip>}"

pass() { printf '  \033[1;32mOK\033[0m    %s\n' "$1"; }
bad()  { printf '  \033[1;31mFAIL\033[0m  %s\n' "$1"; [[ -n "${2:-}" ]] && printf '        → %s\n' "$2"; }
note() { printf '  \033[1;33m--\033[0m    %s\n' "$1"; }
env_get() { [[ -f "$ENV_FILE" ]] && grep -m1 "^$1=" "$ENV_FILE" | cut -d= -f2- || true; }

PORT="$(env_get PORT)"; PORT="${PORT:-5960}"
HOST="$(env_get HOST)"; HOST="${HOST:-127.0.0.1}"
root() { if [[ $EUID -eq 0 ]]; then "$@"; else sudo -n "$@" 2>/dev/null; fi; }

echo "Perennia v4 deployment check (port $PORT)"

echo; echo "1. Process"
if command -v pm2 >/dev/null 2>&1; then
    status="$(pm2 jlist 2>/dev/null | python3 -c 'import json,sys
for p in json.load(sys.stdin):
    if p["name"]==sys.argv[1]: print(p["pm2_env"]["status"], p["pm2_env"].get("restart_time",0))' "$APP_NAME" 2>/dev/null)"
    if [[ "$status" == online* ]]; then pass "pm2 '$APP_NAME' is online (restarts: ${status#* })"
    elif [[ -n "$status" ]]; then bad "pm2 '$APP_NAME' is ${status%% *}" "pm2 logs $APP_NAME --lines 50"
    else bad "no pm2 process named '$APP_NAME'" "./install.sh${PUBLIC_IP:+ --public-ip=$PUBLIC_IP}"; fi
else
    bad "pm2 not installed for this user" "run as the user that ran install.sh"
fi

echo; echo "2. Listening socket"
listen="$(ss -ltn 2>/dev/null | awk -v p=":$PORT" '$4 ~ p"$" {print $4}' | sort -u | tr '\n' ' ')"
if [[ -z "$listen" ]]; then
    bad "nothing is listening on port $PORT" "pm2 logs $APP_NAME --lines 50"
elif [[ "$listen" =~ (0\.0\.0\.0|\*|\[::\]): ]]; then
    pass "listening on all interfaces ($listen)"
else
    bad "listening on $listen only — unreachable from other machines" "./install.sh --public-ip=$HINT_IP   (or put nginx in front)"
fi
note "backend/.env: HOST=$HOST PORT=$PORT ENVIRONMENT=$(env_get ENVIRONMENT) COOKIE_SECURE=$(env_get COOKIE_SECURE)"

echo; echo "3. App on this server"
check_url() {   # label url expect
    local code body
    body="$(curl -sS -m 8 -w '\n%{http_code}' "$2" 2>&1)"; code="${body##*$'\n'}"
    if [[ "$code" == 200 && "$body" == *"$3"* ]]; then pass "$1  $2 → 200"; return 0; fi
    bad "$1  $2 → ${code:-no answer}" ; return 1
}
LOCAL_OK=true
check_url "health " "http://127.0.0.1:$PORT/api/health" '"ok"' || LOCAL_OK=false
check_url "site   " "http://127.0.0.1:$PORT/"            'id="root"' || LOCAL_OK=false
check_url "admin  " "http://127.0.0.1:$PORT/admin"       'id="root"' || LOCAL_OK=false
check_url "sitemap" "http://127.0.0.1:$PORT/sitemap.xml" '<urlset' || true
$LOCAL_OK || note "fix this first: pm2 logs $APP_NAME --lines 50"

if [[ -n "$PUBLIC_IP" ]]; then
    echo; echo "4. Public address"
    if check_url "health " "http://$PUBLIC_IP:$PORT/api/health" '"ok"'; then
        check_url "site   " "http://$PUBLIC_IP:$PORT/" 'id="root"'
        if [[ "$(env_get COOKIE_SECURE)" == "true" ]]; then
            bad "COOKIE_SECURE=true: admin login needs HTTPS and will fail on http://$PUBLIC_IP:$PORT" "./install.sh --public-ip=$PUBLIC_IP"
        fi
    elif $LOCAL_OK; then
        note "works on 127.0.0.1 but not on $PUBLIC_IP — bind address or a firewall is in the way"
        ip -o addr 2>/dev/null | grep -qw "$PUBLIC_IP" \
            || note "$PUBLIC_IP is not on any interface here (normal behind cloud NAT; a failure here can also be the provider not allowing hairpin traffic — test from your own machine too)"
    fi
fi

echo; echo "5. Host firewall"
if command -v ufw >/dev/null 2>&1 && ufw_out="$(root ufw status)"; then
    if [[ "$ufw_out" != *"Status: active"* ]]; then pass "ufw inactive"
    elif grep -qE "^$PORT(/tcp)?[[:space:]]+ALLOW" <<<"$ufw_out"; then pass "ufw allows $PORT/tcp"
    else bad "ufw is active and does not allow $PORT/tcp" "sudo ufw allow $PORT/tcp"; fi
elif command -v firewall-cmd >/dev/null 2>&1 && root firewall-cmd --state >/dev/null 2>&1; then
    if root firewall-cmd --list-ports | grep -qw "$PORT/tcp"; then pass "firewalld allows $PORT/tcp"
    else bad "firewalld does not allow $PORT/tcp" "sudo firewall-cmd --permanent --add-port=$PORT/tcp && sudo firewall-cmd --reload"; fi
else
    note "no ufw/firewalld status available (not installed, or needs sudo)"
fi
# Rules are searched in every chain: ufw/firewalld keep their ACCEPTs in
# their own chains (ufw-user-input, …) behind a default-DROP INPUT policy.
if command -v iptables >/dev/null 2>&1 && rules="$(root iptables -S)"; then
    if [[ "$rules" == *"-P INPUT DROP"* || "$rules" == *"-P INPUT REJECT"* ]] \
        && ! grep -qE -- "--dport(s)? ([0-9,:]*[,])?$PORT([,:][0-9,:]*)? .*-j ACCEPT" <<<"$rules"; then
        bad "iptables drops incoming traffic by default and no chain accepts port $PORT" "sudo iptables -I INPUT -p tcp --dport $PORT -j ACCEPT"
    fi
fi
note "your hosting provider's firewall (control panel / security group) is outside this server: allow inbound TCP $PORT there too if it has one"

echo; echo "From your own computer:  curl -i http://$HINT_IP:$PORT/api/health"

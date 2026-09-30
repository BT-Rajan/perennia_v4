#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================================
# Perennia v4 — installer / deployer (Linux).
#
# Run from the root of this checkout. Safe to re-run: every step is
# idempotent, so the same command both installs and redeploys.
#
#   - MySQL/MariaDB: creates database `perennia4` (utf8mb4) and grants
#     user `app_user` full access to it. If `app_user` does not exist it
#     is created; if it DOES exist (shared with other apps on this
#     server) its password is never changed — the script only adds the
#     grant and verifies it can log in.
#   - backend/.env: created from .env.example on first run (production
#     mode, secrets + bootstrap admin generated). On every run the
#     installer (re)sets only DATABASE_URL, HOST and PORT; everything
#     else in .env is left alone.
#   - Python venv + backend dependencies, database tables, initial
#     content (seed only adds what's missing — never overwrites content
#     edited in the admin panel).
#   - Builds the public site and the admin dashboard; the backend serves
#     both itself, so the whole app runs behind one port (5960).
#   - Runs the backend under pm2 as `perennia4` and saves the pm2 list.
#
# The installer does not install system packages (no apt/yum). It needs
# git, python3 (3.10+) with venv, curl, openssl and a mysql/mariadb
# client + reachable server. Node.js 22 is installed via nvm if missing
# or too old; pm2 via npm if missing.
#
# Usage:
#   ./install.sh                       interactive
#   ./install.sh --yes                 non-interactive (see env vars below)
#
# Options:
#   --yes                  Never prompt. Missing passwords are generated
#                          (app_user only when it is created here).
#   --host=ADDR            Bind address (default 127.0.0.1 — put nginx or
#                          another HTTPS reverse proxy in front).
#   --port=PORT            Default 5960.
#   --db-admin-user=USER   MySQL account used to create the DB/grant
#                          (default: root via sudo/unix socket, else prompt).
#   --admin-user=NAME      Bootstrap admin username for the dashboard
#                          (first install only; default "admin").
#   --http-cookies         Allow admin login over plain HTTP (no TLS).
#                          Testing only — runs the app in development mode.
#   --skip-build           Skip npm install/build (backend-only redeploy).
#
# Secrets are read from environment variables, never from the command
# line (so they don't land in shell history or `ps`):
#   DB_PASSWORD            app_user's password
#   DB_ADMIN_PASSWORD      password for --db-admin-user
#   ADMIN_PASSWORD         bootstrap admin password (first install)
# ============================================================================

APP_NAME="perennia4"          # pm2 process name
DB_NAME="perennia4"
DB_USER="app_user"
DB_HOST="localhost"
DB_PORT="3306"
APP_HOST="127.0.0.1"
APP_PORT="5960"
NODE_VERSION=22

ASSUME_YES=false
DB_ADMIN_USER=""
ADMIN_USERNAME="admin"
HTTP_COOKIES=false
SKIP_BUILD=false

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
ADMIN_DIR="$ROOT_DIR/admin"
ENV_FILE="$BACKEND_DIR/.env"
VENV_PY="$BACKEND_DIR/venv/bin/python"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

log()  { printf '\n\033[1;32m==> %s\033[0m\n' "$1"; }
warn() { printf '\033[1;33m!! %s\033[0m\n' "$1"; }
err()  { printf '\033[1;31mERROR: %s\033[0m\n' "$1" >&2; }
die()  { err "$1"; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1; }

trap 'err "install.sh failed at line $LINENO (exit $?)."' ERR

usage() { sed -n '4,50p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

ask_secret() {   # ask_secret "Prompt: " -> echoes the answer (asked twice)
    local prompt="$1" a b
    while true; do
        read -r -s -p "$prompt" a; echo >&2
        [[ -n "$a" ]] || { warn "Cannot be empty."; continue; }
        read -r -s -p "Repeat: " b; echo >&2
        [[ "$a" == "$b" ]] && { printf '%s' "$a"; return; }
        warn "Didn't match — try again."
    done
}

gen_password() { python3 -c 'import secrets, string; print("".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24)), end="")'; }

sql_escape() { local s="${1//\\/\\\\}"; printf '%s' "${s//\'/\'\'}"; }

# ----------------------------------------------------------------------------
# Arguments
# ----------------------------------------------------------------------------

for arg in "$@"; do
    case "$arg" in
        --yes|-y)            ASSUME_YES=true ;;
        --host=*)            APP_HOST="${arg#*=}" ;;
        --port=*)            APP_PORT="${arg#*=}" ;;
        --db-admin-user=*)   DB_ADMIN_USER="${arg#*=}" ;;
        --admin-user=*)      ADMIN_USERNAME="${arg#*=}" ;;
        --http-cookies)      HTTP_COOKIES=true ;;
        --skip-build)        SKIP_BUILD=true ;;
        -h|--help)           usage; exit 0 ;;
        *)                   die "Unknown option: $arg (see --help)" ;;
    esac
done

[[ "$APP_PORT" =~ ^[0-9]+$ ]] || die "--port must be a number (got '$APP_PORT')."
[[ -f "$BACKEND_DIR/requirements.txt" && -f "$ROOT_DIR/package.json" ]] \
    || die "Run this from the root of the Perennia checkout (backend/ and package.json not found next to install.sh)."

# ----------------------------------------------------------------------------
# 1. Prerequisites (checked, never installed — except Node via nvm, pm2)
# ----------------------------------------------------------------------------

log "Checking prerequisites"

MISSING=()
for cmd in git python3 curl openssl; do require_cmd "$cmd" || MISSING+=("$cmd"); done
(( ${#MISSING[@]} == 0 )) || die "Missing required command(s): ${MISSING[*]}. Install them with your system's package manager, then re-run."

python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || die "Python 3.10+ is required (found $(python3 -V 2>&1))."
python3 -c 'import venv, ensurepip' 2>/dev/null \
    || die "python3 venv/ensurepip is missing (Debian/Ubuntu: the python3-venv package)."

if require_cmd mariadb; then DB_CLIENT="mariadb"
elif require_cmd mysql; then DB_CLIENT="mysql"
else die "Neither the mysql nor the mariadb client is installed."
fi
log "Found: git, $(python3 -V), $($DB_CLIENT --version | head -c 60)"

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
# shellcheck disable=SC1091
[[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"
node_major() { node -v 2>/dev/null | sed 's/^v//' | cut -d. -f1; }
if ! require_cmd node || (( $(node_major) < NODE_VERSION )); then
    log "Installing Node.js $NODE_VERSION via nvm"
    if [[ ! -s "$NVM_DIR/nvm.sh" ]]; then
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
    fi
    # shellcheck disable=SC1091
    source "$NVM_DIR/nvm.sh"
    nvm install "$NODE_VERSION"
    nvm use "$NODE_VERSION"
fi
log "Node.js $(node -v), npm $(npm -v)"

if ! require_cmd pm2; then
    log "Installing pm2"
    npm install -g pm2
fi

DEPLOYED_COMMIT="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
log "Deploying commit: $DEPLOYED_COMMIT"

# ----------------------------------------------------------------------------
# 2. Python virtual environment + backend dependencies
# ----------------------------------------------------------------------------

log "Setting up the backend virtual environment"
[[ -x "$VENV_PY" ]] || python3 -m venv "$BACKEND_DIR/venv"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r "$BACKEND_DIR/requirements.txt"

# ----------------------------------------------------------------------------
# 3. Database: create perennia4, grant app_user
# ----------------------------------------------------------------------------

log "Preparing MySQL/MariaDB: database '$DB_NAME', user '$DB_USER'"

# How to run SQL with admin rights, tried in order:
#   explicit --db-admin-user (+ DB_ADMIN_PASSWORD or a prompt),
#   root over the unix socket as the current user (already root),
#   root over the unix socket via passwordless sudo,
#   otherwise ask for an admin user + password.
ADMIN_MODE=""
admin_sql() {   # SQL on stdin; extra args (e.g. -N) go to the client
    case "$ADMIN_MODE" in
        socket) "$DB_CLIENT" -u root "$@" ;;
        sudo)   sudo -n "$DB_CLIENT" -u root "$@" ;;
        creds)  MYSQL_PWD="$DB_ADMIN_PASSWORD" "$DB_CLIENT" --protocol=tcp -h "$DB_HOST" -P "$DB_PORT" -u "$DB_ADMIN_USER" "$@" ;;
    esac
}
if [[ -z "$DB_ADMIN_USER" ]]; then
    if "$DB_CLIENT" -u root -e 'SELECT 1' >/dev/null 2>&1; then ADMIN_MODE="socket"
    elif sudo -n "$DB_CLIENT" -u root -e 'SELECT 1' >/dev/null 2>&1; then ADMIN_MODE="sudo"
    fi
fi
if [[ -z "$ADMIN_MODE" ]]; then
    if [[ -z "$DB_ADMIN_USER" ]]; then
        $ASSUME_YES && die "No database admin access (root via socket/sudo failed). Pass --db-admin-user=USER and DB_ADMIN_PASSWORD."
        read -r -p "MySQL admin user (can create databases/users) [root]: " DB_ADMIN_USER
        DB_ADMIN_USER="${DB_ADMIN_USER:-root}"
    fi
    if [[ -z "${DB_ADMIN_PASSWORD:-}" ]]; then
        $ASSUME_YES && die "DB_ADMIN_PASSWORD is not set for --db-admin-user=$DB_ADMIN_USER."
        read -r -s -p "Password for MySQL user '$DB_ADMIN_USER': " DB_ADMIN_PASSWORD; echo
    fi
    ADMIN_MODE="creds"
    echo 'SELECT 1;' | admin_sql >/dev/null || die "Could not log in to MySQL as '$DB_ADMIN_USER'."
fi
log "Database admin access: $ADMIN_MODE"

echo "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" | admin_sql

# app_user's password: DB_PASSWORD env, else the one already in
# backend/.env (re-runs), else prompt / generate (new user only).
EXISTING_DB_PASSWORD=""
if [[ -f "$ENV_FILE" ]]; then
    EXISTING_DB_PASSWORD="$(ENV_FILE="$ENV_FILE" DB_USER="$DB_USER" python3 - <<'PY'
import os, re
from urllib.parse import unquote, urlsplit
m = re.search(r"^DATABASE_URL=(.*)$", open(os.environ["ENV_FILE"]).read(), re.MULTILINE)
if m and m.group(1).startswith("mysql"):
    u = urlsplit(m.group(1).strip())
    if u.username and unquote(u.username) == os.environ["DB_USER"] and u.password:
        print(unquote(u.password), end="")
PY
)"
fi
DB_PASSWORD="${DB_PASSWORD:-$EXISTING_DB_PASSWORD}"

USER_HOSTS="$(echo "SELECT Host FROM mysql.user WHERE User='$(sql_escape "$DB_USER")';" | admin_sql -N 2>/dev/null || true)"
if [[ -z "$USER_HOSTS" ]]; then
    if [[ -z "$DB_PASSWORD" ]]; then
        if $ASSUME_YES; then
            DB_PASSWORD="$(gen_password)"
            log "Generated a password for new user '$DB_USER' (stored only in backend/.env)"
        else
            DB_PASSWORD="$(ask_secret "Password for the new MySQL user '$DB_USER': ")"
        fi
    fi
    log "Creating MySQL user '$DB_USER'"
    PW_SQL="$(sql_escape "$DB_PASSWORD")"
    admin_sql <<SQL
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$PW_SQL';
CREATE USER '$DB_USER'@'127.0.0.1' IDENTIFIED BY '$PW_SQL';
SQL
    USER_HOSTS=$'localhost\n127.0.0.1'
else
    log "MySQL user '$DB_USER' already exists — keeping its password, adding the grant only"
    if [[ -z "$DB_PASSWORD" ]]; then
        $ASSUME_YES && die "'$DB_USER' already exists; set DB_PASSWORD to its current password."
        read -r -s -p "Current password for existing MySQL user '$DB_USER': " DB_PASSWORD; echo
    fi
fi

while IFS= read -r host; do
    [[ -n "$host" ]] || continue
    echo "GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'$(sql_escape "$host")';" | admin_sql
done <<< "$USER_HOSTS"
echo "FLUSH PRIVILEGES;" | admin_sql

MYSQL_PWD="$DB_PASSWORD" "$DB_CLIENT" --protocol=tcp -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" -e 'SELECT 1;' >/dev/null 2>&1 \
    || die "'$DB_USER' cannot log in to '$DB_NAME' over TCP with the given password. Check the password (DB_PASSWORD) — this script never resets an existing user's password."
log "Verified: '$DB_USER' can connect to '$DB_NAME'"

# ----------------------------------------------------------------------------
# 4. backend/.env
# ----------------------------------------------------------------------------

log "Configuring backend/.env"
FIRST_INSTALL=false
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
    FIRST_INSTALL=true
fi
chmod 600 "$ENV_FILE"

if $HTTP_COOKIES; then ENVIRONMENT="development"; COOKIE_SECURE="false"; else ENVIRONMENT="production"; COOKIE_SECURE="true"; fi

# Written by Python with values passed through the environment: no
# shell quoting of passwords, and the password is percent-encoded so
# characters like @ # : / can't break the DATABASE_URL.
ENV_FILE="$ENV_FILE" FIRST_INSTALL="$FIRST_INSTALL" \
DB_USER="$DB_USER" DB_PASSWORD="$DB_PASSWORD" DB_HOST="$DB_HOST" DB_PORT="$DB_PORT" DB_NAME="$DB_NAME" \
APP_HOST="$APP_HOST" APP_PORT="$APP_PORT" ENVIRONMENT="$ENVIRONMENT" COOKIE_SECURE="$COOKIE_SECURE" \
python3 - <<'PY'
import os, re
from pathlib import Path
from urllib.parse import quote
e = os.environ
url = "mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4".format(
    quote(e["DB_USER"], safe=""), quote(e["DB_PASSWORD"], safe=""), e["DB_HOST"], e["DB_PORT"], quote(e["DB_NAME"], safe=""))
values = {"DATABASE_URL": url, "HOST": e["APP_HOST"], "PORT": e["APP_PORT"]}
if e["FIRST_INSTALL"] == "true":
    values.update({"ENVIRONMENT": e["ENVIRONMENT"], "COOKIE_SECURE": e["COOKIE_SECURE"], "ALLOWED_ORIGINS": ""})
p = Path(e["ENV_FILE"])
content = p.read_text()
for key, value in values.items():
    line = f"{key}={value}"
    pat = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    content = pat.sub(lambda _m: line, content, count=1) if pat.search(content) else content.rstrip("\n") + "\n" + line + "\n"
p.write_text(content)
PY
unset DB_PASSWORD DB_ADMIN_PASSWORD EXISTING_DB_PASSWORD

env_has() { grep -qE "^$1=.+" "$ENV_FILE"; }
if ! env_has SECRET_KEY || ! env_has ENCRYPTION_KEY || ! env_has BOOTSTRAP_ADMIN_PASSWORD_HASH; then
    log "Generating secrets and the bootstrap admin account"
    GENERATED_ADMIN_PW=false
    if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
        if $ASSUME_YES; then
            ADMIN_PASSWORD="$(gen_password)"; GENERATED_ADMIN_PW=true
        else
            if [[ "$ADMIN_USERNAME" == "admin" ]]; then
                read -r -p "Admin dashboard username [admin]: " u; ADMIN_USERNAME="${u:-admin}"
            fi
            ADMIN_PASSWORD="$(ask_secret "Admin dashboard password (12+ characters recommended): ")"
        fi
    fi
    (cd "$BACKEND_DIR" && "$VENV_PY" scripts/gen_secrets.py --username "$ADMIN_USERNAME" --password "$ADMIN_PASSWORD" --write-env .env >/dev/null)
    if $GENERATED_ADMIN_PW; then
        umask 077
        printf 'Perennia admin dashboard\nusername: %s\npassword: %s\n\nDelete this file once the password is stored safely.\n' \
            "$ADMIN_USERNAME" "$ADMIN_PASSWORD" > "$BACKEND_DIR/ADMIN_CREDENTIALS.txt"
        warn "Admin password generated — saved to backend/ADMIN_CREDENTIALS.txt (mode 600). Delete it once stored."
    fi
    unset ADMIN_PASSWORD
else
    log "Secrets already present in backend/.env — keeping them"
fi

# ----------------------------------------------------------------------------
# 5. Tables, bootstrap admin, initial content
# ----------------------------------------------------------------------------

log "Creating tables and the bootstrap admin (if none yet)"
(cd "$BACKEND_DIR" && "$VENV_PY" scripts/init_db.py)
log "Seeding initial content (adds only what's missing)"
(cd "$BACKEND_DIR" && "$VENV_PY" scripts/seed_content.py)

# ----------------------------------------------------------------------------
# 6. Frontends (public site + admin dashboard)
# ----------------------------------------------------------------------------

if $SKIP_BUILD; then
    warn "--skip-build: using the existing dist/ and admin/dist/"
    [[ -f "$ROOT_DIR/dist/index.html" && -f "$ADMIN_DIR/dist/index.html" ]] || die "No existing build found — re-run without --skip-build."
else
    log "Building the public site"
    (cd "$ROOT_DIR" && npm ci --no-audit --no-fund && npm run build)
    log "Building the admin dashboard"
    (cd "$ADMIN_DIR" && npm ci --no-audit --no-fund && npm run build)
fi

# ----------------------------------------------------------------------------
# 7. pm2
# ----------------------------------------------------------------------------

log "Starting '$APP_NAME' under pm2 on $APP_HOST:$APP_PORT"

# Port must be free (or held by our own pm2 process, which is replaced).
if require_cmd ss && ss -ltn "sport = :$APP_PORT" | grep -q LISTEN; then
    if ! pm2 describe "$APP_NAME" >/dev/null 2>&1; then
        die "Port $APP_PORT is already in use by another process. Free it or pass --port=..."
    fi
fi

# Regenerated every run (gitignored). One uvicorn worker on purpose: the
# booking/calendar background jobs run in-process (app/scheduler.py),
# so extra workers would run every job several times over.
cat > "$ROOT_DIR/ecosystem.config.cjs" <<JS
module.exports = {
  apps: [
    {
      name: "$APP_NAME",
      cwd: "$BACKEND_DIR",
      script: "$BACKEND_DIR/venv/bin/uvicorn",
      args: "app.main:app --host $APP_HOST --port $APP_PORT --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
      kill_timeout: 8000,
    },
  ],
};
JS

# delete + start (not restart) so changed args/port always take effect.
pm2 describe "$APP_NAME" >/dev/null 2>&1 && pm2 delete "$APP_NAME" >/dev/null
pm2 start "$ROOT_DIR/ecosystem.config.cjs"
pm2 save >/dev/null
log "pm2 process list saved ('$APP_NAME')"

# ----------------------------------------------------------------------------
# 8. Health check
# ----------------------------------------------------------------------------

log "Waiting for the app to respond"
HEALTHY=false
for _ in $(seq 1 20); do
    if curl -fsS "http://127.0.0.1:$APP_PORT/api/health" >/dev/null 2>&1; then HEALTHY=true; break; fi
    sleep 1
done
$HEALTHY || die "No response from http://127.0.0.1:$APP_PORT/api/health within 20s (commit $DEPLOYED_COMMIT). Check: pm2 logs $APP_NAME"
curl -fsS "http://127.0.0.1:$APP_PORT/" | grep -q 'id="root"' || warn "API is up but the public site didn't load — check that dist/ was built."
curl -fsS "http://127.0.0.1:$APP_PORT/admin" | grep -q 'id="root"' || warn "API is up but the admin dashboard didn't load — check that admin/dist/ was built."

cat <<DONE

$(printf '\033[1;32m')Perennia v4 is running.$(printf '\033[0m')

  Commit           $DEPLOYED_COMMIT
  pm2 process      $APP_NAME
  Listening on     http://$APP_HOST:$APP_PORT
  Public site      http://$APP_HOST:$APP_PORT/
  Admin dashboard  http://$APP_HOST:$APP_PORT/admin
  Database         $DB_NAME  (user $DB_USER @ $DB_HOST:$DB_PORT)

  pm2 status
  pm2 logs $APP_NAME
  pm2 restart $APP_NAME

To survive a reboot, run once (as the user that owns pm2):  pm2 startup
DONE
if [[ "$APP_HOST" == "127.0.0.1" ]]; then
    echo "The app listens on 127.0.0.1 only — point your HTTPS reverse proxy (e.g. nginx) at http://127.0.0.1:$APP_PORT."
fi
if $HTTP_COOKIES; then
    warn "--http-cookies: running in development mode with insecure cookies. Re-install without it once HTTPS is in place (edit ENVIRONMENT/COOKIE_SECURE in backend/.env)."
fi

#!/bin/sh
set -eu

log() {
  printf '%s [rising-voices-cron] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

SCRIPT_INPUT=$0
case "$SCRIPT_INPUT" in
  /*) SCRIPT_PATH="$SCRIPT_INPUT" ;;
  *) SCRIPT_PATH="$(pwd)/$SCRIPT_INPUT" ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$SCRIPT_PATH")" && pwd)
APP_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

log "Starting Rising AI Voices refresh wrapper"
log "initial_pwd=$(pwd)"
log "script_path=$SCRIPT_PATH"
log "script_dir=$SCRIPT_DIR"
log "app_root=$APP_ROOT"

log "Listing app root contents"
ls -la "$APP_ROOT" || true
log "Listing scripts directory contents"
ls -la "$APP_ROOT/scripts" || true

cd "$APP_ROOT"
log "changed_pwd=$(pwd)"

if [ -f "$APP_ROOT/.env" ]; then
  log "Loading environment from $APP_ROOT/.env"
  set -a
  # shellcheck disable=SC1090
  . "$APP_ROOT/.env"
  set +a
fi

for var_name in DATABASE_URL DATABASE_SYNC_URL OPENAI_API_KEY YOUTUBE_API_KEY DEBUG; do
  eval "var_value=\${$var_name-}"
  if [ -n "$var_value" ]; then
    log "env:$var_name is set"
  else
    log "env:$var_name is MISSING"
  fi
done

if [ -x "$APP_ROOT/venv/bin/python" ]; then
  PYTHON_CMD="$APP_ROOT/venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="$(command -v python)"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="$(command -v python3)"
else
  PYTHON_CMD=""
fi

log "python_cmd=${PYTHON_CMD:-<missing>}"

if [ -z "${PYTHON_CMD:-}" ]; then
  log "ERROR: no python executable found"
  exit 1
fi

log "python_version=$("$PYTHON_CMD" --version 2>&1 || true)"

log "Running alembic upgrade head"
if "$PYTHON_CMD" -c "from alembic.config import main; main(argv=['upgrade', 'head'])"; then
  log "Alembic upgrade completed successfully"
else
  status=$?
  log "ERROR: alembic upgrade failed with status=$status"
  exit "$status"
fi

log "Running rising voices refresh job"
if "$PYTHON_CMD" scripts/refresh_rising_voices_job.py; then
  log "Rising voices refresh job completed successfully"
else
  status=$?
  log "ERROR: refresh job failed with status=$status"
  exit "$status"
fi

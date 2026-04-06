#!/bin/sh
set -eu

if [ -x "./venv/bin/python" ]; then
  ./venv/bin/python -m alembic upgrade head
  ./venv/bin/python scripts/refresh_rising_voices_job.py
  exit 0
fi

alembic upgrade head
python scripts/refresh_rising_voices_job.py

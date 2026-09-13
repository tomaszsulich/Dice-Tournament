#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python src/manage.py migrate --noinput
fi

exec "$@"

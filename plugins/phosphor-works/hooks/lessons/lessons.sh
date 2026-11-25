#!/bin/sh
# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Runs lessons.py with the Python of the lesson index's virtualenv, which
# workspace/tools/setup creates. `check` needs no dependencies and runs on the
# system Python. Without the virtualenv the hook passes the prompt through.
here=$(dirname "$0")
data="${PHOSPHOR_LESSONS_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/phosphor-works/lessons}"
py="$data/venv/bin/python"

if [ "$1" = check ]; then
    exec python3 -I "$here/lessons.py" "$@"
fi
if [ ! -x "$py" ]; then
    if [ "$1" = hook ]; then
        cat >/dev/null
        exit 0
    fi
    echo "The lesson index is not installed: run tools/setup in the workspace checkout." >&2
    exit 1
fi
exec "$py" -I "$here/lessons.py" "$@"

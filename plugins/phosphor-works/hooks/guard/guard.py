#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 fuddlesworth
# SPDX-License-Identifier: GPL-3.0-or-later
"""PreToolUse guard of the phosphor-works plugin: the hard rules of each repository's CLAUDE.md.

Run as `python3 -I "${CLAUDE_PLUGIN_ROOT}/hooks/guard/guard.py"`. Claude Code passes the tool call as JSON on
stdin. Exit code 2 blocks the call and shows stderr to Claude. Any failure of the guard itself (malformed input,
an exception in a check) blocks the call too: a hook that exits with another status lets the call run.

The repository is the base name of the main checkout of `git rev-parse --show-toplevel` in $CLAUDE_PROJECT_DIR
(a linked worktree counts as its main checkout), else of $CLAUDE_PROJECT_DIR, else of the working directory. Its
rules are repos/<name>.py, case-insensitively, and repos/default.py for any other repository. core.py has the rules
that all of them share, and the reading of a command line.

Tests: python3 -I test_guard.py
"""

import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # python3 -I does not put the script's directory on sys.path

MSG_FAILED = ('The guard could not check this call ({}), so it blocks it. Write the command in a simpler form, or '
              'ask the user.')
try:
    import core  # noqa: E402
except Exception as error:  # a broken install blocks every call, in main()
    core, IMPORT_ERROR = None, error


def repository_name(project=None):
    """The name of the repository of PROJECT (default: $CLAUDE_PROJECT_DIR, else the working directory)."""
    project = project or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    top = core.toplevel(project)
    return os.path.basename(core.main_checkout(os.path.realpath(top or project)).rstrip('/'))


def repository_module(name):
    """The rules module of the repository NAME: repos/<name>.py in lower case, else repos/default.py."""
    key = name.lower()
    if not re.fullmatch(r'[a-z][a-z0-9_]*', key) or not os.path.isfile(os.path.join(HERE, 'repos', key + '.py')):
        key = 'default'
    return importlib.import_module('repos.' + key)


def guard_for(project=None):
    project = project or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
    return core.Guard(repository_module(repository_name(project)), project)


def main():
    try:
        if core is None:
            raise IMPORT_ERROR
        message = guard_for().call(json.load(sys.stdin))
    except Exception as error:
        print(MSG_FAILED.format(f'{type(error).__name__}: {error}'[:200]), file=sys.stderr)
        sys.exit(2)
    if message:
        print(message, file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()

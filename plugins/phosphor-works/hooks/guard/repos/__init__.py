# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules of each repository: repos/<name>.py, with the repository's base name in lower case.

A module has a CONFIG (see core.DEFAULTS for its fields) and may have check(cmd, guard, scope), which runs for every
simple command after the shared rules and returns a message to block it, or None. default.py covers every
repository that has no module of its own.
"""

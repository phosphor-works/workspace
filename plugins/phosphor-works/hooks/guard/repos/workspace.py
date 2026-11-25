# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""The workspace repository. A session started here may touch every app, so it gets the app rules of PlasmaZones
and Afterglow together (D-Bus and the desktop; the terminal, its mux daemon and its windows), and no sibling-repo
protection: the other repositories are its working area."""

from repos import afterglow, plasmazones

CONFIG = {
    'messages': {
        'pkill': (
            'pkill and killall match by name, and the user runs PlasmaZones and Afterglow on this desktop: `pkill '
            "plasmazonesd`, `pkill kwin` or `pkill afterglow` takes down the user's real session or closes their "
            'terminal windows, possibly this session too, and the pattern can match the shell that runs it. Use '
            '`pgrep -a NAME`, then `kill PID` on a build-tree or nested-session process only.'
        ),
        'pgrep_kill': (
            "kill with the PIDs that pgrep or pidof found can match the user's own plasmazonesd, KWin, Afterglow or "
            'mux daemon, and pgrep -f also matches the shell that runs the command, because its command line holds '
            'the pattern. List the processes with `pgrep -a NAME`. Then run `kill PID` with the numbers in a '
            'separate command.'
        ),
        'install': (
            'Never install or uninstall the build (cmake --install, the install or uninstall target, '
            'cmake_install.cmake, make post-install, moon run repo:install/repo:post-install). The user installs the '
            'apps. Only an install into a temporary directory (--prefix /tmp/... or DESTDIR=/tmp/... on the command '
            'itself) is allowed.'
        ),
    },
    'command_tools': afterglow.CONFIG['command_tools'],
}


def check(cmd, guard, scope):
    return plasmazones.check(cmd, guard, scope) or afterglow.check(cmd, guard, scope)

# SPDX-FileCopyrightText: 2026 fuddlesworth
# SPDX-License-Identifier: GPL-3.0-or-later
"""PlasmaZones (CLAUDE.md, pz-build, pz-verify-live).

The user runs PlasmaZones on the desktop this session runs on. The host-session rules keep a command from reaching
the user's own daemon, compositor or shell: the nested-KWin harness (scripts/nested-kwin, pz-verify-live) is where
Claude drives a PlasmaZones session.
"""

import os
import re

DBUS_TOOLS = {'qdbus', 'qdbus6', 'qdbus-qt6', 'qdbus-qt5', 'busctl', 'dbus-send', 'gdbus'}
# The root of every PlasmaZones bus name: the daemon's placement API, the settings app and the editor.
PROTECTED_BUS_PREFIXES = ('org.phosphor_works',)
# systemctl verbs that stop, restart or disable a unit
SYSTEMCTL_DISRUPT = {
    'stop', 'restart', 'try-restart', 'reload', 'reload-or-restart', 'try-reload-or-restart', 'kill', 'disable',
    'mask', 'isolate',
}
DESKTOP_UNIT = re.compile(r'plasma|kwin|plasmazones', re.I)

MSG_HOST_DBUS = (
    "This D-Bus call reaches PlasmaZones (org.phosphor_works.*) on the user's own session bus, which drives the "
    'daemon of their real desktop. Run it in the nested session: source its env first (`. '
    '"$XDG_RUNTIME_DIR/pz-nested/env.sh"; qdbus6 ...`, see pz-verify-live), or give the bus address explicitly. If '
    'the user asked about their live desktop, ask them to run the command with `! <command>`.'
)
MSG_DESKTOP = (
    "This command restarts or stops a process of the user's real desktop (KWin, plasmashell, plasmazonesd or their "
    'systemd units). Never do that from a session. Use the nested-KWin harness (scripts/nested-kwin, '
    'pz-verify-live), or ask the user to run it with `! <command>`.'
)

CONFIG = {
    'messages': {
        'pkill': (
            "pkill and killall match by name, and the user runs PlasmaZones on this desktop: `pkill plasmazonesd` "
            "or `pkill kwin` takes down the user's real session, and the pattern can match the shell that runs it. "
            'Use `pgrep -a NAME`, then `kill PID` on a build-tree or nested-session process only. '
            'scripts/nested-kwin/daemon.sh restarts the nested daemon by its pid file.'
        ),
        'pgrep_kill': (
            "kill with the PIDs that pgrep or pidof found can match the user's own plasmazonesd or KWin, and "
            'pgrep -f also matches the shell that runs the command, because its command line holds the pattern. '
            'List the processes with `pgrep -a NAME`. Then run `kill PID` with the numbers in a separate command.'
        ),
        'install': (
            'Never install the build (cmake --install, the install or uninstall target, make install/post-install, '
            'moon run repo:install/repo:post-install). The user installs PlasmaZones. Only a staged install into a '
            'temporary directory (--prefix /tmp/... or DESTDIR=/tmp/... on the command itself) is allowed.'
        ),
    },
    'local_paths': [
        (r'(^|/)(Testing|scratchpad|\.moon/cache)(/|$)', 'Testing/, scratchpad/, .moon/cache/'),
    ],
    # Trees that CMake, CPM, ctest or moon write. A worktree under .claude/worktrees/ has build trees of its own.
    'build_tree': r'^(\.claude/worktrees/[^/]+/)?(build[^/]*|\.cache|Testing|\.moon/cache)/',
}


def installs(cmd, guard):
    """moon run PROJECT:install outside a temporary directory, and post-install (moon or make), which refreshes
    the user's KDE service cache against what is installed: both belong to the install step."""
    if cmd.word == 'make' and 'post-install' in cmd.args:
        return True
    if cmd.word == 'moon':
        tasks = [a for a in cmd.args if not a.startswith('-')]
        if any(t.endswith(':post-install') for t in tasks):
            return True
        return any(t.endswith(':install') for t in tasks) and not guard.temporary_destination(cmd)
    return False


def nested_bus(word, args):
    """Whether this simple command points the commands after it at a bus other than the user's: it sources the
    nested session's env.sh, or exports DBUS_SESSION_BUS_ADDRESS."""
    if word in ('.', 'source') and args and os.path.basename(args[0]) == 'env.sh':
        return True
    return word == 'export' and any(a.startswith('DBUS_SESSION_BUS_ADDRESS=') for a in args)


def own_bus(cmd):
    """Whether one command names its own bus: a VAR= or env assignment (its own or its shell's), dbus-run-session,
    or an address option of a D-Bus tool."""
    if 'dbus-run-session' in cmd.wrappers or cmd.sets('DBUS_SESSION_BUS_ADDRESS'):
        return True
    word, args = cmd.word, cmd.args
    if word == 'busctl' and ('--system' in args or any(a.startswith('--address') for a in args)):
        return True
    if word == 'dbus-send' and any(a == '--system' or a.startswith('--address=') for a in args):
        return True
    if word == 'gdbus' and any(a in ('--system', '-y', '--address', '-a') or a.startswith('--address=')
                               for a in args):
        return True
    return False


def disrupts_desktop(word, args):
    if word in ('kwin_wayland', 'kwin_x11', 'plasmashell') and '--replace' in args:
        return True
    if word in ('kquitapp6', 'kquitapp5'):
        return True
    if word == 'systemctl' and '--user' in args:
        verbs = [a for a in args if not a.startswith('-')]
        if verbs and verbs[0] in SYSTEMCTL_DISRUPT and any(DESKTOP_UNIT.search(u) for u in verbs[1:]):
            return True
    return False


def check(cmd, guard, scope):
    word, args = cmd.word, cmd.args
    scope.state['nested'] = scope.state.get('nested') or nested_bus(word, args)
    if installs(cmd, guard):
        return guard.message('install')
    elsewhere = scope.state['nested'] or own_bus(cmd)
    if word in DBUS_TOOLS and any(p in a for a in args for p in PROTECTED_BUS_PREFIXES) and not elsewhere:
        return MSG_HOST_DBUS
    if disrupts_desktop(word, args) and not elsewhere:
        return MSG_DESKTOP
    return None

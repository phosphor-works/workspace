# SPDX-FileCopyrightText: 2026 fuddlesworth
# SPDX-License-Identifier: GPL-3.0-or-later
"""Afterglow (CLAUDE.md).

The user runs Afterglow as their terminal, and this session usually runs inside one of its panes. The terminal
rules keep a command from reaching the user's running Afterglow, their mux daemon and its sessions, and their
display.
"""

import fnmatch
import os
import pwd
import re

import core

# The run tool of `afterglow mcp`: a shell command in a pane of the agent session. send, which types into a
# program, is not checked: CLAUDE.md says to run shell commands with run.
MCP_RUN = 'mcp__afterglow__run'

CONFIG = {
    'messages': {
        'pkill': (
            'pkill and killall match by name, and the user runs Afterglow as their terminal: `pkill afterglow` '
            "closes the user's own windows, and possibly this session. Use `pgrep -a NAME`, then `kill PID` on a "
            'build/ process only.'
        ),
        'pgrep_kill': (
            "kill with the PIDs that pgrep or pidof found can match the user's own Afterglow or mux daemon, and "
            'pgrep -f also matches the shell that runs the command, because its command line holds the pattern. '
            'List the processes with `pgrep -a NAME`. Then run `kill PID` with the numbers in a separate command.'
        ),
        'install': (
            'Never install or uninstall the build (cmake --install, the install or uninstall target, '
            'cmake_install.cmake). The user installs Afterglow. Only an install into a temporary directory '
            '(--prefix /tmp/... or DESTDIR=/tmp/... on the command itself) is allowed.'
        ),
        'sibling': (
            '{path} is in {name}, which changes only through its own branch and pull request. Afterglow builds the '
            'Phosphor libraries from phosphor-libs. Tell the user what Phosphor needs and why.'
        ),
    },
    # Generated files: run the generator instead
    'generated': {
        'docs/CONFIGURATION.md': 'python3 tools/generate-reference.py build/afterglow/afterglow',
        'libs/afterglow-vt/src/UnicodeTables.inc': 'python3 -I tools/gen_unicode_tables.py <ucd-dir> '
        'libs/afterglow-vt/src/UnicodeTables.inc',
    },
    # The Phosphor libraries come from phosphor-libs, and a build can use the phosphor-libs checkout next to the
    # main checkout of this repository. That repository and PlasmaZones change only through their own branches
    # and pull requests.
    'protected_siblings': ('phosphor-libs', 'PlasmaZones'),
    'command_tools': (MCP_RUN,),
}

MSG_CTL = (
    "`afterglow ctl`, `aglow run` and `afterglow run` drive the user's running Afterglow: this session runs inside "
    "one of its panes, and they use the pane's $AFTERGLOW_SOCKET, else the socket of the user's Wayland display. "
    'Give them the socket of a test session, with the pane ID cleared '
    '(AFTERGLOW_SOCKET=/path/to/test.sock AFTERGLOW_PANE_ID=), or remove the pane variables and point them at '
    'another display (env -u AFTERGLOW_SOCKET -u AFTERGLOW_PANE_ID WAYLAND_DISPLAY=...). Ask the user before you '
    'drive their instance.'
)
MSG_MUX = (
    "`afterglow mux`, `afterglow ctl --session`, `afterglow mcp`, `aglow-mux` (`afterglow-mux` in an older build) "
    "and `afterglow --mux-attach` reach the user's mux daemon, which holds the user's terminal sessions. Its sockets "
    'are in $XDG_RUNTIME_DIR/aglow-mux and $XDG_STATE_HOME/aglow-mux (else ~/.local/state/aglow-mux), so '
    'WAYLAND_DISPLAY does not isolate it. Name a private runtime directory and a private state directory under /tmp '
    'on the command (XDG_RUNTIME_DIR=/tmp/... XDG_STATE_HOME=/tmp/...), and kill the sessions that you made with the '
    'same variables. Never stop, kill, restart or mask aglow-mux.service, and never remove the files in the two '
    "socket directories of the user: that ends or strands the user's sessions. `afterglow mcp` also needs a private "
    'XDG_CONFIG_HOME and HOME under /tmp: save_project writes to the projects folder of the configuration. '
    '`afterglow mux` alone, and the --help of `afterglow mux` and `afterglow mcp`, connect to nothing.'
)
MSG_MCP_BUILD = (
    "An MCP server from build/ starts an aglow-mux from build/, which the next build breaks, and it reaches the "
    "user's mux daemon. Register the afterglow that the user installed, or test the build of `afterglow mcp` with "
    'private XDG directories (afterglow/tests/mcp_session.py).'
)
MSG_LAUNCH = (
    "This starts Afterglow on the user's own Wayland display: it opens a window on the user's desktop, or hands the "
    "window to the user's running Afterglow through the socket of that display. Test in a nested KWin with its own "
    'display (the ag-verify-live skill), or name another display on the command: WAYLAND_DISPLAY=NAME or '
    'XDG_RUNTIME_DIR=/tmp/... before the program. --help, --version and --config-reference open no window.'
)


def display_socket_name(display, runtime):
    """The file name of a display's main socket in RUNTIME, as AfterglowProto::sharedSocketPath names it."""
    name = display or ''
    if runtime and name.startswith(runtime.rstrip('/') + '/'):
        name = name[len(runtime.rstrip('/')) + 1 :]
    name = name.lstrip('/')
    return 'afterglow-%s.sock' % (re.sub(r'[^A-Za-z0-9._-]', '_', name) or 'wayland-0')


def isolated_client(env):
    """Whether afterglow ctl, aglow run or afterglow run reaches a socket other than the user's. Each picks
    AFTERGLOW_SOCKET, else the main socket of WAYLAND_DISPLAY in XDG_RUNTIME_DIR. Only literal values count."""
    if any(env.get(n, '') is None for n in ('AFTERGLOW_SOCKET', 'AFTERGLOW_PANE_ID', 'XDG_RUNTIME_DIR',
                                            'WAYLAND_DISPLAY')):
        return False
    socket = env.get('AFTERGLOW_SOCKET')
    if socket:
        if not socket.startswith('/'):
            return False
        target = os.path.realpath(socket)
    elif env.get('AFTERGLOW_PANE_ID'):
        return True  # the client refuses a pane ID without its socket
    elif not env.get('XDG_RUNTIME_DIR'):
        return True  # no socket to find
    else:
        runtime = env['XDG_RUNTIME_DIR']
        target = os.path.realpath(os.path.join(runtime, display_socket_name(env.get('WAYLAND_DISPLAY'), runtime)))
    if os.environ.get('AFTERGLOW_SOCKET') and target == os.path.realpath(os.environ['AFTERGLOW_SOCKET']):
        return False
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if runtime and os.path.dirname(target) == os.path.realpath(runtime):
        # The main socket of the user's display, or the socket of a separate process on it
        own = display_socket_name(os.environ.get('WAYLAND_DISPLAY'), runtime)[: -len('.sock')]
        return not re.fullmatch(re.escape(own) + r'(-\d+)?\.sock', os.path.basename(target))
    return True


def isolated_launch(env):
    """Whether a launch of afterglow opens on a display other than the user's: another WAYLAND_DISPLAY or another
    XDG_RUNTIME_DIR, given literally."""
    runtime, display = env.get('XDG_RUNTIME_DIR', ''), env.get('WAYLAND_DISPLAY', '')
    if runtime is None or display is None:
        return False
    return (os.path.realpath(runtime or '/-') != os.path.realpath(os.environ.get('XDG_RUNTIME_DIR', '') or '/-')
            or (display or 'wayland-0') != (os.environ.get('WAYLAND_DISPLAY') or 'wayland-0'))


# The names of the daemon: aglow-mux, and afterglow-mux of an older build, which the user may still run. Both name
# its executable, its systemd unit and its socket directories.
MUX_DAEMONS = ('aglow-mux', 'afterglow-mux')


def user_bases():
    """The directories that hold the socket directories of the user's own mux daemon."""
    bases = {'/run/user/%d' % os.getuid()}
    if os.environ.get('XDG_RUNTIME_DIR', '').startswith('/'):
        bases.add(os.environ['XDG_RUNTIME_DIR'])
    if os.environ.get('XDG_STATE_HOME', '').startswith('/'):
        bases.add(os.environ['XDG_STATE_HOME'])
    try:
        bases.add(os.path.join(pwd.getpwuid(os.getuid()).pw_dir, '.local', 'state'))
    except KeyError:
        pass
    return {os.path.realpath(b) for b in bases}


def mux_directories():
    return {os.path.join(base, name) for base in user_bases() for name in MUX_DAEMONS}


def isolated_mux(env):
    """Whether a mux command reaches a daemon other than the user's: a literal XDG_RUNTIME_DIR and a state
    directory (XDG_STATE_HOME, else HOME/.local/state) that are not the user's."""
    runtime = env.get('XDG_RUNTIME_DIR')
    if not runtime or not runtime.startswith('/'):
        return False
    users = user_bases()
    if os.path.realpath(runtime) in users:
        return False
    state = env.get('XDG_STATE_HOME')
    if not state:
        home = env.get('HOME')
        if not home:
            return home is not None  # no HOME: no state socket
        state = os.path.join(home, '.local', 'state')
    return state.startswith('/') and os.path.realpath(state) not in users


def isolated_config(env):
    """Whether afterglow mcp writes its projects elsewhere than the user's: a literal XDG_CONFIG_HOME and HOME
    under /tmp."""
    return all(core.under_tmp(env.get(name)) for name in ('XDG_CONFIG_HOME', 'HOME'))


def registers_build_server(word, args):
    """Whether claude mcp add registers an afterglow from a build tree (build/ or a preset's build-NAME/) as an MCP
    server."""
    if word != 'claude' or args[:2] != ['mcp', 'add']:
        return False
    return any(os.path.basename(a) == 'afterglow' and re.search(r'(^|/)build(-[^/]+)?/', a) for a in args[2:])


def reaches_mux(word, args):
    """Whether afterglow ARGS or a daemon of MUX_DAEMONS reaches a mux daemon: afterglow mux and afterglow mcp (but
    not their help), afterglow ctl --session, afterglow --mux-attach, and the daemon itself (but not its --help or
    --version)."""
    if word == 'afterglow':
        if args[:2] == ['ctl', '--session']:
            return True
        if args[:1] == ['mcp'] and args[1:2] not in (['-h'], ['--help']):
            return True
        if any(a == '--mux-attach' or a.startswith('--mux-attach=') for a in args):
            return True
        if args[:1] != ['mux'] or len(args) == 1 or args[1] in ('-h', '--help', 'help'):
            return False
        return args[1:] not in (['server', '--help'], ['server', '-h'])
    return word in MUX_DAEMONS and args[:1] not in (['--help'], ['-h'], ['--version'])


def drives_instance(word, args):
    """Whether afterglow ctl, afterglow run or aglow run connects to a running Afterglow. Their help does not."""
    if word == 'afterglow' and args[:1] == ['ctl']:
        return args[1:2] not in ([], ['-h'], ['--help'], ['--session'])
    if word in ('afterglow', 'aglow') and args[:1] == ['run']:
        return not any(a in ('-h', '--help') for a in args[1:2])
    return False


# afterglow's options that take a value, and the ones that end the process before a window (main.cpp)
LAUNCH_VALUES = {'-d', '--working-directory', '--title', '--config', '-o', '--override', '--class', '--mux-attach'}
NO_WINDOW = {'-h', '--help', '-?', '--help-all', '-v', '--version', '--config-reference'}
# The words after afterglow that run something else than the terminal
NO_TERMINAL = {'ctl', 'ssh', 'mux', 'mcp', 'run', 'transfer', 'dnd', 'icat', 'clipboard'}


def launches_window(args):
    if args[:1] and args[0] in NO_TERMINAL:
        return False
    k = 0
    while k < len(args):
        a = args[k]
        if a == '--' or not a.startswith('-'):
            break
        if a.split('=', 1)[0] in NO_WINDOW:
            return False
        k += 1 + (a in LAUNCH_VALUES)
    return True


SYSTEMCTL_ENDS = {'stop', 'kill', 'restart', 'try-restart', 'reload-or-restart', 'try-reload-or-restart',
                  'condrestart', 'force-reload', 'disable', 'mask', 'clean', 'freeze', 'reset-failed'}
MUX_UNITS = tuple(f'{name}.service' for name in MUX_DAEMONS) + ('app.slice',)


def stops_mux_unit(args):
    """Whether systemctl ARGS stops, restarts or masks the unit of the user's mux daemon, or app.slice, which
    holds it."""
    words = [a for a in args if not a.startswith('-')]
    if not SYSTEMCTL_ENDS & set(words):
        return False
    for unit in words:
        if '.' not in unit and not any(c in unit for c in '*?['):
            unit += '.service'
        if any(fnmatch.fnmatchcase(name, unit) for name in MUX_UNITS):
            return True
    return False


REMOVES = {'rm', 'unlink', 'rmdir', 'mv', 'shred', 'trash', 'trash-put'}


def removes_mux_files(word, args, cwd):
    """Whether a removal or a move names one of the user's mux socket directories, a file in one, or a directory
    above one."""
    if word not in REMOVES:
        return False
    protected = mux_directories()
    for a in args:
        if a.startswith('-'):
            continue
        if '$' in a or '`' in a:
            if any(name in a for name in MUX_DAEMONS):
                return True
            continue
        path = os.path.realpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(a)))
        if any(path == d or path.startswith(d + '/') or d.startswith(path.rstrip('/') + '/') for d in protected):
            return True
    return False


def check(cmd, guard, scope):
    """The terminal rules. A command of MCP_RUN runs in a pane of the agent session of `afterglow mcp`, whose
    AFTERGLOW_SOCKET and AFTERGLOW_PANE_ID are those of that session: afterglow ctl and aglow run act on it, not on
    the user's windows."""
    word, args = cmd.word, cmd.args
    env = core.environment(cmd.env)
    if reaches_mux(word, args) and not isolated_mux(env):
        return MSG_MUX
    if word == 'afterglow' and reaches_mux(word, args) and args[:1] == ['mcp'] and not isolated_config(env):
        return MSG_MUX
    if registers_build_server(word, args):
        return MSG_MCP_BUILD
    if word == 'systemctl' and stops_mux_unit(args):
        return MSG_MUX
    if removes_mux_files(word, args, guard.cwd):
        return MSG_MUX
    if drives_instance(word, args) and guard.tool != MCP_RUN and not isolated_client(env):
        return MSG_CTL
    if word == 'afterglow' and launches_window(args) and not reaches_mux(word, args) and not isolated_launch(env):
        return MSG_LAUNCH
    return None

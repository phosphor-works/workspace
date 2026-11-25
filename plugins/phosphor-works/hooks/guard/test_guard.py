#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cases for the guard. Run: python3 -I test_guard.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core  # noqa: E402
import guard  # noqa: E402
from repos import afterglow, default, plasmazones, workspace  # noqa: E402

UID = os.getuid()
RUN = f'/run/user/{UID}'


def git(*args, cwd=None):
    subprocess.run(['git', *args], check=True, cwd=cwd, capture_output=True)


def git_repo(path, branch='feat'):
    """A repository at PATH with one commit, on BRANCH."""
    os.makedirs(path, exist_ok=True)
    git('init', '-q', '-b', 'main', path)
    git('-C', path, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'x')
    if branch != 'main':
        git('-C', path, 'checkout', '-q', '-b', branch)
    return path


class Case(unittest.TestCase):
    """Rules of one repository, checked from a temporary repository on a feature branch."""

    repo = default

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = git_repo(os.path.join(cls.tmp.name, 'project'))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def guard(self, tool='Bash'):
        return core.Guard(self.repo, self.root, tool)

    def msg(self, key):
        return self.guard().message(key)

    def blocked(self, command, message=None, cwd=None, tool='Bash'):
        got = self.guard(tool).bash(command, cwd or self.root)
        self.assertIsNotNone(got, f'not blocked: {command!r}')
        if message is not None:
            self.assertEqual(got, message, command)

    def allowed(self, command, cwd=None, tool='Bash'):
        self.assertIsNone(self.guard(tool).bash(command, cwd or self.root), command)


class SharedRules(Case):
    """The core rules, against the default repository."""

    def test_sudo(self):
        self.blocked('sudo pacman -S glslang', self.msg('sudo'))
        self.blocked('cd build && sudo make install', self.msg('sudo'))
        for c in ('su -c ls', 'sudoedit /etc/x', 'pkexec ls', 'run0 ls', 'doas ls', 'nice -n 5 sudo ls',
                  'systemd-run --user --scope -p MemoryMax=6G sudo ls'):
            self.blocked(c, self.msg('sudo'))
        self.allowed("grep -n 'a|sudo' file")

    def test_install(self):
        for c in ('cmake --install build', 'cmake --build build --target install', 'cmake --build build -t uninstall',
                  'cmake --build build --target install/strip', 'make install', 'make uninstall', 'gmake install',
                  'ninja -C build install/local', 'cmake -P build/cmake_install.cmake',
                  'DESTDIR=~/stage cmake --install build', 'cmake --install build --prefix stage'):
            self.blocked(c, self.msg('install'))
        for c in ('cmake --install build --prefix /tmp/pz', 'DESTDIR=/tmp/stage cmake --install build',
                  'DESTDIR=/var/tmp/stage cmake --install build', 'make DESTDIR=/tmp/stage install',
                  'cmake -DCMAKE_INSTALL_PREFIX=/tmp/p -P build/cmake_install.cmake',
                  'cmake --build build --parallel 6', 'make test', 'ninja -C build'):
            self.allowed(c)

    def test_uninstall_always_blocked(self):  # decision 2
        for c in ('make uninstall', 'DESTDIR=/tmp/s make uninstall', 'ninja uninstall',
                  'cmake --build build --target uninstall', 'DESTDIR=/tmp/s cmake --build build --target=uninstall'):
            self.blocked(c, self.msg('install'))

    def test_destdir_from_own_words(self):  # decision 3
        self.allowed('DESTDIR=/tmp/s cmake --install build')
        self.allowed('env DESTDIR=/tmp/s cmake --install build')
        self.blocked('echo DESTDIR=/tmp/s; cmake --install build', self.msg('install'))
        self.blocked('export DESTDIR=/tmp/s; cmake --install build', self.msg('install'))
        self.blocked('DESTDIR=/tmp/s true; cmake --install build', self.msg('install'))
        self.blocked('DESTDIR=$STAGE cmake --install build', self.msg('install'))

    def test_kill(self):
        self.blocked('pkill -f plasmazonesd', self.msg('pkill'))
        self.blocked('then killall kwin_wayland', self.msg('pkill'))
        for c in ('killall5 -9', 'skill afterglow', 'timeout 5 pkill x', 'valgrind pkill x'):
            self.blocked(c, self.msg('pkill'))
        self.allowed('pgrep -a plasmazonesd')
        self.allowed('kill 12345')

    def test_pgrep_kill(self):  # decision 1
        for c in ('kill $(pgrep -f plasmazonesd)', 'pgrep -f kwin | xargs kill', 'kill $(pgrep afterglow)',
                  'kill `pidof afterglow`', 'pidof x | xargs kill -9', 'for p in $(pgrep x); do kill $p; done',
                  'kill -9 $(echo $(pgrep x))'):
            self.blocked(c, self.msg('pgrep_kill'))
        self.allowed('pgrep -a afterglow; kill 4242')
        self.allowed('pgrep -f x; kill 4242')
        self.allowed('kill %1')

    def test_reading(self):
        self.blocked('echo $(echo $(sudo ls))', self.msg('sudo'))  # nested substitutions
        self.blocked('echo "`sudo ls`"', self.msg('sudo'))
        self.allowed("echo '$(sudo ls)'")
        self.allowed('echo hi # sudo ls')
        self.allowed("echo hi # it's a comment\necho done")
        self.blocked("echo hi # it's a comment\nsudo ls", self.msg('sudo'))
        self.blocked('bash -c "sudo ls"', self.msg('sudo'))
        self.blocked('bash -lc "sudo ls"', self.msg('sudo'))
        self.blocked('dash -c "pkill x"', self.msg('pkill'))
        self.blocked('eval "sudo ls"', self.msg('sudo'))
        self.blocked('gdb --args sudo ls', self.msg('sudo'))
        self.blocked('rr record -n pkill x', self.msg('pkill'))
        self.blocked('lldb -- pkill x', self.msg('pkill'))
        self.allowed("git commit -F - <<'EOF'\nsudo pkill everything\nEOF")
        self.allowed('echo "unbalanced')

    def test_git_add(self):
        self.blocked('git add -A', self.msg('broad'))
        self.blocked('git add .', self.msg('broad'))
        self.blocked('git commit -am "x"', self.msg('broad'))
        self.blocked('git add -f build/foo', self.msg('local'))
        self.blocked('git add .claude/audit-state.json', self.msg('local'))
        self.blocked('git add build-asan/x.o', self.msg('local'))
        self.blocked('git add src/__pycache__/x.pyc', self.msg('local'))
        self.allowed('git add .claude/hooks/guard.py .claude/settings.json')
        self.allowed('git add data/build-inspector.luau')
        self.allowed('git commit -m "fix: add -A handling"')
        self.allowed("git commit -F - <<'EOF'\ngit add -A\nEOF")

    def test_push(self):
        self.blocked('git push --force origin feat', self.msg('push'))
        self.blocked('git push origin +feat', self.msg('push'))
        self.blocked('git push origin main', self.msg('push_main'))
        self.blocked('git push origin HEAD:refs/heads/main', self.msg('push_main'))
        self.blocked('git push --all', self.msg('push_main'))
        self.allowed('git push -u origin chore/claude-tooling')
        self.allowed('git push')
        with tempfile.TemporaryDirectory() as tmp:
            on_main = git_repo(os.path.join(tmp, 'm'), branch='main')
            self.blocked('git push', self.msg('push_main'), cwd=on_main)
            self.blocked('git push origin HEAD', self.msg('push_main'), cwd=on_main)
            self.blocked('git push origin "$(git branch --show-current)"', self.msg('push_main'), cwd=on_main)
            self.blocked(f'cd {on_main} && git push', self.msg('push_main'))
            self.blocked(f'pushd {on_main}; git push', self.msg('push_main'))
            self.blocked(f'env -C {on_main} git push', self.msg('push_main'))
            self.blocked(f'git -C {on_main} push', self.msg('push_main'))
            self.blocked(f'bash -c "cd {on_main} && git push"', self.msg('push_main'))
            git('-C', on_main, 'checkout', '-q', '-b', 'feat')
            self.allowed('git push', cwd=on_main)
            self.blocked('cd "$SOMEWHERE" && git push', self.msg('push_unknown'), cwd=on_main)
            self.blocked('GIT_DIR=/x/.git git push', self.msg('push_unknown'))
            self.blocked('export GIT_DIR=/x/.git; git push', self.msg('push_unknown'))
            self.allowed('cd "$SOMEWHERE" && git push -u origin feat', cwd=on_main)

    def test_messages_name_no_app(self):
        g = core.Guard(default, self.root)
        for key, text in g.config['messages'].items():
            for app in ('PlasmaZones', 'Afterglow', 'plasmazonesd', 'afterglow'):
                self.assertNotIn(app, text, key)


class Edits(Case):
    def test_build_trees(self):
        g = self.guard()
        for rel in ('build/CMakeCache.txt', 'build-audit/x.cpp', '.cache/cpm/luau/x.h'):
            self.assertIsNotNone(g.edit(os.path.join(self.root, rel)), rel)
        for rel in ('src/main.cpp', 'data/build-inspector.luau', 'Testing/x.log'):
            self.assertIsNone(g.edit(os.path.join(self.root, rel)), rel)
        self.assertIsNone(g.edit('/tmp/build/x'))


class FailClosed(unittest.TestCase):
    def run_guard(self, stdin, project):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=project)
        return subprocess.run([sys.executable, '-I', str(HERE / 'guard.py')], input=stdin, capture_output=True,
                              text=True, env=env, cwd='/')

    def test_malformed(self):
        g = core.Guard(default, '/tmp')
        for call in ([], 'x', {'tool_name': 5}, {'tool_name': 'Bash', 'tool_input': []},
                     {'tool_name': 'Bash', 'tool_input': {'command': 5}},
                     {'tool_name': 'Edit', 'tool_input': {'file_path': ['x']}},
                     {'tool_name': 'Bash', 'tool_input': {'command': 'ls'}, 'cwd': 3}):
            with self.assertRaises(ValueError, msg=repr(call)):
                g.call(call)
        with tempfile.TemporaryDirectory() as tmp:
            for stdin in ('', 'not json', '[]', '{"tool_name":"Bash","tool_input":{"command":5}}'):
                out = self.run_guard(stdin, tmp)
                self.assertEqual(out.returncode, 2, stdin)
                self.assertIn('could not check this call', out.stderr, stdin)

    def test_isolated_end_to_end(self):  # decision 4: runs under python3 -I from any directory
        with tempfile.TemporaryDirectory() as tmp:
            call = {'tool_name': 'Bash', 'tool_input': {'command': 'sudo ls'}, 'cwd': tmp}
            out = self.run_guard(json.dumps(call), tmp)
            self.assertEqual(out.returncode, 2)
            self.assertIn('Do not use sudo', out.stderr)
            call['tool_input']['command'] = 'ls'
            out = self.run_guard(json.dumps(call), tmp)
            self.assertEqual((out.returncode, out.stderr), (0, ''))
            out = self.run_guard(json.dumps({'tool_name': 'Read', 'tool_input': {'file_path': '/x'}}), tmp)
            self.assertEqual(out.returncode, 0)


class Selection(unittest.TestCase):
    def test_repositories(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, module in (('PlasmaZones', plasmazones), ('Afterglow', afterglow), ('workspace', workspace),
                                 ('phosphor-libs', default), ('Lambent', default)):
                path = git_repo(os.path.join(tmp, name))
                self.assertIs(guard.repository_module(guard.repository_name(path)), module, name)
                sub = os.path.join(path, 'src', 'deep')
                os.makedirs(sub)
                self.assertIs(guard.repository_module(guard.repository_name(sub)), module, name)
            # A linked worktree counts as its main checkout
            wt = os.path.join(tmp, 'Afterglow', '.claude', 'worktrees', 'agent-1')
            git('-C', os.path.join(tmp, 'Afterglow'), 'worktree', 'add', '-q', '-b', 'w', wt)
            self.assertEqual(guard.repository_name(wt), 'Afterglow')
            # Not a repository: the directory's own name, case-insensitively
            plain = os.path.join(tmp, 'plain', 'AFTERGLOW')
            os.makedirs(plain)
            self.assertIs(guard.repository_module(guard.repository_name(plain)), afterglow)
            self.assertIs(guard.repository_module('../evil'), default)
            self.assertIs(guard.repository_module('__init__'), default)
            with mock.patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': os.path.join(tmp, 'PlasmaZones')}):
                self.assertIs(guard.guard_for().repo, plasmazones)


class PlasmaZones(Case):
    repo = plasmazones

    def test_install(self):
        for c in ('make post-install', 'moon run repo:install', 'moon run repo:post-install',
                  'DESTDIR=/tmp/stage moon run repo:post-install', 'make uninstall'):
            self.blocked(c, self.msg('install'))
        for c in ('DESTDIR=/tmp/stage moon run repo:install', 'moon run plasmazones:build'):
            self.allowed(c)
        self.assertIn('PlasmaZones', self.msg('install'))

    def test_kill_messages(self):
        self.blocked('pkill -f plasmazonesd', plasmazones.CONFIG['messages']['pkill'])
        self.blocked('kill $(pgrep -f plasmazonesd)', plasmazones.CONFIG['messages']['pgrep_kill'])

    def test_host_dbus(self):
        M = plasmazones.MSG_HOST_DBUS
        self.blocked('qdbus6 org.phosphor_works.Placement /org/phosphor_works/Placement', M)
        self.blocked('busctl --user call org.phosphor_works.Placement /X a b', M)
        self.blocked('dbus-send --session --dest=org.phosphor_works.Placement /X a.b', M)
        self.blocked('bash -c "qdbus6 org.phosphor_works.Placement"', M)
        self.allowed('. "$XDG_RUNTIME_DIR/pz-nested/env.sh"; qdbus6 org.phosphor_works.Placement '
                     '/org/phosphor_works/Placement')
        self.allowed('bash -c \'. "$XDG_RUNTIME_DIR/pz-nested/env.sh" && qdbus6 org.phosphor_works.Placement\'')
        self.allowed('. "$XDG_RUNTIME_DIR/pz-nested/env.sh"; bash -c "qdbus6 org.phosphor_works.Placement"')
        self.allowed('export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/b; qdbus6 org.phosphor_works.Placement')
        self.allowed('DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/dbus-x qdbus6 org.phosphor_works.Placement')
        self.allowed('DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/x bash -c "qdbus6 org.phosphor_works.Placement"')
        self.allowed('dbus-run-session -- qdbus6 org.phosphor_works.Placement')
        self.allowed('gdbus call --address unix:path=/tmp/b --dest org.phosphor_works.Placement -o /X -m a.b')
        self.blocked('gdbus call --session --dest org.phosphor_works.Facet -o /org/phosphor_works/Facet -m a.b', M)
        self.allowed('qdbus6 org.kde.KWin /KWin supportInformation')
        self.allowed('grep -rn org.phosphor_works plasmazones/dbus')

    def test_desktop(self):
        M = plasmazones.MSG_DESKTOP
        self.blocked('kwin_wayland --replace &', M)
        self.blocked('plasmashell --replace', M)
        self.blocked('kquitapp6 plasmashell', M)
        self.blocked('systemctl --user restart plasmazones.service', M)
        self.blocked('systemctl --user stop plasma-kwin_wayland.service', M)
        self.allowed('systemctl --user status plasmazones.service')
        self.allowed('journalctl --user -u plasma-kwin_wayland.service -n 50')
        self.allowed('scripts/nested-kwin/run-nested.sh 2 1600 900')
        self.allowed('dbus-run-session -- bash -c "kwin_wayland --replace"')

    def test_local_paths(self):
        self.blocked('git add .claude/audit-state.json', self.msg('local'))
        self.blocked('git add Testing/Temporary/LastTest.log', self.msg('local'))
        self.blocked('git add scratchpad/notes.txt', self.msg('local'))
        self.blocked('git add .moon/cache/x', self.msg('local'))
        self.allowed('git add data/build-inspector.luau')

    def test_build_trees(self):
        g = self.guard()
        for rel in ('build/CMakeCache.txt', 'build-audit/x.cpp', '.cache/cpm/luau/x.h', 'Testing/x.log',
                    '.moon/cache/x', '.claude/worktrees/pr1165/build/x.cpp'):
            self.assertIsNotNone(g.edit(os.path.join(self.root, rel)), rel)
        for rel in ('plasmazones/src/daemon/daemon.cpp', '.claude/hooks/guard.py',
                    'cmake/PlasmaZonesDependencies.cmake', '.claude/worktrees/pr1165/plasmazones/src/x.cpp'):
            self.assertIsNone(g.edit(os.path.join(self.root, rel)), rel)
        self.assertIsNone(g.edit('/tmp/build/x'))


# The user's session as the Afterglow rules see it: a pane of the user's Afterglow on wayland-0
SESSION = {'XDG_RUNTIME_DIR': RUN, 'WAYLAND_DISPLAY': 'wayland-0',
           'AFTERGLOW_SOCKET': f'{RUN}/afterglow-wayland-0.sock',
           'AFTERGLOW_PANE_ID': '3', 'HOME': os.path.expanduser('~')}


class Afterglow(Case):
    repo = afterglow

    def setUp(self):
        patcher = mock.patch.dict(os.environ, SESSION)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop('XDG_STATE_HOME', None)

    def test_ctl(self):
        self.blocked('afterglow ctl list-panes', afterglow.MSG_CTL)
        self.blocked('aglow run build', afterglow.MSG_CTL)
        self.blocked('WAYLAND_DISPLAY=wayland-9 afterglow ctl list-panes', afterglow.MSG_CTL)  # pane socket wins
        self.allowed('AFTERGLOW_SOCKET=/tmp/t/test.sock AFTERGLOW_PANE_ID= afterglow ctl list-panes')
        self.allowed('env -u AFTERGLOW_SOCKET -u AFTERGLOW_PANE_ID WAYLAND_DISPLAY=wayland-9 afterglow ctl x')
        self.allowed('afterglow ctl --help')
        self.allowed('afterglow ctl list-panes', tool=afterglow.MCP_RUN)  # the agent session's own pane

    def test_mux(self):
        for c in ('afterglow mux ls', 'aglow-mux', 'afterglow-mux', 'afterglow ctl --session s list',
                  'afterglow --mux-attach work', 'XDG_RUNTIME_DIR=/tmp/r afterglow mux ls',
                  'XDG_RUNTIME_DIR=/tmp/r XDG_STATE_HOME=/tmp/s afterglow mcp',
                  'systemctl --user restart aglow-mux', 'systemctl --user stop afterglow-mux.service',
                  'systemctl --user kill app.slice', f'rm -rf {RUN}/aglow-mux', f'rm {RUN}/aglow-mux/x.sock',
                  'rm -rf "$XDG_RUNTIME_DIR/aglow-mux"', 'rm -rf ~/.local/state'):
            self.blocked(c, afterglow.MSG_MUX)
        for c in ('afterglow mux', 'afterglow mux --help', 'afterglow mcp --help', 'aglow-mux --version',
                  'XDG_RUNTIME_DIR=/tmp/r XDG_STATE_HOME=/tmp/s afterglow mux ls',
                  'XDG_RUNTIME_DIR=/tmp/r XDG_STATE_HOME=/tmp/s bash -c "afterglow mux ls"',
                  'XDG_RUNTIME_DIR=/tmp/r XDG_STATE_HOME=/tmp/s XDG_CONFIG_HOME=/tmp/c HOME=/tmp/h afterglow mcp',
                  'systemctl --user status aglow-mux', 'rm -rf build/mux'):
            self.allowed(c)

    def test_mcp_build(self):
        self.blocked('claude mcp add afterglow build/afterglow/afterglow mcp', afterglow.MSG_MCP_BUILD)
        self.blocked('claude mcp add ag /src/build-asan/afterglow/afterglow mcp', afterglow.MSG_MCP_BUILD)
        self.allowed('claude mcp add afterglow /usr/bin/afterglow mcp')

    def test_launch(self):
        for c in ('afterglow', './build/afterglow/afterglow -e htop', 'valgrind build/afterglow/afterglow',
                  'gdb --args build/afterglow/afterglow', 'heaptrack afterglow --title x'):
            self.blocked(c, afterglow.MSG_LAUNCH)
        for c in ('afterglow --version', 'afterglow --help', 'afterglow --config-reference',
                  'WAYLAND_DISPLAY=wayland-9 afterglow', 'XDG_RUNTIME_DIR=/tmp/nested afterglow',
                  'gdb -batch -ex run build/afterglow/afterglow'):
            self.allowed(c)

    def test_messages(self):
        self.blocked('pkill afterglow', afterglow.CONFIG['messages']['pkill'])
        self.blocked('kill $(pgrep afterglow)', afterglow.CONFIG['messages']['pgrep_kill'])
        self.blocked('cmake --install build', afterglow.CONFIG['messages']['install'])

    def test_build_inspector(self):
        self.allowed('git add examples/scripts/build-inspector.luau')
        self.allowed('git add build-inspector.luau')
        self.blocked('git add build/afterglow/x', self.msg('local'))
        self.assertIsNone(self.guard().edit(os.path.join(self.root, 'build-inspector.luau')))

    def test_mcp_tool_call(self):
        g = self.guard()
        call = {'tool_name': afterglow.MCP_RUN, 'tool_input': {'command': 'sudo make'}}
        self.assertEqual(g.call(call), g.message('sudo'))
        call['tool_input']['command'] = 'afterglow mux ls'
        self.assertEqual(g.call(call), afterglow.MSG_MUX)
        call['tool_input']['command'] = 'afterglow ctl list-panes'
        self.assertIsNone(g.call(call))
        self.assertIsNone(core.Guard(default, self.root).call(call))  # not a shell tool of other repositories


class AfterglowFiles(unittest.TestCase):
    """Generated files and the sibling repositories, in a tree like phosphor-works/."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = self.tmp.name
        self.app = git_repo(os.path.join(base, 'Afterglow'))
        self.libs = git_repo(os.path.join(base, 'phosphor-libs'))
        self.pz = git_repo(os.path.join(base, 'PlasmaZones'))
        self.other = git_repo(os.path.join(base, 'Lambent'))
        self.wt = os.path.join(self.app, '.claude', 'worktrees', 'a')
        git('-C', self.app, 'worktree', 'add', '-q', '-b', 'w', self.wt)

    def test_generated(self):
        g = core.Guard(afterglow, self.app)
        msg = g.edit(os.path.join(self.app, 'docs/CONFIGURATION.md'))
        self.assertIn('generate-reference.py', msg)
        unicode_tables = os.path.join(self.app, 'libs/afterglow-vt/src/UnicodeTables.inc')
        self.assertIn('gen_unicode_tables.py', g.edit(unicode_tables))
        self.assertIsNone(g.edit(os.path.join(self.app, 'docs/MUX.md')))
        self.assertIsNotNone(g.edit(os.path.join(self.app, 'build/x.cpp')))

    def test_siblings(self):
        for project in (self.app, self.wt):  # a worktree's siblings are those of its main checkout
            g = core.Guard(afterglow, project)
            msg = g.edit(os.path.join(self.libs, 'src/x.cpp'))
            self.assertIsNotNone(msg)
            self.assertIn('phosphor-libs', msg)
            self.assertIsNotNone(g.edit(os.path.join(self.pz, 'CMakeLists.txt')))
            self.assertIsNone(g.edit(os.path.join(self.other, 'x')))
            self.assertIsNotNone(g.bash(f'git -C {self.libs} commit -m x', project))
            self.assertIsNotNone(g.bash(f'cd {self.pz} && git add src/x.cpp', project))
            self.assertIsNone(g.bash(f'git -C {self.libs} log', project))
            self.assertIsNone(g.bash(f'git -C {self.other} add x', project))
        # Other repositories protect no siblings
        for repo in (workspace, plasmazones, default):
            self.assertIsNone(core.Guard(repo, self.app).edit(os.path.join(self.libs, 'src/x.cpp')), repo)


class Workspace(Case):
    repo = workspace

    def setUp(self):
        patcher = mock.patch.dict(os.environ, SESSION)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_union(self):
        self.blocked('qdbus6 org.phosphor_works.Placement /X', plasmazones.MSG_HOST_DBUS)
        self.blocked('kwin_wayland --replace', plasmazones.MSG_DESKTOP)
        self.blocked('moon run repo:post-install', self.msg('install'))
        self.blocked('afterglow ctl list-panes', afterglow.MSG_CTL)
        self.blocked('afterglow mux ls', afterglow.MSG_MUX)
        self.blocked('afterglow', afterglow.MSG_LAUNCH)
        self.allowed('afterglow ctl list-panes', tool=afterglow.MCP_RUN)
        self.allowed('cmake --workflow --preset dev')
        self.assertIsNone(self.guard().edit(os.path.join(os.path.dirname(self.root), 'PlasmaZones', 'x.cpp')))


if __name__ == '__main__':
    unittest.main()

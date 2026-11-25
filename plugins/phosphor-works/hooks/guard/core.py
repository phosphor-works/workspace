# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""The rules that every phosphor-works repository shares, and the reading of a command line.

The guard catches the plain form of a mistake that a session makes in good faith: `pkill NAME`, `sudo`,
`git add -A`, `git push origin main`, an install of the build, an edit of a generated file. It is not a security
boundary. A shell is too expressive for a list of command shapes to be complete, and a program that wants to get
past the guard can write a script and run it. So the guard reads a command line simply, and a rule covers the
spelling that a session types, not every spelling that the shell accepts. Do not add rules for unusual spellings
(commands hidden in parallel, find -exec, nested quoting, encoded delimiters): that work never ends and makes the
guard slow and fragile. Add a rule only for a mistake that a session made, or would make, in its plain form.

How a Bash command is read: the bodies of here-documents (commit messages) are text. Comments are left out, and
nothing is special inside single quotes. The rest is split into simple commands at ; & | newlines, parentheses and
backquotes outside quotes, and each one is tokenized with its quotes removed. The commands in $(...) and
backquotes are read too, nested ones included, and so is the script of `bash -c` (also `bash -lc`), `sh -c`,
`zsh -c`, `dash -c` and `eval`. The words in front of a command (VAR=value, env, timeout, nice, nohup, sudo,
systemd-run...) are skipped, and the variables that they set are kept for the rules that look at the environment.
A nested shell inherits the variables and wrappers of the command that starts it.

The core holds no application names: the messages and the paths that differ come from the CONFIG of the
repository module (repos/<name>.py), which may also have a check() for rules that are too behavioural for config.
"""

import os
import re
import shlex
import subprocess

# Reading a command line

SEPARATORS = ';&|()\n`'
# Words that run the command after them: skipped, with their options, to find the command itself
WRAPPERS = set(
    'then do else elif if while until ! { } time nohup env exec command builtin xargs timeout nice ionice stdbuf '
    'setsid unbuffer systemd-run dbus-run-session sudo doas pkexec run0 valgrind heaptrack strace ltrace catchsegv'
    .split()
)
# Wrapper options that take the next word as their value
WRAPPER_VALUES = {
    'env': {'-C', '--chdir', '-u', '--unset', '-S', '--split-string'},
    'timeout': {'-s', '--signal', '-k', '--kill-after'},
    'nice': {'-n', '--adjustment'},
    'ionice': {'-c', '--class', '-n', '--classdata', '-p', '--pid'},
    'stdbuf': {'-i', '--input', '-o', '--output', '-e', '--error'},
    'xargs': {'-I', '--replace', '-d', '--delimiter', '-a', '--arg-file', '-E', '-n', '--max-args', '-P', '-s'},
    'exec': {'-a'},
    'time': {'-f', '--format', '-o', '--output'},
    'systemd-run': {'-p', '--property', '-E', '--setenv', '-u', '--unit', '--description', '--slice', '-M',
                    '--machine', '--uid', '--gid', '--nice', '--working-directory'},
    'dbus-run-session': {'--config-file', '--dbus-daemon'},
    'strace': {'-o', '-e', '-p', '-s', '-u', '-E', '--output', '--trace', '--string-limit', '--user', '--env'},
    'ltrace': {'-o', '-e', '-p', '-s', '-u', '--output'},
}
# Debuggers that start the program after these words: gdb --args PROGRAM, lldb -- PROGRAM, rr record PROGRAM
DEBUGGER_STARTS = {'gdb': '--args', 'lldb': '--', 'rr': 'record'}
SHELLS = {'bash', 'sh', 'zsh', 'dash'}
KILL_BY_NAME = {'pkill', 'killall', 'killall5', 'skill'}
PRIVILEGED = {'sudo', 'sudoedit', 'doas', 'su', 'pkexec', 'run0'}
INSTALL_TARGET = re.compile(r'^install(/(strip|local|fast))?$')
TEMPORARY = ('/tmp/', '/var/tmp/')
# A directory the guard cannot know before the shell runs: $(...), $VAR, a backquote command, cd -, GIT_DIR
UNKNOWN = object()
EDIT_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
GIT_VALUE_OPTIONS = ('-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env')
# git subcommands that change a repository: refused in a protected sibling repository
GIT_WRITES = {'add', 'stage', 'commit', 'push', 'rm', 'mv', 'reset', 'checkout', 'switch', 'rebase', 'merge',
              'cherry-pick', 'revert', 'tag', 'restore', 'stash', 'apply', 'am'}


class Command:
    """One simple command: its environment changes (('set', NAME, VALUE), ('unset', NAME) or ('clear',)), the
    wrappers in front of it, the directories that its wrappers run it in, its command word and its arguments."""

    __slots__ = ('env', 'wrappers', 'chdirs', 'word', 'args')

    def __init__(self, env, wrappers, chdirs, word, args):
        self.env, self.wrappers, self.chdirs, self.word, self.args = env, wrappers, chdirs, word, args

    def sets(self, name):
        """Whether this command's own words (or the shell that runs it) set NAME."""
        return any(c[0] == 'set' and c[1] == name for c in self.env)


def strip_heredocs(command):
    """The command with the bodies of its here-documents left out: they are text (commit messages, PR bodies)."""
    out, pos = [], 0
    for m in re.finditer(r'<<-?[ \t]*([\'"]?)([A-Za-z_][A-Za-z0-9_]*)\1', command):
        if m.start() < pos:
            continue
        body = command.find('\n', m.end())
        if body < 0:
            break
        end = re.compile(r'^[ \t]*%s[ \t]*$' % re.escape(m.group(2)), re.M).search(command, body + 1)
        if not end:
            break
        out.append(command[pos : body + 1])
        pos = end.end()
    out.append(command[pos:])
    return ''.join(out)


def tokens(command):
    lex = shlex.shlex(command, posix=True, punctuation_chars=SEPARATORS)
    lex.whitespace = ' \t\r'
    lex.whitespace_split = True
    lex.commenters = ''
    try:
        return list(lex)
    except ValueError:  # unbalanced quotes: split at whitespace and separators, quotes dropped
        return re.findall(r'[%s]+|[^\s%s]+' % (re.escape(SEPARATORS), re.escape(SEPARATORS)),
                          command.replace('"', '').replace("'", ''))


def without_substitutions(command):
    """(the command line with each $(...) and backquote command as one word, $SUBST; the bodies of those commands).
    Quotes are followed as the shell follows them: nothing is special inside single quotes or after a #."""
    out, bodies, i, quote, word_start = [], [], 0, '', True
    while i < len(command):
        ch = command[i]
        if quote == "'" or (not quote and ch == '#' and word_start):
            end = command.find("'", i) if quote else command.find('\n', i + 1)
            end = len(command) if end < 0 else end + (quote == "'")
            if quote:  # a comment is left out: it is not a command, and its apostrophes are not quotes
                out.append(command[i:end])
            i, quote, word_start = end, '', False
            continue
        if ch == '\\':
            if command[i + 1 : i + 2] != '\n':  # a backslash before a newline joins the lines
                out.append(command[i : i + 2])
            i, word_start = i + 2, False
            continue
        word_start = not quote and ch in ' \t\n;&|('
        if ch in '\'"' and quote in ('', ch) and not (ch == "'" and quote):
            quote = '' if quote else ch
        if command.startswith('$(', i):
            depth, j = 1, i + 2
            while j < len(command) and depth:
                depth += {'(': 1, ')': -1}.get(command[j], 0)
                j += 1
            if not depth:
                out.append('$SUBST')
                bodies.append(command[i + 2 : j - 1])
                i = j
                continue
        elif ch == '`':
            j = command.find('`', i + 1)
            if j >= 0:
                out.append('$SUBST')
                bodies.append(command[i + 1 : j])
                i = j + 1
                continue
        out.append(ch)
        i += 1
    return ''.join(out), bodies


def simple_commands(command):
    """Every simple command (a Command) in a command line, including the ones in a command substitution. A
    substitution inside single quotes or a comment is text, as in the shell."""
    command = strip_heredocs(command)
    lines, pending = [], [command]
    while pending:
        line, bodies = without_substitutions(pending.pop())
        lines.append(line)
        pending += bodies
    for line in lines:
        words = []
        for tok in tokens(line) + [';']:
            if tok and all(ch in SEPARATORS for ch in tok):
                if words:
                    yield split_wrappers(words)
                words = []
            else:
                words.append(tok)


def split_wrappers(words):
    """The Command of the words of one simple command."""
    env, wrappers, chdirs, i = [], [], [], 0
    while i < len(words):
        w = words[i]
        name = os.path.basename(w)
        if m := re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', w, re.S):
            env.append(('set', m.group(1), m.group(2)))
            if m.group(1) in ('GIT_DIR', 'GIT_WORK_TREE'):
                chdirs.append('$')  # git then runs elsewhere
            i += 1
        elif name in WRAPPERS:
            wrappers.append(name)
            values = WRAPPER_VALUES.get(name, set())
            i += 1
            while i < len(words):
                a = words[i]
                value = words[i + 1] if i + 1 < len(words) else None
                if name == 'env' and a in ('-i', '--ignore-environment', '-'):
                    env.append(('clear',))
                elif name == 'env' and a in ('-u', '--unset') and value is not None:
                    env.append(('unset', value))
                    i += 1
                elif name == 'env' and a.startswith('--unset='):
                    env.append(('unset', a.split('=', 1)[1]))
                elif name == 'env' and re.match(r'^-u.', a):
                    env.append(('unset', a[2:]))
                elif name == 'env' and a in ('-C', '--chdir') and value is not None:
                    chdirs.append(value)
                    i += 1
                elif name == 'env' and a.startswith('--chdir='):
                    chdirs.append(a.split('=', 1)[1])
                elif name == 'env' and re.match(r'^-C.', a):
                    chdirs.append(a[2:])
                elif name == 'systemd-run' and a in ('-E', '--setenv') and value is not None:
                    n, _, v = value.partition('=')
                    env.append(('set', n, v))
                    i += 1
                elif a in values:
                    i += 1
                elif not (a.startswith('-') and a != '-') and not (
                        name == 'timeout' and re.match(r'^[\d.]+[smhd]?$', a)):
                    break
                i += 1
        else:
            return Command(env, wrappers, chdirs, name, words[i + 1 :])
    return Command(env, wrappers, chdirs, '', [])


def environment(changes):
    """The environment of a command: this session's, with CHANGES applied in order. A value that the shell expands
    is None: the guard cannot know it."""
    env = dict(os.environ)
    for change in changes:
        if change[0] == 'clear':
            env.clear()
        elif change[0] == 'unset':
            env.pop(change[1], None)
        else:
            env[change[1]] = None if any(mark in change[2] for mark in '$`*?[~') else change[2]
    return env


def short_flags(arg):
    return arg[1:] if re.match(r'^-[A-Za-z]+$', arg) else ''


def under_tmp(path):
    """An absolute path, written out, under /tmp or /var/tmp. A relative path, ~ or $VAR is resolved by the shell,
    in a place the guard does not know."""
    return isinstance(path, str) and path.startswith('/') and os.path.realpath(path).startswith(TEMPORARY)


def shell_script(cmd):
    """The script that a shell's -c (also a combined flag like -lc) or eval runs, or None."""
    if cmd.word in SHELLS:
        flag = next((k for k, a in enumerate(cmd.args) if a == '-c' or 'c' in short_flags(a)), None)
        if flag is not None and flag + 1 < len(cmd.args):
            return cmd.args[flag + 1]
    elif cmd.word == 'eval' and cmd.args:
        return ' '.join(cmd.args)
    return None


# Directories

def resolve(base, target):
    """Where `cd TARGET` from BASE lands, or UNKNOWN when the shell decides (expansions, cd -)."""
    if base is UNKNOWN or '$' in target or '`' in target or target == '-':
        return UNKNOWN
    path = os.path.abspath(os.path.join(base, os.path.expanduser(target)))
    # A cd that fails leaves the shell where it was, which is kept; a directory that mkdir made earlier in the
    # command belongs to the repository of its nearest existing parent.
    while path != '/' and not os.path.isdir(path):
        path = os.path.dirname(path)
    return path


def main_checkout(repo):
    """The main working tree of the repository at REPO. A linked worktree (git worktree add, .claude/worktrees/...)
    has a .git file that names its git directory, whose commondir file names the main .git directory. Read without
    running git. Anything unexpected keeps REPO."""
    try:
        with open(os.path.join(repo, '.git')) as f:
            line = f.readline().strip()
        if not line.startswith('gitdir:'):
            return repo
        gitdir = os.path.join(repo, line[len('gitdir:') :].strip())
        with open(os.path.join(gitdir, 'commondir')) as f:
            common = os.path.realpath(os.path.join(gitdir, f.readline().strip()))
    except (OSError, UnicodeDecodeError):  # the main checkout's .git is a directory
        return repo
    return os.path.dirname(common) if os.path.basename(common) == '.git' else repo


def toplevel(directory):
    """The top of the git working tree that holds DIRECTORY, or None."""
    try:
        out = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, timeout=5,
                             cwd=directory)
    except (OSError, subprocess.SubprocessError):
        return None
    return (out.stdout.strip() or None) if out.returncode == 0 else None


# git

def git_subcommand(args):
    """The git subcommand and its arguments, after git's own options (-C dir, -c key=value...)."""
    i = 0
    while i < len(args) and args[i].startswith('-'):
        i += 1 + (args[i] in GIT_VALUE_OPTIONS)
    return (args[i], args[i + 1 :]) if i < len(args) else ('', [])


def git_directory(args, cwd):
    """The directory git runs in: CWD, then its own -C options (they stack, like cd)."""
    directory, i = cwd, 0
    while i < len(args) and args[i].startswith('-'):
        if args[i] == '-C' and i + 1 < len(args):
            directory = resolve(directory, args[i + 1])
        elif args[i].startswith(('--git-dir', '--work-tree')):
            directory = UNKNOWN
        i += 1 + (args[i] in GIT_VALUE_OPTIONS)
    return directory


def current_branch(directory):
    """The branch checked out in DIRECTORY, or None when git cannot tell."""
    try:
        out = subprocess.run(['git', 'symbolic-ref', '--short', '-q', 'HEAD'], capture_output=True, text=True,
                             timeout=5, cwd=directory)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


# Messages. The repository's CONFIG overrides any of them, and names its applications there.

MESSAGES = {
    'broad': 'Stage files by name (git add path...), not with -A, -u, ., *, :/ or commit -a.',
    'push': 'Never force-push. Fix the branch with a new commit instead.',
    'push_main': ('Never push to main. Push a branch and open a pull request. The user merges it. '
                  'If this command makes the branch, name it: git push -u origin BRANCH.'),
    'push_unknown': ('This push names no branch, and the command runs git in a directory the guard cannot '
                     'resolve. Name the branch: git push -u origin BRANCH.'),
    'pkill': ('pkill and killall match by name: the name can match a program that the user runs on this desktop, '
              'and the pattern can match the shell that runs the command. Use `pgrep -a NAME`, then `kill PID` on '
              'a process that you started.'),
    'pgrep_kill': ("kill with the PIDs that pgrep or pidof found can match the user's own programs, and pgrep -f "
                   'also matches the shell that runs the command, because its command line holds the pattern. '
                   'List the processes with `pgrep -a NAME`. Then run `kill PID` with the numbers in a separate '
                   'command.'),
    'sudo': ('Do not use sudo, su, doas, pkexec or run0. The user installs system packages. Tell the user what you '
             'need and why.'),
    'install': ('Never install or uninstall the build (cmake --install, the install or uninstall target, '
                'cmake_install.cmake). The user installs it. Only an install into a temporary directory '
                '(--prefix /tmp/... or DESTDIR=/tmp/... on the command itself) is allowed.'),
    'sibling': ('{path} is in {name}, which changes only through its own branch and pull request. Tell the user '
                'what it needs and why.'),
    'generated': '{rel} is generated. Change its source, then run: {command}',
    'build_tree': '{rel} is in a build tree. Change the source or CMake code that makes it.',
    'local': ('{paths} are local state and never go into git, and `git add -f` would bypass .gitignore. Stage only '
              'source files, by name.'),
}

# Local state that never goes into git, in every repository: Python caches, build trees (build/, build-asan/),
# .cache and Claude Code's own state. A file whose name starts with "build" is a source file (build-inspector.luau).
LOCAL_PATHS = [
    (r'(^|/)(__pycache__|\.cache)(/|$)|(^|/)build[^/]*/|(^|/)build[^/.]*$', '__pycache__/, build*/, .cache/'),
    (r'(^|/)\.claude/(worktrees|audit-|final-report|settings\.local|scheduled_tasks)',
     '.claude/worktrees/, .claude/settings.local.json, the .claude/audit-* ledgers'),
]
BUILD_TREE = r'^(build[^/]*|\.cache)/'

# The fields of a repository's CONFIG, with their defaults
DEFAULTS = {
    'messages': {},          # key -> text: overrides MESSAGES
    'local_paths': [],       # (regex, label) pairs that add to LOCAL_PATHS
    'build_tree': BUILD_TREE,  # regex over a path relative to the project: a tree that a build writes
    'generated': {},         # path relative to the project -> the command that makes it
    'protected_siblings': (),  # names of the checkouts beside this one that a session must not change
    'command_tools': (),     # tools other than Bash whose tool_input.command is a shell command
}


def configure(config):
    """The full configuration of a repository: DEFAULTS with CONFIG over them."""
    merged = dict(DEFAULTS)
    merged.update(config or {})
    messages = dict(MESSAGES)
    messages.update(merged['messages'])
    local = LOCAL_PATHS + list(merged['local_paths'])
    merged['local_regex'] = re.compile('|'.join('(?:%s)' % r for r, _ in local))
    if 'local' not in merged['messages']:
        messages['local'] = messages['local'].format(paths=', '.join(label for _, label in local))
    merged['messages'] = messages
    merged['build_regex'] = re.compile(merged['build_tree'])
    return merged


class Scope:
    """One shell: the directories a later git may run in, the state that a repository's check keeps across the
    commands of the line, and the environment changes and wrappers that its commands inherit."""

    def __init__(self, places, state=None, env=(), wrappers=()):
        self.places, self.state, self.env, self.wrappers = places, dict(state or {}), list(env), list(wrappers)


class Guard:
    """The checks of one repository. REPO is its module: CONFIG, and an optional check(cmd, guard, scope)."""

    def __init__(self, repo, project=None, tool='Bash'):
        self.repo = repo
        self.config = configure(getattr(repo, 'CONFIG', {}))
        self.project = project or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
        self.tool = tool
        self.cwd = None
        self._siblings = None

    def message(self, key, **fields):
        text = self.config['messages'][key]
        return text.format(**fields) if fields else text

    # The tool call

    def call(self, call):
        """The message that blocks the hook input CALL, or None. A malformed input raises ValueError."""
        if not isinstance(call, dict):
            raise ValueError('the hook input is not an object')
        tool = call.get('tool_name', '')
        params = call.get('tool_input', {})
        cwd = call.get('cwd')
        if not isinstance(tool, str) or not isinstance(params, dict) or not (cwd is None or isinstance(cwd, str)):
            raise ValueError('the hook input has a field of the wrong type')
        self.tool = tool
        if tool == 'Bash' or tool in self.config['command_tools']:
            command = params.get('command', '')
            if not isinstance(command, str):
                raise ValueError('the command is not a string')
            return self.bash(command, cwd)
        if tool in EDIT_TOOLS:
            path = params.get('file_path') or params.get('notebook_path') or ''
            if not isinstance(path, str):
                raise ValueError('the path is not a string')
            return self.edit(path)
        return None

    # Edits

    def siblings(self):
        """{name: root/} of the protected checkouts beside the main checkout of this project."""
        if self._siblings is None:
            names = self.config['protected_siblings']
            top = toplevel(self.project) if names else None
            base = main_checkout(os.path.realpath(top or self.project))
            self._siblings = {n: os.path.realpath(os.path.join(base, '..', n)) + '/' for n in names}
        return self._siblings

    def sibling(self, path):
        """The name of the protected sibling repository that holds PATH, or None."""
        real = os.path.realpath(path) + '/'
        return next((name for name, root in self.siblings().items() if real.startswith(root)), None)

    def edit(self, path):
        if name := self.sibling(path):
            return self.message('sibling', path=path, name=name)
        real = os.path.realpath(path)
        project = os.path.realpath(self.project) + '/'
        if not real.startswith(project):
            return None
        rel = real[len(project) :]
        if rel in self.config['generated']:
            return self.message('generated', rel=rel, command=self.config['generated'][rel])
        if self.config['build_regex'].match(rel):
            return self.message('build_tree', rel=rel)
        return None

    # Bash

    def bash(self, command, cwd=None, scope=None):
        """The message that blocks the shell command COMMAND, or None. CWD is a directory or a list of them."""
        if scope is None:
            self.cwd = cwd if isinstance(cwd, str) else None
            scope = Scope(list(cwd) if isinstance(cwd, list) else [cwd or os.getcwd()])
        cmds = [Command(scope.env + c.env, scope.wrappers + c.wrappers, c.chdirs, c.word, c.args)
                for c in simple_commands(command)]
        words, kills = set(), False
        k = 0
        while k < len(cmds):
            cmd = cmds[k]
            k += 1
            # The program that a debugger starts is checked as a command of its own
            if (start := DEBUGGER_STARTS.get(cmd.word)) and start in cmd.args:
                rest = cmd.args[cmd.args.index(start) + 1 :]
                if cmd.word == 'rr':
                    rest = [a for a in rest if not a.startswith('-')][:1] + rest[1:]
                if rest:
                    inner = split_wrappers(rest)
                    cmds.append(Command(cmd.env + inner.env, cmd.wrappers + [cmd.word] + inner.wrappers,
                                        cmd.chdirs + inner.chdirs, inner.word, inner.args))
            self.track_places(cmd, scope)
            words.add(cmd.word)
            # kill with PIDs that the shell fills in, or that xargs reads: not kill with numbers
            kills |= cmd.word == 'kill' and ('xargs' in cmd.wrappers or any('$' in a or '`' in a for a in cmd.args))
            if message := self.check_command(cmd, scope):
                return message
            script = shell_script(cmd)
            if script is not None:
                inner = Scope(list(scope.places), scope.state, cmd.env, cmd.wrappers)
                if message := self.bash(script, scope=inner):
                    return message
        # kill $(pgrep ...), pgrep ... | xargs kill, a loop over pidof
        if words & {'pgrep', 'pidof'} and kills:
            return self.message('pgrep_kill')
        return None

    def track_places(self, cmd, scope):
        """Add every directory a later git may run in: each cd, pushd and env -C target, and UNKNOWN after a
        GIT_DIR or GIT_WORK_TREE. A cd in a subshell or a failed cd leaves the start in place, so all of them are
        kept, not only the last."""
        targets = list(cmd.chdirs)
        if cmd.word in ('cd', 'pushd'):
            operands = [a for a in cmd.args if not a.startswith('-') or a == '-']
            targets += operands[:1] or ['~']
        if cmd.word == 'export' and any(a.startswith(('GIT_DIR=', 'GIT_WORK_TREE=')) for a in cmd.args):
            targets.append('$')
        places = scope.places + [resolve(place, t) for t in targets for place in scope.places]
        places = list(dict.fromkeys(places))
        if len(places) > 16:  # many cds: the guard stops guessing
            places = places[:16] + [UNKNOWN]
        scope.places = places

    def check_command(self, cmd, scope):
        word, args = cmd.word, cmd.args
        if word in KILL_BY_NAME:
            return self.message('pkill')
        if word in PRIVILEGED or PRIVILEGED & set(cmd.wrappers):
            return self.message('sudo')
        if self.is_install(cmd):
            return self.message('install')
        if word == 'git' and (message := self.check_git(args, scope.places)):
            return message
        check = getattr(self.repo, 'check', None)
        return check(cmd, self, scope) if check else None

    def temporary_destination(self, cmd):
        """Whether an install goes into a temporary directory: DESTDIR on the command itself, or --prefix,
        -DCMAKE_INSTALL_PREFIX, under /tmp or /var/tmp."""
        if under_tmp(environment(cmd.env).get('DESTDIR')):
            return True
        prefix = None
        for k, a in enumerate(cmd.args):
            if a == '--prefix' and k + 1 < len(cmd.args):
                prefix = cmd.args[k + 1]
            elif a.startswith('--prefix='):
                prefix = a.split('=', 1)[1]
            elif m := re.match(r'^-DCMAKE_INSTALL_PREFIX(:\w+)?=(.*)$', a):
                prefix = m.group(2)
            elif a.startswith('DESTDIR=') and cmd.word in ('make', 'gmake', 'ninja'):
                prefix = a[len('DESTDIR=') :]
        return under_tmp(prefix)

    def is_install(self, cmd):
        """Whether the command installs the build outside a temporary directory, or uninstalls it: cmake --install,
        an install or uninstall target of cmake --build, ninja or make, or cmake -P cmake_install.cmake."""
        word, args = cmd.word, cmd.args
        if word == 'cmake':
            targets = [args[k + 1] for k, a in enumerate(args[:-1]) if a in ('--target', '-t')]
            targets += [a.split('=', 1)[1] for a in args if a.startswith('--target=')]
            if 'uninstall' in targets:
                return True
            installs = ('--install' in args
                        or '-P' in args and any(os.path.basename(a) == 'cmake_install.cmake' for a in args)
                        or any(INSTALL_TARGET.match(t) for t in targets))
            return installs and not self.temporary_destination(cmd)
        if word in ('ninja', 'make', 'gmake'):
            if 'uninstall' in args:
                return True
            return any(INSTALL_TARGET.match(a) for a in args) and not self.temporary_destination(cmd)
        return False

    def check_git(self, args, places):
        sub, rest = git_subcommand(args)
        directories = [git_directory(args, place) for place in places]
        if sub in GIT_WRITES:
            for d in directories:
                if d is not UNKNOWN and (name := self.sibling(d)):
                    return self.message('sibling', path=d, name=name)
        if sub in ('add', 'stage'):
            paths, broad, force = [], False, False
            for k, a in enumerate(rest):
                if a == '--':
                    paths += rest[k + 1 :]
                    break
                if a.startswith('-'):
                    force |= a == '--force' or 'f' in short_flags(a)
                    broad |= a in ('--all', '--update', '--no-ignore-removal') or a.startswith('--pathspec-from-file')
                    broad |= 'A' in short_flags(a) or 'u' in short_flags(a)
                else:
                    paths.append(a)
            if force or any(self.config['local_regex'].search(p) for p in paths):
                return self.message('local')
            if broad or any(p in ('.', './', '..', '*', ':', ':/') or p.startswith((':/', ':(')) for p in paths):
                return self.message('broad')
        elif sub == 'commit':
            k = 0
            while k < len(rest) and rest[k] != '--':
                a = rest[k]
                k += 1
                if a == '--all':
                    return self.message('broad')
                for n, ch in enumerate(short_flags(a)):
                    if ch == 'a':
                        return self.message('broad')
                    if ch in 'mFCct':  # takes a value: the rest of the word, or the next word
                        k += n == len(a) - 2
                        break
        elif sub == 'push':
            for a in rest:
                if a.startswith(('--force', '--mirror')) or 'f' in short_flags(a) or a.startswith('+'):
                    return self.message('push')
            return self.pushes_main(rest, directories)
        return None

    def pushes_main(self, rest, directories):
        """The refusal for `git push ARGS`, if it can update main: a refspec whose destination is main, --all, or no
        refspec (push.default then pushes the current branch) while main is checked out in any directory the
        command may run git in. A directory the guard cannot resolve counts as main for HEAD and the current
        branch."""

        def current_is_main():
            if any(d is UNKNOWN for d in directories):
                return self.message('push_unknown')
            return self.message('push_main') if any(current_branch(d) == 'main' for d in directories) else None

        words, k = [], 0
        while k < len(rest):
            a = rest[k]
            k += 1
            if a in ('--all', '--branches'):
                return self.message('push_main')
            if a in ('-o', '--push-option', '--repo', '--receive-pack', '--exec'):
                k += 1
            elif not a.startswith('-'):
                words.append(a)
        refspecs = words[1:]
        if not refspecs:
            return current_is_main()
        for spec in refspecs:
            dst = spec.split(':', 1)[1] if ':' in spec else spec
            if dst in ('HEAD', '@') or '$' in dst:  # $(git branch --show-current) is the current branch
                if message := current_is_main():
                    return message
            elif dst.removeprefix('refs/').removeprefix('heads/') == 'main':
                return self.message('push_main')
        return None

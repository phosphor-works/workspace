---
name: debug
description: "Find why a phosphor-works test or program crashes or hangs: gdb in batch mode, watchpoints for memory that something overwrote, cores with coredumpctl, rr for a crash in some runs only, sanitizer builds, and the crash-triage agent for long backtraces. Use when: crash, segfault, SIGSEGV, SIGABRT, hang, deadlock, core dump, gdb, backtrace, a test that fails in some runs only."
---

<!--
SPDX-FileCopyrightText: 2026 fuddlesworth
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Debug a crash or a hang

A fix explains why the bug happens. The backtrace of a crash shows where the program fell, which is often not where
the bad value came from. Find the write that made the value.

Debug only the processes that you started: a test binary, a program from the build tree, or a process of a nested
session. Never attach gdb or any ptrace tool to the user's compositor, shell or own copy of an app: stopping it
freezes the user's session. A program that opens a window runs only in a nested session (the repository's verify
skill: `plasmazones:verify-live`, `afterglow:verify-live`, or Lambent's `scripts/nested-shell/`). The app skills add
their own cautions (`afterglow:debug`).

## When to dispatch crash-triage

Dispatch the `phosphor-works:crash-triage` agent for a core of a host process, for a backtrace of many threads, or
for a chain through logs and several libraries. It reads the full backtraces and logs and returns the mechanism, so
they stay out of the main context. Give it the PID or `coredumpctl` match, the log path, the build dir, the
repository and what you already know. For a crash that one `gdb -batch` call explains, do it yourself.

## Batch mode first

One `gdb -batch` call answers most questions. It took 3 tool calls and 20 seconds in a measurement, where gdb in
an interactive pane took 26 calls and 3 minutes for the same answer.

A crash in one test:

```sh
gdb -q -batch -ex run -ex bt -ex 'info locals' --args build/<path>/<test-binary> <args>
```

`ctest --test-dir build -R NAME -V` prints the command line of a test, with its environment. A test that ctest runs
through the `dbus-run-session` launcher can need the same launcher in front of gdb.

A value that something overwrote: stop before the write, watch the memory, and let the program run. The
watchpoint stops at the write, with the stack that made it.

```sh
gdb -q -batch -ex 'break functionBeforeTheWrite' -ex run -ex 'watch -l object.field' -ex continue -ex bt \
    --args PROGRAM ARGS
```

`watch -l` watches the address, so it outlives the scope of the expression. `ptype /o TYPE` gives the offsets of
the fields: an overflow from one field reaches the next.

A hang: start the program in the background, find its PID with `pgrep -a NAME`, and take the stacks of all its
threads:

```sh
gdb -q -batch -p PID -ex 'thread apply all bt'
```

Run a program that can fill the memory in `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0`, as
`phosphor-works:build` says.

## A crash in some runs only

Do not rerun until it passes. Read the core of a run that failed, then write a test that makes the crash happen
every time.

```sh
coredumpctl list --since today
coredumpctl debug PID --debugger-arguments="-q -batch -ex 'thread apply all bt'"
```

A memory error that does not crash every time: build the repository's ASan and UBSan tree (an `asan` preset of the
`workspace` superbuild, or the app's own sanitizer preset, see `phosphor-works:build`) and run the test there. ASan
names the write and the allocation.

When `command -v rr` finds `rr`, record the test until a run fails, then replay that run backwards from the crash:

```sh
rr record build/<path>/<test-binary> <args>        # repeat until it fails
rr replay -- -batch -ex continue -ex 'watch -l object.field' -ex reverse-continue -ex bt
```

`reverse-continue` stops at the last write to the watched address before the crash. `rr` needs
`/proc/sys/kernel/perf_event_paranoid` at 1 or lower. If it is higher, ask the user.

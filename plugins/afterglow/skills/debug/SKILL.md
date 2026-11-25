---
name: debug
description: "Afterglow's additions to phosphor-works:debug: which Afterglow processes you may debug, GoogleTest filters, the ASan tree, and gdb in a pane of the afterglow MCP server when the questions span several turns. Use when: crash, segfault, hang, core dump, gdb, backtrace, a test that fails in some runs only, in Afterglow."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Debug a crash or a hang in Afterglow

Follow `phosphor-works:debug` first: batch mode, watchpoints, cores, rr and the crash-triage agent. This skill adds
what is Afterglow's own. A fix explains why the bug happens (CLAUDE.md, "Find the mechanism").

Debug only the processes that you started: a test binary, a program from `build/`, or a test's own Afterglow.
Never attach to the user's `afterglow` or `aglow-mux`. This session usually runs in one of their panes. A program
that opens a window runs only in a nested KWin (`afterglow:verify-live`).

## Tests and builds

Most tests are GoogleTest binaries. Narrow the gdb run to the test that crashes:

```sh
gdb -q -batch -ex run -ex bt -ex 'info locals' --args build/afterglow/tests/afterglow_config_tests \
    --gtest_filter='Config.TheTestThatCrashes'
```

A memory error that does not crash every time: build `build-asan` (the `asan` preset) with ASan and UBSan (`afterglow:build`) and run
the test there.

For a crash in some runs only, the native suite lesson in CLAUDE.md applies: read the core, then write a test that
makes the crash happen every time.

## gdb in a pane of the agent session

The `afterglow` MCP server (`.mcp.json`) keeps a program running between turns. Use a pane for gdb only when the
questions come one after the other over several turns: a breakpoint that leads to the next one, or a state that
you want to look at again after you read the code.

1. Open a pane in the repository: `open_pane` with `where` `tab` and `cwd` the repository root.
2. Start gdb with `send` and `text` `gdb -q --args PROGRAM ARGS` and a line end.
3. Wait for its prompt: `wait` with `until` `text` and `pattern` `^\(gdb\) $`. After a send, the wait reads only
   what gdb writes after your input, so the old prompt does not match.
4. Send each command the same way, wait for the prompt, and `read` the screen when the wait's output is too short.
5. End with `quit` and `close_pane`.

A pane runs in the cgroup of the user's `aglow-mux.service`. A program that can fill the memory runs in
`systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0` there too.

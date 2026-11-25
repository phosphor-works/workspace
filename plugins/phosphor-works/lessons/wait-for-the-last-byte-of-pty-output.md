---
id: wait-for-the-last-byte-of-pty-output
title: A test that waits for the first byte a program printed has not seen the rest of the output
repos: [all]
domains: [test, terminal]
added: 2026-11-25
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

Afterglow's PaneEvents.AWriteAtThePromptGoesOnlyToAnEmptyCommandLine failed once in the workspace superbuild and
never in 900 local runs. The child printed one string: an `x`, then OSC 133 prompt marks. The test waited for the
`x` on the screen, then read the shell state. A PTY can give one write to the reader in more than one read, and the
reader feeds each read to the terminal, so the `x` was on the screen before the marks were read. A sequence that
changes no screen text (an OSC mark, a mode) cannot be waited for at all. End the output with a sentinel that the
test can observe and that changes nothing it checks (Afterglow uses a title, OSC 2), and wait for that. The terminal
reads in order, so everything before the sentinel has been read.

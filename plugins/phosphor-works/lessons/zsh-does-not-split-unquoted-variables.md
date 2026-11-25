---
id: zsh-does-not-split-unquoted-variables
title: The Bash tool runs zsh, which does not split an unquoted variable into words
repos: [all]
domains: [shell, agents]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`args="-DA=1 -DB=2"; cmake $args` passes one argument in zsh, so a test of three build switches built every app and
looked like a pass. Use an array (`args=(-DA=1 -DB=2); cmake "${args[@]}"`) or run the loop in `bash -c`. The same
applies to `env -i $E command`.

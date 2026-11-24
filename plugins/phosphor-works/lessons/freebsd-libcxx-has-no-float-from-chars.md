---
id: freebsd-libcxx-has-no-float-from-chars
title: FreeBSD 15's libc++ 19 has no float std::from_chars
repos: [phosphor-bots]
domains: [cpp-qt, freebsd]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 fuddlesworth -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

`std::from_chars` for `float` and `double` does not exist in the libc++ 19 of FreeBSD 15, so code that builds on
Linux fails there. Use `std::strtod` for floating-point parsing in phosphor-bots.

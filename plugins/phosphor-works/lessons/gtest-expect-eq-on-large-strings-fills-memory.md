---
id: gtest-expect-eq-on-large-strings-fills-memory
title: A failed EXPECT_EQ on two large strings fills the memory
repos: [all]
domains: [test]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

GoogleTest builds a line diff of two strings that differ. On large strings that diff fills the memory. Compare them
with `EXPECT_TRUE(a == b)`.

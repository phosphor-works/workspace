---
name: lessons
description: "Search the lesson index of the phosphor-works repos: traps that cost earlier sessions time, with the rule that avoids each one. Use before work in an unfamiliar area, when a fix is not working, or when a build, test or tool gives a result you do not trust. Use when: lessons, has this happened before, known traps, search lessons, what did we learn."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Search the lessons

The lessons are Markdown files in the `phosphor-works` plugin's `lessons/` directory, one trap each. A local SQLite
index (sqlite-vec embeddings and FTS5 keywords) finds them by meaning and by exact names. A prompt hook already adds
the closest few to each prompt. Search on demand for more:

```sh
sh <plugin root>/hooks/lessons/lessons.sh search "<what you are doing or seeing>" [--repo <Repo>] [-k 5]
```

`<plugin root>` is two levels above this skill's base directory. In the workspace checkout that is
`workspace/plugins/phosphor-works`.

- Write the query as the situation, with its symbols: "ctest passed but the tests may not be built", "QHash value
  returns what I inserted".
- `--repo` keeps the lessons for that repo and for every repo. Without it, every lesson is a candidate.
- A distance near 0.3 is a close match. Above 0.45 the lesson is probably about something else.

If the command says the index is not installed, run `tools/setup` in the workspace checkout.

To add a lesson, use `phosphor-works:record-lesson`.

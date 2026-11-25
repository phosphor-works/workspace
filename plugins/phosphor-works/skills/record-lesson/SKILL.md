---
name: record-lesson
description: "Record what work in a phosphor-works repo taught, in the place the next session will look for it. Use it after a bug took more than one attempt to find, when the same mistake happened twice, when a debug or verification technique worked, when an audit pass kept re-finding the same shape, or when the user corrects how you work. Use when: remember this, note this for next time, record the lesson, don't let this happen again."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Record a lesson

The next session does not see a lesson that stays only in the chat. Put the lesson where a session will read it.

The skills, agents and guard come from the Claude plugins in the `workspace` repo. Edit them in the `workspace`
checkout beside this repo (`../workspace/plugins/...`), never in the installed copy under `~/.claude/plugins/`, and
commit them there.

| Lesson | Where | Form |
| --- | --- | --- |
| Why code does something that looks wrong (an API rule, a protocol or driver quirk, a Qt or Wayland behaviour, a retry) | A comment at that code | One or two lines that say why, and name the API, spec, protocol or issue |
| A trap that a future change or session could fall into again, in one repo or in every repo | A lesson file in `workspace/plugins/phosphor-works/lessons/` (format below). The lesson index finds it by meaning and adds it to the prompts it fits | A title that states the rule, then the trap, what it cost and the rule, in a few sentences |
| A rule that every repo must always follow, whatever the task | `workspace/claude/conventions.md` | One line in the section it belongs to |
| A step of a procedure that a session missed | The skill that covers it: the app plugin's (`<app>:build`, `<app>:verify-live`, ...) or the shared one (`phosphor-works:code-audit`) | An imperative line with the reason |
| A command that must never run | The guard in `workspace/plugins/phosphor-works/hooks/guard/`: the core for every repo, or `repos/<repo>.py` for one. Add a case to its `test_guard.py` | A rule for the plain command that a session types, with the message to show. No rules for unusual spellings: the guard is not a security boundary. Run `python3 -I test_guard.py` there |
| A past bug shape in one domain | "Known past-bug shapes to check for" in that domain's `<app>:*-reviewer` agent | One bullet: what went wrong, what to check, naming the real symbol |
| A rule that a program can decide by inspection | The repo's conventions check, with a selftest case (PlasmaZones: `scripts/check-conventions.py`) | Only when the shape recurred; see the existing rules for the form |
| A script that worked | The repo's `scripts/` or `tools/` with a usage comment and the SPDX header, or the skill's own directory if only Claude uses it | The scratchpad does not survive the session |
| How the user wants to work | The session memory | With the reason the user gave |

Prove it first. For a rule from one occurrence, write what that occurrence needed, not a general rule. Write the
general rule only when a second case confirms it. Name a symbol or path only after you grep the current tree for it.
When a lesson turns out wrong, correct it. Do not add a second lesson that contradicts it.

CLAUDE.md is long and every session loads it, so a trap does not go there: it goes to the lesson index, which shows
it only when a prompt is about it. A trap that lives in one domain goes to that domain's reviewer (or the app's
`review-notes`), and a step goes to its skill.

## A lesson file

One file per lesson, named after its id, in `workspace/plugins/phosphor-works/lessons/`:

```markdown
---
id: qhash-value-default-is-evaluated-every-call
title: QHash::value(key, f()) evaluates f() on every call
repos: [all]
domains: [cpp-qt]
added: 2026-11-24
---
<!-- SPDX-FileCopyrightText: 2026 Phosphor Works Team -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

The default is an ordinary argument, so if `f` inserts into the same container, the lookup returns what `f` just
wrote. Use `constFind` and resolve only on a miss.
```

- `id`: the file name, lowercase with dashes. `repos`: `[all]`, or the repo names it applies to (`[Afterglow]`).
  `domains`: the review domains or areas (`cpp-qt`, `qml`, `wayland`, `build`, `test`, `ci`, `shader`, `luau`, ...).
- Write the text so that it is found: name the symptom a session would see and the real symbols.
- Check the file with `sh workspace/plugins/phosphor-works/hooks/lessons/lessons.sh check`, then find it with
  `lessons.sh search "<the symptom>"`. The index updates itself from the files.

Commit a lesson in the workspace repo, with the work that found it or alone as `docs(lessons): note ...`.

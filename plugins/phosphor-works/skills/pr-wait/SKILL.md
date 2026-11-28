---
name: pr-wait
description: "Wait for the CI of one or more pull requests, and merge them when every check passes, with workspace/tools/pr-wait. It fails fast on the first failed check and prints its log, stops on a conflict, a draft or a closed PR, never merges a PR that someone else opened, and merges a change set in order. Use when: wait for CI, wait for the checks, watch the PR, merge when green, is CI done, merge the change set, babysit the PRs."
---

<!--
SPDX-FileCopyrightText: 2026 Phosphor Works Team
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Wait for pull requests

Use `workspace/tools/pr-wait` for every wait on CI. Do not write a polling loop, do not `sleep` and check by hand,
and do not use `gh pr checks --watch`. The tool asks GitHub once a minute for each PR, so it stays inside the API
limits, and it always ends with one result for each PR.

## Run it

1. Start it with the Bash tool and `run_in_background: true`. The harness tells you when it exits. Do not poll its
   output while it runs.

   | Goal | Command |
   | --- | --- |
   | Wait for the checks | `../workspace/tools/pr-wait Lambent#26` |
   | Merge when green | `../workspace/tools/pr-wait --merge Lambent#26 PlasmaZones#1330` |
   | Merge a change set | `../workspace/tools/pr-wait --merge --in-order phosphor-libs#80 PlasmaZones#1330 workspace#90` |

2. Read the last line when it exits. It gives the result of each PR.

A PR is `REPO#N` (a phosphor-works repository), `OWNER/REPO#N` or a URL. Give a change set in the order of
`tools/change status`: libraries first, `workspace` last.

## Results

| Result | Exit | What to do |
| --- | --- | --- |
| `passed`, `merged`, `no-checks` | 0 | Continue. `no-checks` means that no check started in 10 minutes (a repository with no CI). |
| `failed` | 1 | Read the failed check and log lines that the tool printed. Fix the root cause and push. Do not re-run a flaky check. |
| `conflict` | 2 | Merge `origin/main` into the branch, resolve, push, and start the tool again. |
| `draft`, `unmergeable` | 2 | Read why. Mark the PR ready (`gh pr ready`) only when it is yours and complete. |
| `not-mine` | 2 | Someone else opened the PR. Do not merge it. |
| `closed`, `stopped` | 2 | `stopped` means that another PR ended badly first, or a PR before it in `--in-order` did not merge. |
| `timeout` | 3 | The checks ran longer than `--timeout` (default 4 h). Look at the run before you wait again. |

The first PR that ends badly stops the wait for all of them. Add `--keep-going` to wait for every PR.

## Change sets

With `--in-order`, the tool merges each PR only after the one before it merged. After a library merges, an app
usually must move its pin before its own PR can merge. In that case, merge the library PRs with one run, move the
pins and push, then run the tool again for the apps and `workspace`.

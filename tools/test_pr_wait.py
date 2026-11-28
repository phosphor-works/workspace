# SPDX-FileCopyrightText: 2026 Phosphor Works Team
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests of tools/pr-wait's parsing and its classification of a pull request.

  python3 -I tools/test_pr_wait.py
"""

import importlib.machinery
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader('pr_wait', os.path.join(HERE, 'pr-wait'))
spec = importlib.util.spec_from_loader('pr_wait', loader)
pw = importlib.util.module_from_spec(spec)
loader.exec_module(pw)


def run(name, status='COMPLETED', conclusion=None):
    return {'__typename': 'CheckRun', 'name': name, 'status': status, 'conclusion': conclusion,
            'detailsUrl': f'https://github.com/o/r/actions/runs/1/job/{len(name)}'}


def pr(state='OPEN', draft=False, mergeable='MERGEABLE'):
    return {'state': state, 'isDraft': draft, 'mergeable': mergeable}


class Parse(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(pw.parse('Lambent#26'), ('phosphor-works', 'Lambent', 26))
        self.assertEqual(pw.parse('phosphor-libs:75'), ('phosphor-works', 'phosphor-libs', 75))
        self.assertEqual(pw.parse('someone/thing#3'), ('someone', 'thing', 3))
        self.assertEqual(pw.parse('https://github.com/phosphor-works/workspace/pull/88'),
                         ('phosphor-works', 'workspace', 88))

    def test_bad(self):
        with self.assertRaises(SystemExit):
            pw.parse('not a pr')


class Checks(unittest.TestCase):
    def test_a_running_check_is_pending(self):
        # GitHub reports a running check with no conclusion: that is not a pass.
        found = pw.checks([run('Build', status='IN_PROGRESS', conclusion=None)])
        self.assertEqual(found[0][1], 'PENDING')

    def test_status_contexts(self):
        found = pw.checks([{'__typename': 'StatusContext', 'context': 'ci/x', 'state': 'EXPECTED', 'targetUrl': ''},
                           {'__typename': 'StatusContext', 'context': 'ci/y', 'state': 'SUCCESS', 'targetUrl': ''}])
        self.assertEqual([s for _, s, _ in found], ['PENDING', 'SUCCESS'])


class Classify(unittest.TestCase):
    def c(self, contexts, merge=False, **state):
        return pw.classify(pr(**state), pw.checks(contexts), merge)

    def test_all_passed(self):
        self.assertEqual(self.c([run('A', conclusion='SUCCESS'), run('B', conclusion='SKIPPED')]), 'passed')

    def test_waits_while_one_runs(self):
        self.assertIsNone(self.c([run('A', conclusion='SUCCESS'), run('B', status='IN_PROGRESS')]))

    def test_fails_at_once_while_others_run(self):
        # One failure decides: the other checks are not waited for.
        self.assertEqual(self.c([run('A', conclusion='FAILURE'), run('B', status='QUEUED')]), 'failed')

    def test_cancelled_and_timed_out_fail(self):
        for conclusion in ('CANCELLED', 'TIMED_OUT', 'ACTION_REQUIRED', 'STARTUP_FAILURE'):
            self.assertEqual(self.c([run('A', conclusion=conclusion)]), 'failed', conclusion)

    def test_no_checks_waits(self):
        self.assertIsNone(self.c([]))

    def test_conflict_before_checks(self):
        self.assertEqual(self.c([run('A', status='IN_PROGRESS')], mergeable='CONFLICTING'), 'conflict')

    def test_closed_and_merged(self):
        self.assertEqual(self.c([], state='CLOSED'), 'closed')
        self.assertEqual(self.c([run('A', conclusion='FAILURE')], state='MERGED'), 'merged')

    def test_draft_only_matters_for_merge(self):
        green = [run('A', conclusion='SUCCESS')]
        self.assertEqual(self.c(green, draft=True), 'passed')
        self.assertEqual(self.c(green, merge=True, draft=True), 'draft')

    def test_never_merges_another_persons_pr(self):
        green = [run('A', conclusion='SUCCESS')]
        theirs = dict(pr(), mine=False)
        self.assertEqual(pw.classify(theirs, pw.checks(green), True), 'not-mine')
        self.assertEqual(pw.classify(theirs, pw.checks(green), False), 'passed')


if __name__ == '__main__':
    unittest.main()

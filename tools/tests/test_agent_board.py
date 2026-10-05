"""Agent task board: header validation, rendering order and committed-board freshness."""

from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS / 'agents'))
import board  # noqa: E402

HEADER = """---
id: T-0042
title: Example
status: {status}
priority: P2
owner: claude-opus-5-5
reviewers: claude-sonnet-5-5, gpt-6.1-sol
orchestrator: gpt-6-astra
branch: codex/t0042-example-opus
base: abc1234
candidate: {candidate}
claim: none
lease: none
updated: 2026-10-04
---

## Log

### 2026-10-04T21:40-07:00 · gpt-6-astra → claude-opus-5-5 · DISPATCH
go
### 2026-10-04T22:10-07:00 · claude-opus-5-5 → gpt-6-astra · HANDBACK
done
"""


def write_task(directory, name='T-0042-example.md', status='in-progress', candidate='none'):
    path = Path(directory) / name
    path.write_text(HEADER.format(status=status, candidate=candidate), encoding='utf-8')
    return path


class BoardTest(unittest.TestCase):
    def test_review_without_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            write_task(directory, status='review', candidate='none')
            _, errors = board.load_tasks(Path(directory))
        self.assertTrue(any('requires a candidate' in error for error in errors), errors)

    def test_non_sha_candidate_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            write_task(directory, status='review', candidate='latest-fix')
            _, errors = board.load_tasks(Path(directory))
        self.assertTrue(any("candidate 'latest-fix'" in error for error in errors), errors)

    def test_unknown_status_and_mismatched_filename_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            write_task(directory, name='T-0043-wrong.md', status='done')
            _, errors = board.load_tasks(Path(directory))
        self.assertTrue(any("status='done'" in error for error in errors), errors)
        self.assertTrue(any('filename does not start with T-0042-' in error for error in errors), errors)

    def test_review_task_needs_attention_with_latest_message(self):
        with tempfile.TemporaryDirectory() as directory:
            write_task(directory, status='review', candidate='def5678')
            tasks, errors = board.load_tasks(Path(directory))
        self.assertEqual(errors, [])
        attention = board.render(tasks).split('## Active')[0]
        self.assertIn('**T-0042** `review`', attention)
        self.assertIn('HANDBACK by claude-opus-5-5', attention)

    def test_committed_board_is_valid_and_current(self):
        self.assertEqual(board.main(['--check']), 0)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Block until a new task-log message addressed to an agent appears, then print it.

Usage: wait_message.py --to claude-opus-5-5 [--timeout 3600] [--poll 5] [--watch]
Messages already present at start are ignored. Exit 0 = message printed,
2 = timeout. --watch keeps running and prints each new message (for monitors).
Reads docs/agents/tasks/*.md only; never writes. Standard library only.
"""

import argparse
from pathlib import Path
import re
import sys
import time

TASKS = Path(__file__).resolve().parents[2] / 'docs' / 'agents' / 'tasks'
HEADING = re.compile(r'^### (\S+) · (\S+) → (\S+) · ([A-Z-]+)\s*$')


def messages(task_dir=TASKS):
    """Yield (file, heading, body, recipient) for every log entry."""
    for path in sorted(task_dir.glob('T-*.md')):
        current = None
        for line in path.read_text(encoding='utf-8').splitlines() + ['### end']:
            match = HEADING.match(line)
            if match or line == '### end':
                if current:
                    yield current[0], current[1], '\n'.join(current[3]).strip(), current[2]
                current = (path.name, line, match.group(3), []) if match else None
            elif current and not line.startswith('<!--'):
                current[3].append(line)


def addressed(recipient, task_dir=TASKS):
    return {(f, h): (b, r) for f, h, b, r in messages(task_dir) if r in (recipient, 'all')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--to', required=True, help='exact model id, or user')
    parser.add_argument('--timeout', type=float, default=3600)
    parser.add_argument('--poll', type=float, default=5)
    parser.add_argument('--watch', action='store_true')
    args = parser.parse_args(argv)
    seen = set(addressed(args.to))
    deadline = time.monotonic() + args.timeout
    while args.watch or time.monotonic() < deadline:
        time.sleep(args.poll)
        try:
            current = addressed(args.to)
        except (OSError, UnicodeDecodeError):
            continue  # file mid-write; retry next poll
        new = [key for key in current if key not in seen]
        for name, heading in new:
            print(f'[{name}] {heading}\n{current[(name, heading)][0]}\n', flush=True)
        seen.update(new)
        if new and not args.watch:
            return 0
    print(f'timeout: no new message for {args.to}', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())

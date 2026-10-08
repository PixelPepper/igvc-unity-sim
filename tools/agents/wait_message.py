#!/usr/bin/env python3
"""Block until a task-log message addressed to an agent appears, then print it.

Usage: wait_message.py --to claude-opus-5-5 [--timeout 3600] [--poll 5] [--watch]
                       [--cursor PATH]
Without --cursor, messages already present at start are ignored (legacy mode).
With --cursor, delivered message IDs (file name + heading) persist in a versioned
JSON cursor bound to the recipient and resolved task directory: a missing cursor
replays every addressed message, and an existing one immediately prints entries
posted while no listener ran. Delivery is at-least-once, never exactly-once.
Exit 0 = message printed, 2 = timeout, 1 = error. --watch keeps running and prints
each new message (for monitors). Reads docs/agents/tasks/*.md only; writes only the
selected cursor, its .lock and temporary files. Printing never starts or wakes an
agent and does not prove receipt. See docs/AGENT_LISTENER.md. Standard library only.
"""

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import time

TASKS = Path(__file__).resolve().parents[2] / 'docs' / 'agents' / 'tasks'
HEADING = re.compile(r'^### (\S+) · (\S+) → (\S+) · ([A-Z-]+)\s*$')
CURSOR_VERSION = 1
CURSOR_KEYS = {'version', 'recipient', 'tasks', 'delivered'}


class ListenerError(Exception):
    """A clear, non-recoverable listener failure (exit 1)."""


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


def positive_seconds(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError(f'must be a finite positive number: {text}')
    return value


class CursorLock:
    """Process-held exclusive lock on PATH.lock; the lock file itself is kept."""

    def __init__(self, cursor):
        self.path = Path(str(cursor) + '.lock')
        self.handle = None

    def __enter__(self):
        try:
            self.handle = open(self.path, 'a+b')
        except OSError as exc:
            raise ListenerError(f'cannot open cursor lock {self.path}: {exc}') from exc
        try:
            if os.name == 'nt':
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise ListenerError(
                f'cursor {self.path} is locked by another listener; '
                'use a distinct --cursor per consumer') from exc
        return self

    def __exit__(self, *exc):
        if self.handle is None:
            return
        try:
            if os.name == 'nt':
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass  # closing the handle releases the lock regardless
        finally:
            self.handle.close()
            self.handle = None


def load_cursor(path, recipient, task_dir):
    """Return the delivered ID set, or None if the cursor does not exist yet."""
    try:
        text = Path(path).read_text(encoding='utf-8')
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as exc:
        raise ListenerError(f'cannot read cursor {path}: {exc}') from exc
    try:
        state = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ListenerError(f'corrupt cursor {path}: {exc}; not resetting') from exc
    if not isinstance(state, dict) or set(state) != CURSOR_KEYS:
        raise ListenerError(f'corrupt cursor {path}: expected keys {sorted(CURSOR_KEYS)}')
    if type(state['version']) is not int or state['version'] != CURSOR_VERSION:
        raise ListenerError(f'unsupported cursor version in {path}: {state["version"]!r}')
    if state['recipient'] != recipient or state['tasks'] != str(task_dir):
        raise ListenerError(
            f'cursor {path} belongs to recipient {state["recipient"]!r} and tasks '
            f'{state["tasks"]!r}, not {recipient!r} and {str(task_dir)!r}')
    delivered = state['delivered']
    if not isinstance(delivered, list) or not all(
            isinstance(item, list) and len(item) == 2
            and all(isinstance(part, str) for part in item) for item in delivered):
        raise ListenerError(f'corrupt cursor {path}: delivered must be [file, heading] pairs')
    return {tuple(item) for item in delivered}


def save_cursor(path, recipient, task_dir, delivered):
    """Atomically replace the cursor; on failure the previous cursor is untouched."""
    path = Path(path)
    state = {'version': CURSOR_VERSION, 'recipient': recipient, 'tasks': str(task_dir),
             'delivered': [list(item) for item in sorted(delivered)]}
    temp = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    try:
        with open(temp, 'w', encoding='utf-8') as handle:
            json.dump(state, handle, indent=1, ensure_ascii=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink()
        except OSError:
            pass
        raise ListenerError(f'cannot save cursor {path}: {exc}; '
                            'printed entries will be delivered again') from exc


def emit(out, keys, current):
    """Print and flush entries; any output failure aborts before persisting."""
    try:
        for name, heading in keys:
            print(f'[{name}] {heading}\n{current[(name, heading)][0]}\n', file=out)
        out.flush()
    except (OSError, ValueError) as exc:
        raise ListenerError(f'cannot write messages to output: {exc}') from exc


def legacy(args, out, clock, sleep):
    seen = set(addressed(args.to, args.tasks))
    deadline = clock() + args.timeout
    while args.watch or clock() < deadline:
        sleep(args.poll)
        try:
            current = addressed(args.to, args.tasks)
        except (OSError, UnicodeDecodeError):
            continue  # file mid-write; retry next poll
        new = [key for key in current if key not in seen]
        emit(out, new, current)
        seen.update(new)
        if new and not args.watch:
            return 0
    print(f'timeout: no new message for {args.to}', file=sys.stderr)
    return 2


def durable(args, out, clock, sleep):
    with CursorLock(args.cursor):
        delivered = load_cursor(args.cursor, args.to, args.tasks)
        if delivered is None:
            delivered = set()
            save_cursor(args.cursor, args.to, args.tasks, delivered)
        deadline = clock() + args.timeout
        while True:
            try:
                current = addressed(args.to, args.tasks)
            except (OSError, UnicodeDecodeError):
                current = None  # file mid-write; retry next poll
            if current is not None:
                new = [key for key in current if key not in delivered]
                if new:
                    emit(out, new, current)  # flushed before persisting
                    save_cursor(args.cursor, args.to, args.tasks, delivered | set(new))
                    delivered |= set(new)
                    if not args.watch:
                        return 0
            remaining = deadline - clock()
            if not args.watch and remaining <= 0:
                break
            sleep(args.poll if args.watch else min(args.poll, remaining))
    print(f'timeout: no new message for {args.to}', file=sys.stderr)
    return 2


def main(argv=None, out=None, clock=time.monotonic, sleep=time.sleep):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--to', required=True, help='exact model id, or user')
    parser.add_argument('--timeout', type=positive_seconds, default=3600)
    parser.add_argument('--poll', type=positive_seconds, default=5)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--cursor', type=Path, help='opt-in durable delivery state file')
    parser.add_argument('--tasks', type=Path, default=TASKS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    args.tasks = args.tasks.resolve()
    out = sys.stdout if out is None else out
    try:
        return durable(args, out, clock, sleep) if args.cursor else legacy(args, out, clock, sleep)
    except ListenerError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

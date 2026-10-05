#!/usr/bin/env bash
# Snapshot the primary working tree (tracked + untracked, respecting .gitignore)
# into a local branch WITHOUT touching the real index, files or current branch.
# Usage: snapshot.sh [--create <branch>] [--allow-large] [--message <text>]
# Default is a dry run that lists what would differ from HEAD.
set -euo pipefail

branch="" allow_large=0 message="Snapshot working tree for agent tasks"
while [ $# -gt 0 ]; do
  case "$1" in
    --create) branch="${2:?--create needs a branch name}"; shift 2 ;;
    --allow-large) allow_large=1; shift ;;
    --message) message="${2:?--message needs text}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

root="$(git rev-parse --show-toplevel)"
cd "$root"
tmp_index="$(mktemp)"
trap 'rm -f "$tmp_index"' EXIT
cp "$(git rev-parse --git-path index)" "$tmp_index"
GIT_INDEX_FILE="$tmp_index" git add -A
tree="$(GIT_INDEX_FILE="$tmp_index" git write-tree)"

echo "Changes relative to HEAD $(git rev-parse --short HEAD):"
git diff-tree -r --no-commit-id --name-status HEAD "$tree"
git diff-tree -r --no-commit-id --shortstat HEAD "$tree" | sed 's/^/total:/'

# Refuse unexpectedly large new/changed blobs (builds, bags, CAD) by default.
large=""
while IFS=$'\t' read -r meta path; do
  # meta = ":<old mode> <new mode> <old blob> <new blob> <status>"
  read -r _ _ _ blob status <<< "$meta"
  [ "$status" = D ] && continue
  size="$(git cat-file -s "$blob")"
  [ "$size" -gt 5242880 ] && large+="$size"$'\t'"$path"$'\n'
done < <(git diff-tree -r --no-commit-id HEAD "$tree")
if [ -n "$large" ]; then
  echo "Files over 5 MB:"; echo "$large"
  [ "$allow_large" -eq 1 ] || { echo "refusing; fix .gitignore or pass --allow-large" >&2; exit 1; }
fi

if [ -z "$branch" ]; then
  echo "dry run: no commit created (use --create <branch>)"
  exit 0
fi
if git show-ref --verify --quiet "refs/heads/$branch"; then
  echo "branch already exists: $branch" >&2; exit 1
fi
commit="$(git commit-tree "$tree" -p HEAD -m "$message")"
git branch "$branch" "$commit"
echo "created $branch at $commit"

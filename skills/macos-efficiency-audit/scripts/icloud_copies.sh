#!/usr/bin/env bash
# iCloud conflict copies: "Name 2.ext" (or " 3", up to " 9") sitting next to "Name.ext".
#
#   icloud_copies.sh DIR                 list them, say which are byte-identical to the original
#   icloud_copies.sh DIR --trash         move the identical ones to the Trash (via trash.sh)
#   icloud_copies.sh DIR --exclude SUB   skip a subfolder (repeatable); .git is always skipped
#
# iCloud Drive makes these when two writers race (a sync and a git checkout, two
# devices, an editor and a script). A copy identical to its original carries nothing;
# a copy that differs is an edit nobody merged and is only reported. The rule is
# strict on purpose: the stem must end in " N", the original must exist, and the
# bytes must match, so "Chapter 2.md" or "Screenshot at 9.55.07.png" are never touched.
set -u
DIR=""; TRASH=0; EXCL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --trash) TRASH=1 ;;
    --exclude) EXCL+=("$2"); shift ;;
    *) DIR="$1" ;;
  esac
  shift
done
[[ -n "$DIR" && -d "$DIR" ]] || { sed -n '2,10p' "$0"; exit 2; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
prune=( -path "$DIR/.git" )
for e in ${EXCL[@]+"${EXCL[@]}"}; do prune+=( -o -path "$DIR/$e" ); done

identical=(); differing=0
while IFS= read -r -d '' dup; do
  base=${dup##*/}; stem=${base%.*}; ext=${base##*.}
  case "$stem" in *" "[2-9]) ;; *) continue ;; esac
  orig="${dup%/*}/${stem% [2-9]}.$ext"
  [[ "$orig" != "$dup" && -f "$orig" ]] || continue
  if cmp -s "$dup" "$orig"; then
    echo "identical  $dup"; identical+=("$dup")
  else
    echo "DIFFERS    $dup   (left alone: it holds edits the original lacks)"; differing=$((differing+1))
  fi
done < <(find "$DIR" \( "${prune[@]}" \) -prune -o -type f -name '* [2-9].*' -print0 2>/dev/null)

echo
echo "identical copies: ${#identical[@]}, differing: $differing"
if [[ $TRASH -eq 1 && ${#identical[@]} -gt 0 ]]; then
  "$HERE/trash.sh" -- "${identical[@]}"
fi

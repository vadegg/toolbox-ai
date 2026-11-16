#!/usr/bin/env bash
# Which running processes hold files under each path. Read-only.
#
#   holders.sh PATH...        one line per path: "held by: none" or the process names
#
# A cache a running app holds open is not safe to move: the app keeps writing into
# the Trash. Run this on every cache or updater folder before it goes into a "safe"
# list, and quote the answer in the report. `lsof +D` walks the whole tree, so a
# folder with a hundred thousand files takes a while; caches rarely do.
set -u
[[ $# -gt 0 ]] || { sed -n '2,10p' "$0"; exit 2; }
for p in "$@"; do
  if [[ ! -e "$p" ]]; then echo "missing            $p"; continue; fi
  holders=$(lsof -n +D "$p" 2>/dev/null | awk 'NR>1 {print $1}' | sort | uniq -c | sort -rn | awk '{printf "%s(%s) ", $2, $1}')
  if [[ -z "$holders" ]]; then echo "held by: none      $p"; else echo "held by: $holders $p"; fi
done

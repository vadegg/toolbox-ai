#!/bin/bash
# Re-injects an orchestrator chat's own prompt. Installed once, as global Claude Code hooks:
#   SessionStart (matcher compact|resume)  inject-prompt.sh full
#   UserPromptSubmit                        inject-prompt.sh changed
# Walks up from the session's cwd to the nearest orchestrator/session-id and acts only when
# that file names this session, so every other session gets no output.
#   full     print PROMPT.md and snapshot the watched files
#   changed  report any watched file edited since its snapshot: in full up to 8 000 bytes,
#            as a diff above that, because hook output over ~10 KB reaches the session only
#            as a preview
input=$(cat)
read -r cwd cli_id < <(python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
print(d.get("cwd") or ".", d.get("session_id") or "-")' <<<"$input")

# Desktop app: the host id survives restarts. CLI: the session id from the hook input.
ids=("${CLAUDE_CODE_HOST_SESSION_ID:-}" "$cli_id")

dir=""
d=$(cd "$cwd" 2>/dev/null && pwd -P) || exit 0
while [ -n "$d" ] && [ "$d" != / ]; do
  if [ -f "$d/orchestrator/session-id" ]; then dir="$d/orchestrator"; break; fi
  d=$(dirname "$d")
done
[ -n "$dir" ] || exit 0
bound=$(tr -d '[:space:]' <"$dir/session-id")
[ -n "$bound" ] || exit 0
match=""
for id in "${ids[@]}"; do
  [ -n "$id" ] && [ "$id" != - ] || continue
  [ "$id" = "$bound" ] || [ "local_$id" = "$bound" ] || [ "$id" = "local_$bound" ] && match=1
done
[ -n "$match" ] || exit 0

root=$(dirname "$dir")
watched=("$dir/PROMPT.md")
if [ -f "$dir/watch" ]; then
  while IFS= read -r line; do
    line="${line%%#*}"; line="${line%"${line##*[![:space:]]}"}"
    [ -n "$line" ] && watched+=("${line/#\~/$HOME}")
  done <"$dir/watch"
else
  watched+=("$HOME/.claude/CLAUDE.md" "$HOME/.claude/AGENTS.md" "$root/CLAUDE.md" "$root/AGENTS.md")
fi

state="$dir/.state"
mkdir -p "$state"
max_full=8000
seen=" "

for f in "${watched[@]}"; do
  [ -f "$f" ] || continue
  real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$f")
  case "$seen" in *" $real "*) continue ;; esac
  seen="$seen$real "
  snap="$state/$(echo "$real" | shasum | cut -c1-12).snap"
  if [ "$1" = full ]; then
    # Compaction and resume re-read CLAUDE.md/AGENTS.md themselves; only PROMPT.md needs injecting.
    if [ "$f" = "$dir/PROMPT.md" ]; then
      echo "<reloaded_instructions source=\"$f\">"; cat "$f"; echo "</reloaded_instructions>"
    fi
  elif ! cmp -s "$f" "$snap"; then
    if [ "$(wc -c <"$f")" -le "$max_full" ] || [ ! -f "$snap" ]; then
      echo "<reloaded_instructions source=\"$f\">"; cat "$f"; echo "</reloaded_instructions>"
    else
      echo "<changed_instructions source=\"$f\" note=\"diff against the previous version; the rest is unchanged\">"
      diff -u "$snap" "$f" | tail -n +3
      echo "</changed_instructions>"
    fi
  fi
  cp "$f" "$snap"
done
exit 0

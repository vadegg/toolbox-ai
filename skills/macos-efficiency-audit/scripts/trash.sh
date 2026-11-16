#!/usr/bin/env bash
# Move files and folders to the Trash instead of deleting them.
#
#   trash.sh [--dry-run] [--log FILE] PATH...
#   trash.sh [--dry-run] [--log FILE] --from LIST      one path per line; "-" reads stdin
#
# A move inside the same volume is instant and reversible: the person empties the
# Trash when they are satisfied, and until then nothing is lost. Root-owned paths are
# not moved (a root-owned item in the user's Trash cannot be emptied without a
# password prompt); they are listed at the end as a command for the user to run.
# Paths that must never be trashed by a cleanup script are refused outright.
set -u
TRASH="${TRASH_DIR:-$HOME/.Trash}"
DRY=0; LOG=""; FROM=""; paths=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --log) LOG="$2"; shift ;;
    --from) FROM="$2"; shift ;;
    --) shift; paths+=("$@"); break ;;
    *) paths+=("$1") ;;
  esac
  shift
done
if [[ -n "$FROM" ]]; then
  if [[ "$FROM" == "-" ]]; then while IFS= read -r l; do [[ -n "$l" ]] && paths+=("$l"); done
  else while IFS= read -r l; do [[ -n "$l" ]] && paths+=("$l"); done < "$FROM"; fi
fi
[[ ${#paths[@]} -gt 0 ]] || { sed -n '2,12p' "$0"; exit 2; }
mkdir -p "$TRASH"

refused() {   # paths a cleanup must never touch, however the list was produced
  local p="$1"
  case "$p" in
    /|/System|/System/*|/usr|/usr/*|/bin|/bin/*|/sbin|/sbin/*|/etc|/etc/*|/private/etc|/private/etc/*|/private|/var|/private/var|/private/var/db|/private/var/db/*|/Library|/Applications|/Users|"$HOME"|"$HOME/") return 0 ;;
    "$HOME/Library"|"$HOME/Library/Keychains"*|"$HOME/Library/Mail"*|"$HOME/Library/Messages"*|"$HOME/Library/Photos"*|*.photoslibrary|*.photoslibrary/*) return 0 ;;
    "$HOME/Documents"|"$HOME/Desktop"|"$HOME/Downloads"|"$HOME/Pictures"|"$HOME/Movies"|"$HOME/Music"|"$HOME/Library/Mobile Documents"|"$HOME/Library/Mobile Documents/"*) return 0 ;;
  esac
  return 1
}

stamp=$(date +%Y%m%d-%H%M); moved=0; failed=0; skipped=0; total_kb=0; sudo_list=()
me=$(id -un)
for src in "${paths[@]}"; do
  src="${src%/}"
  if [[ ! -e "$src" && ! -L "$src" ]]; then echo "SKIP  missing      $src"; skipped=$((skipped+1)); continue; fi
  if refused "$src"; then echo "REFUSE protected    $src"; skipped=$((skipped+1)); continue; fi
  owner=$(stat -f '%Su' "$src" 2>/dev/null)
  if [[ "$owner" != "$me" ]]; then echo "SKIP  owned by $owner  $src"; sudo_list+=("$src"); skipped=$((skipped+1)); continue; fi
  kb=$(du -sk "$src" 2>/dev/null | cut -f1); kb=${kb:-0}
  base=$(basename "$src"); dest="$TRASH/$base"; n=0
  while [[ -e "$dest" ]]; do n=$((n+1)); dest="$TRASH/$base (trashed $stamp-$n)"; done
  if [[ $DRY -eq 1 ]]; then
    printf 'WOULD %8.1f MiB  %s\n' "$(awk -v k="$kb" 'BEGIN{print k/1024}')" "$src"; total_kb=$((total_kb+kb)); continue
  fi
  if mv "$src" "$dest" 2>/dev/null; then
    printf 'OK    %8.1f MiB  %s\n' "$(awk -v k="$kb" 'BEGIN{print k/1024}')" "$src"; moved=$((moved+1)); total_kb=$((total_kb+kb))
    [[ -n "$LOG" ]] && printf '%s\t%s\t%s\t%s\n' "$(date '+%F %T')" "$kb" "$src" "$dest" >> "$LOG"
  else
    echo "FAIL               $src"; failed=$((failed+1))
  fi
done
echo
if [[ $DRY -eq 1 ]]; then
  echo "dry run: $(awk -v k="$total_kb" 'BEGIN{printf "%.2f GiB", k/1048576}') would move to $TRASH; nothing changed"
else
  echo "moved $moved item(s), $(awk -v k="$total_kb" 'BEGIN{printf "%.2f GiB", k/1048576}'), to $TRASH; failed $failed, skipped $skipped"
fi
if [[ ${#sudo_list[@]} -gt 0 ]]; then
  echo
  echo "Root-owned items were left alone. If the person wants them gone, they run (permanent, so they decide):"
  printf '  sudo rm -rf'; printf ' %q' "${sudo_list[@]}"; printf '\n'
fi

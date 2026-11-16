#!/usr/bin/env bash
# Where the disk space went. Read-only.
#
#   disk_report.sh                      full map (3-10 min on a large home folder)
#   disk_report.sh --quick              skip the slow parts: large-file search, dependency folders
#   disk_report.sh --top 25             rows per table (default 20)
#   disk_report.sh --archive-dirs "a:b" folders of retired projects to scan for node_modules/.venv
#                                       (default: every directory named archive, Archive or old
#                                       up to three levels below the home folder)
#
# Sizes are what `du -x` reports, in binary gigabytes (GiB, 1024^3) with two decimals;
# Finder shows decimal GB, about 7% larger. Everything is measured, nothing is changed.
set -u
shopt -s nullglob
TOP=20; QUICK=0; ARCHIVES=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick) QUICK=1 ;;
    --top) TOP="$2"; shift ;;
    --archive-dirs) ARCHIVES="$2"; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

section() { printf '\n## %s\n' "$1"; }
fmt='{s=$1; $1=""; sub(/^ /,""); printf "  %8.2f GiB  %s\n", s/1048576, $0}'
du_top() {               # du_top N path...   (missing paths are simply skipped)
  local n="$1"; shift
  [[ $# -gt 0 ]] || { echo "  (nothing found)"; return; }
  du -xsk "$@" 2>/dev/null | sort -rn | awk '$1 >= 1024' | head -n "$n" | awk "$fmt"
}
total_kb() { du -xsk "$@" 2>/dev/null | awk '{s+=$1} END{print s+0}'; }

section "Home folder, top level"
du_top "$TOP" "$HOME"/* "$HOME"/.[!.]*

section "~/Library, top level"
du_top "$TOP" "$HOME"/Library/*

section "~/Library/Caches"
du_top 15 "$HOME"/Library/Caches/*

section "~/Library/Application Support"
du_top 15 "$HOME"/Library/Application\ Support/*

section "~/Library/Containers and Group Containers"
du_top 12 "$HOME"/Library/Containers/* "$HOME"/Library/Group\ Containers/*

section "Developer and tool caches"
du_top 40 \
  "$HOME"/.npm "$HOME"/.cache/* "$HOME"/.ollama "$HOME"/.colima "$HOME"/.lima "$HOME"/.docker \
  "$HOME"/Library/Caches/pip "$HOME"/Library/Caches/Homebrew "$HOME"/Library/Caches/ms-playwright \
  "$HOME"/.cargo "$HOME"/.rustup "$HOME"/.gradle "$HOME"/.m2 "$HOME"/.pyenv "$HOME"/.nvm "$HOME"/.bun \
  "$HOME"/go "$HOME"/.local/share/* "$HOME"/.cursor "$HOME"/.vscode "$HOME"/.claude "$HOME"/.codex \
  "$HOME"/.gemini "$HOME"/Library/pnpm "$HOME"/Library/Android "$HOME"/.android \
  "$HOME"/Library/Developer/Xcode/DerivedData "$HOME"/Library/Developer/Xcode/iOS\ DeviceSupport \
  "$HOME"/Library/Developer/Xcode/Archives "$HOME"/Library/Developer/CoreSimulator
if command -v docker >/dev/null 2>&1; then
  docker system df 2>/dev/null | sed 's/^/  docker: /' | head -5 || true
fi
if [[ -d "$HOME/.ollama/models/manifests" ]]; then
  echo "  ollama models: $(find "$HOME/.ollama/models/manifests" -type f 2>/dev/null | sed -E 's#.*/manifests/[^/]+/(library/)?##' | tr '\n' ' ')"
fi
if command -v brew >/dev/null 2>&1; then
  echo "  brew cleanup --prune=all would free: $(brew cleanup -n --prune=all 2>/dev/null | grep -o 'approximately .*' | tail -1)"
fi

section "Cloud and media libraries (personal folders as totals; the report keeps it that way)"
du_top 15 \
  "$HOME"/Library/Mobile\ Documents/* "$HOME"/Library/CloudStorage/* "$HOME"/Library/Mail \
  "$HOME"/Library/Messages "$HOME"/Pictures/*.photoslibrary "$HOME"/Library/Photos/Libraries/* \
  "$HOME"/Music/* "$HOME"/Movies "$HOME"/Movies/*.imovielibrary "$HOME"/Movies/*.fcpbundle \
  "$HOME"/Library/Containers/com.apple.BKAgentService "$HOME"/Library/News
for d in "$HOME"/Movies "$HOME"/Pictures "$HOME"/Documents "$HOME"/Downloads "$HOME"/Desktop; do
  [[ -d "$d" ]] || continue
  echo "  $(basename "$d"): $(find "$d" -type f -not -name '.DS_Store' 2>/dev/null | wc -l | tr -d ' ') files, $(find "$d" -type f -size +1G 2>/dev/null | wc -l | tr -d ' ') of them over 1 GiB"
done

section "Updater leftovers (downloaded updates waiting or forgotten; 'held by' = a process still uses it)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
upd=$(find "$HOME/Library/Caches" -maxdepth 2 -type d \
  \( -iname '*ShipIt*' -o -iname '*updater*' -o -name 'org.sparkle-project.Sparkle' -o -name 'pending' \) 2>/dev/null)
if [[ -n "$upd" ]]; then
  echo "$upd" | tr '\n' '\0' | xargs -0 du -xsk 2>/dev/null | sort -rn | awk '$1 >= 1024' | head -n 15 | while IFS=$'\t' read -r kb path; do
    printf '  %8.2f GiB  %s  [%s]\n' "$(awk -v k="$kb" 'BEGIN{print k/1048576}')" "$path" "$("$HERE/holders.sh" "$path" | sed -E 's/ +\/.*$//')"
  done
fi

section "Browser caches and on-device models (Service Worker storage is site data, not cache)"
du_top 12 "$HOME"/Library/Caches/Google/Chrome "$HOME"/Library/Caches/com.google.Chrome* \
  "$HOME"/Library/Caches/Firefox "$HOME"/Library/Caches/BraveSoftware "$HOME"/Library/Caches/Arc \
  "$HOME"/Library/Caches/com.microsoft.edgemac "$HOME"/Library/Caches/com.vivaldi.Vivaldi \
  "$HOME"/Library/Application\ Support/Google/Chrome/OptGuideOnDeviceModel \
  "$HOME"/Library/Application\ Support/Google/Chrome/*/Service\ Worker/CacheStorage
for b in "Google Chrome" Firefox Brave\ Browser Arc Microsoft\ Edge Vivaldi Safari; do pgrep -x "$b" >/dev/null 2>&1 && echo "  running now: $b (its caches are in use; quit it before touching them)"; done

for prof in "$HOME"/Library/Application\ Support/Google/Chrome/Default "$HOME"/Library/Application\ Support/Google/Chrome/Profile\ *; do
  [[ -d "$prof/Extensions" ]] && echo "  Chrome extensions in $(basename "$prof"): $(ls "$prof/Extensions" 2>/dev/null | wc -l | tr -d ' ')"
done

section "Trash (emptying it is permanent: the five biggest items, so the person can look first)"
du_top 1 "$HOME"/.Trash
echo "  items: $(ls -A "$HOME/.Trash" 2>/dev/null | wc -l | tr -d ' ')"
du_top 5 "$HOME"/.Trash/* "$HOME"/.Trash/.[!.]*

section "Applications by last use (oldest first; 'never' = no launch recorded by Spotlight)"
for a in /Applications/*.app /Applications/*/*.app "$HOME"/Applications/*.app "$HOME"/Applications/*/*.app; do
  d=$(mdls -name kMDItemLastUsedDate -raw "$a" 2>/dev/null); [[ "$d" == "(null)" || -z "$d" ]] && d="never"
  printf '%s\t%s\t%s\n' "$d" "$(du -sk "$a" 2>/dev/null | cut -f1)" "$a"
done | sort | awk -F'\t' '{printf "  %-20s %7.2f GiB  %s\n", substr($1,1,10), $2/1048576, $3}' | head -n "$TOP"

if [[ $QUICK -eq 0 ]]; then
  section "Files over 1 GiB (outside iCloud, cloud mounts, the Trash and photo libraries)"
  find "$HOME" -xdev -type f -size +1G \
    -not -path "*/Library/Mobile Documents/*" -not -path "*/Library/CloudStorage/*" \
    -not -path "*/.Trash/*" -not -path "*.photoslibrary/*" -print0 2>/dev/null \
    | xargs -0 du -k 2>/dev/null | sort -rn | head -n "$TOP" | awk "$fmt"

  section "Dependency folders inside retired projects (node_modules, .venv, venv)"
  if [[ -z "$ARCHIVES" ]]; then
    ARCHIVES=$(find "$HOME" -maxdepth 3 -type d \( -iname archive -o -iname old \) -not -path "*/Library/*" -not -path "*/.*" 2>/dev/null | tr '\n' ':')
  fi
  IFS=':' read -r -a dirs <<< "$ARCHIVES"
  existing=()
  for d in "${dirs[@]}"; do [[ -n "$d" && -d "$d" ]] && existing+=("$d"); done
  if [[ ${#existing[@]} -eq 0 ]]; then
    echo "  (no archive folders found; pass --archive-dirs)"
  else
    echo "  scanned: ${existing[*]}"
    find "${existing[@]}" -xdev -type d \( -name node_modules -o -name .venv -o -name venv \) -prune -print0 2>/dev/null \
      | xargs -0 du -sk 2>/dev/null | sort -rn | awk -v top="$TOP" 'NR<=top {s=$1; $1=""; sub(/^ /,""); printf "  %8.2f GiB  %s\n", s/1048576, $0} {t+=$1; n++} END {printf "  total: %.2f GiB in %d folders\n", t/1048576, n}'
  fi
fi

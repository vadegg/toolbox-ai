#!/usr/bin/env bash
# System snapshot for the macOS efficiency audit. Read-only: nothing here changes state.
#
#   snapshot.sh                 hardware, memory, disk, power, security, backups, stability
#   snapshot.sh --with-updates  also ask Software Update (adds 30-60 s)
#
# Sections start with "## ". Numbers are rounded for a human reader; rerun a single
# command when you need the exact figure.
set -u
shopt -s nullglob
WITH_UPDATES=0
[[ "${1:-}" == "--with-updates" ]] && WITH_UPDATES=1

section() { printf '\n## %s\n' "$1"; }
gb() { awk -v k="${1:-0}" 'BEGIN{printf "%.1f GiB", k/1048576}'; }

section "Hardware and OS"
sw_vers 2>/dev/null | sed 's/^/  /'
system_profiler SPHardwareDataType 2>/dev/null \
  | grep -E 'Model Name|Model Identifier|Chip|Total Number of Cores|Memory:' | sed 's/^ */  /'
echo "  Uptime: $(uptime | sed -E 's/.*up +//; s/, [0-9]+ users?.*load averages?: / | load /')"
echo "  Last reboot: $(last reboot 2>/dev/null | head -1 | awk '{print $3, $4, $5, $6}')"
system_profiler SPDisplaysDataType 2>/dev/null \
  | grep -E 'Display Type|Resolution|UI Looks like' | sed 's/^ */  /'

section "Memory and swap"
top -l 1 -n 0 2>/dev/null | grep 'PhysMem' | sed 's/^/  /'
echo "  Swap: $(sysctl -n vm.swapusage)"
vm_stat 2>/dev/null | awk '
  /page size of/            { ps = $8 }
  /Pages stored in compressor/   { c = $5; gsub(/\./, "", c) }
  /Pages occupied by compressor/ { o = $5; gsub(/\./, "", o) }
  END { if (ps > 0) printf "  Compressor: %.1f GiB of data squeezed into %.1f GiB of RAM\n", c*ps/1073741824, o*ps/1073741824 }'

section "Disk"
df -h /System/Volumes/Data 2>/dev/null | awk 'NR==2 {print "  Data volume: size " $2 ", used " $3 ", free " $4 " (" $5 " used)"}'
diskutil apfs list 2>/dev/null | awk '/Capacity Not Allocated/ {gsub(/[()]/, ""); print "  APFS container free: " $6 " " $7; exit}'
echo "  Trash: $(gb "$(du -sk "$HOME/.Trash" 2>/dev/null | cut -f1)")"
system_profiler SPStorageDataType 2>/dev/null | grep -m1 'S.M.A.R.T' | sed 's/^ */  /'
hdiutil info 2>/dev/null | awk '/image-path/ {sub(/^[^:]*: */, ""); print "  Mounted disk image: " $0}'
writes=$(ls /Library/Logs/DiagnosticReports 2>/dev/null | grep -c -E '^disk writes')
if [[ "$writes" -gt 0 ]]; then
  echo "  Heavy-disk-write diagnostics on file: $writes (macOS writes one when a day's writes exceed its budget)"
  grep -h -m1 'Low Power Mode' /Library/Logs/DiagnosticReports/disk\ writes_*.diag 2>/dev/null | tail -1 | sed 's/^ */  Latest diagnostic says: /'
fi

section "Battery and power"
pmset -g batt 2>/dev/null | tail -1 | sed 's/^ */  /'
system_profiler SPPowerDataType 2>/dev/null | grep -E 'Cycle Count|Condition|Maximum Capacity' | sed 's/^ */  /'
pmset -g custom 2>/dev/null | awk '
  /Battery Power/ { src = "battery" }
  /AC Power/      { src = "AC" }
  /^ *powermode/  { print "  Energy mode on " src ": " $2 "  (0 automatic, 1 low power, 2 high power)" }
  /^ *sleep /     { print "  System sleep on " src ": " $2 " min (0 = never)" }
  /^ *displaysleep/ { print "  Display sleep on " src ": " $2 " min" }'

section "Security and backups"
fdesetup status 2>/dev/null | sed 's/^/  /'
csrutil status 2>/dev/null | sed 's/^/  /'
spctl --status 2>/dev/null | sed 's/^/  Gatekeeper: /'
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate 2>/dev/null | sed 's/^/  /'
echo "  Time Machine: $(tmutil destinationinfo 2>&1 | head -1 | sed 's/^ *//')"
tmutil latestbackup 2>/dev/null | sed 's/^/  Latest backup: /'
echo "  Local APFS snapshots: $(tmutil listlocalsnapshots / 2>/dev/null | grep -c com.apple)"
mdutil -s / 2>/dev/null | tail -1 | sed 's/^[[:space:]]*/  Spotlight: /'
scutil --nc list 2>/dev/null | grep -i '(connected)' | sed 's/^ */  VPN: /'

section "What keeps the Mac awake right now (power assertions by process)"
pmset -g assertions 2>/dev/null | grep -E 'pid [0-9]+\(' | grep -E 'PreventUserIdleSystemSleep|NoIdleSleepAssertion|PreventUserIdleDisplaySleep|PreventSystemSleep' \
  | sed -E 's/^ *pid [0-9]+\(([^)]+)\).*(PreventUserIdleSystemSleep|NoIdleSleepAssertion|PreventUserIdleDisplaySleep|PreventSystemSleep) named: "([^"]*)".*/  \1: \2 (\3)/' | sort -u | head -12

section "Background jobs whose last run failed (launchctl list, non-zero status)"
launchctl list 2>/dev/null | awk -F'\t' 'NR>1 && $2 != 0 && $2 != "-" && $3 !~ /^com\.apple\./ {print "  exit " $2 "  " $3}' | head -12
echo "  (an item here failed on its last run; look at its StandardErrorPath or run it by hand)"

section "Stability: crash reports in the last 14 days, grouped by process"
find "$HOME/Library/Logs/DiagnosticReports" /Library/Logs/DiagnosticReports -maxdepth 1 -mtime -14 \
     \( -name '*.ips' -o -name '*.crash' -o -name '*.panic' -o -name '*.diag' \) 2>/dev/null \
  | sed -E 's#.*/##; s/[-_.][0-9]{4}-[0-9]{2}-[0-9]{2}.*//' | sort | uniq -c | sort -rn | head -12 | sed 's/^/  /'
echo "  Kernel panics on file: $(find /Library/Logs/DiagnosticReports -maxdepth 1 -name '*.panic' 2>/dev/null | wc -l | tr -d ' ')"

if [[ $WITH_UPDATES -eq 1 ]]; then
  section "Software updates"
  softwareupdate -l 2>&1 | grep -E 'Title|No new software' | sed 's/^ */  /'
fi

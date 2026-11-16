---
name: macos-efficiency-audit
description: >-
  Audit a Mac for wasted performance and disk space, then clean it up with the
  owner's confirmation at every step. Covers running processes and memory
  pressure, what starts at login (launch agents, Login Items, background items),
  data left behind by uninstalled apps, caches and downloads, large files, and
  system health (swap, uptime, updates, backups, firewall, energy mode). Use
  whenever the user asks why their Mac is slow, hot, loud or low on space,
  wants an audit or a spring cleaning, asks which background processes or
  startup items are unnecessary, wants the remains of deleted apps removed, or
  asks what can be deleted or moved safely, in any phrasing or language:
  "аудит ноутбука", "что жрёт память", "почему тормозит Mac", "что занимает
  место", "почисти кэши", "убери лишнее из автозагрузки", "disk full", "clean
  up my Mac", "my fan never stops". A single question from that list (just
  startup items, just disk space) is still this skill: run the matching part.
---

# macOS efficiency audit

Two halves. The audit only reads and ends in a report the owner can act on.
The cleanup changes things, one confirmed group at a time. Start with the
audit even when the request is "just clean up": the report is where the
person decides, and the measurements are what make the cleanup safe.

## Principles, and why

- **Trash, not deletion.** Everything removed goes through `scripts/trash.sh`
  into `~/.Trash`, so a wrong call costs a drag back instead of a file. The
  only exceptions are the tool-native cache commands (`npm cache clean`,
  `brew cleanup`, `uv cache clean`, `pip cache purge`, `docker system prune`),
  which rebuild on demand. Never empty the Trash: that click is the owner's,
  and it is the moment the space is actually freed.
- **One group, one yes.** Show the exact paths with sizes and what will be
  noticed, wait for the answer, act, verify, report. A yes for caches is not a
  yes for leftovers. The same applies to killing processes and quitting apps.
- **Never `sudo`.** Root-owned leftovers become one command block the person
  runs, with a line of explanation per item. An agent shell has no password
  anyway, and a privileged deletion must be a human decision.
- **Running apps keep their caches.** Moving a cache an app holds open leaves
  the app writing into the Trash. `scripts/holders.sh <path>` says who holds
  it; run it on every cache or updater folder before the folder enters a
  "safe" list, and quote the answer in the row. "Not running" is a claim
  about a process list, not a guess from the app name (Codex runs inside
  ChatGPT; a Sparkle `Updater` may be mid-download).
- **Explain the unfamiliar before being asked.** The person will not know what
  Colima, `mediaanalysisd`, a KeepAlive agent or a ShipIt folder is. One plain
  sentence at the first mention of each such term; `references/glossary.md`
  has them ready to copy.
- **Report what the shell showed, not what was expected.** Every number in
  the report comes from an output saved under `raw/` or quoted in the
  transcript; a claim you did not measure ("Spotlight indexes these folders")
  is marked as a guess or left out. Totals are the sum of their rows. Sizes
  are GiB as `du` prints them; say once that Finder's GB run about 7% larger.
- **Discretion.** Personal media and documents appear in the report as sizes
  and counts ("7 video files, 43 GB"), not as a list of titles, unless the
  person asks to see them.
- **Language.** Write the report and every question in the language the person
  used. Keep commands, paths and identifiers as they are.

## Workflow

### 0. Scope the request

Full audit: all of steps 1-3, then cleanup if asked. A focused question maps
to a part: "slow / fan / memory" → processes and system snapshot; "startup /
login items" → autostart; "what is eating my disk" → disk and leftovers;
"remains of deleted apps" → leftovers. Say in one line what you are about to
run and that nothing changes until the report.

Skim `references/macos-gotchas.md` once per session before writing shell of
your own; every entry there has cost an hour at least once (zsh's `path`
variable, missing `timeout`, empty globs, Login Items that are "disallowed").

### 1. Collect

The scripts live in this skill's `scripts/` folder; call them by absolute
path. They are read-only. Run the fast ones together and the slow ones in the
background, then read everything before interpreting.

| Script | What it answers | Time |
|---|---|---|
| `snapshot.sh [--with-updates]` | hardware, uptime, memory and swap, disk, battery and energy mode, security, backups, crash and disk-write diagnostics | 20 s (+60 s with updates) |
| `procs.py [--live] [--top N]` | memory by application, real CPU use, orphaned dev processes, VMs and container engines, system daemons burning CPU, helper counts | 5 s (+3 s live) |
| `launchd_audit.py` | every launch agent and daemon with a verdict (DEAD, running, loaded, off by user), Login Items with stale entries, mounted installer images | 5 s |
| `leftovers.py [--min-mb N] [--paths-out F]` | data of uninstalled apps grouped by inferred owner, with sizes | 1-3 min |
| `disk_report.sh [--quick] [--archive-dirs a:b]` | where the space is: home and Library maps, dev caches, cloud and media as totals, updater leftovers with their holders, browser caches, the Trash's biggest items, apps by last use, large files, dependency folders in retired projects | 2-10 min |
| `holders.sh PATH...` | which processes hold files under a path; run on every cache before it is called safe | seconds per folder |

A script that prints "not measured" or "timed out" for a part (Background
Task Management can hang on some machines) is telling you to say so in the
report, not to retry it in a loop. A script of yours that hangs is yours to
kill; do not leave it running behind a "read-only" audit. Keep the raw
outputs (`raw/` next to your notes) so every figure in the report can be
traced.

Things the scripts cannot see and you check by hand when relevant: Spotlight
privacy exclusions, a specific app's own storage setting, an app's pending
update (`pending` folders in the updater section), what a `root`-owned
daemon does (`ps` shows it; `launchctl print system/<label>` needs sudo).

### 2. Interpret

Use the thresholds in `references/report-template.md`; they are rules of
thumb that say when a number is worth a sentence. Patterns that recur on
developer machines:

- **Memory, not CPU, is the usual bottleneck**: swap in use plus a compressor
  holding a quarter of RAM means the machine is paging. Name the top five
  consumers by application and any VM that holds a fixed reservation while
  idle (`colima list`, `docker system df` show whether anything inside runs).
- **Electron sprawl**: four AI assistants, two editors and a browser easily
  take 15 GB; the finding is the count, not any single app.
- **Orphaned dev servers** (parent is launchd, not a launchd job, hours old)
  are leftovers of a closed terminal or agent session. Candidates, not
  verdicts: a database the person started by hand looks the same.
- **Weeks of uptime** show as a bloated `WindowServer` and daemons with hours
  of CPU time; the fix is a reboot, ideally paired with the pending security
  update.
- **Dead launch agents** (program missing) and Login Items with
  `missing value` are leftovers of uninstalled apps. Agents the person
  switched off in System Settings ("off (user)") are already harmless;
  report them only when their program is gone too.
- **Apps that are gone but still registered**: Login Items or Background
  Task Management entries pointing at a bundle that no longer exists, and
  hidden folders at home (`~/.SomeTool`) of tools nobody runs any more.
- **Leftovers list needs a human read**: the scanner cannot tell a rebranded
  app's old folder from junk, and a transcript database of a removed app is
  data worth exporting. Group by product, name what is data, then size it.
- **Updater leftovers** (`ShipIt/update.*`, Sparkle downloads,
  `pending` + `update.zip`) are free space; a `pending` folder is also an
  update waiting for the app to restart.
- **Dependency folders in retired projects** (`node_modules`, `.venv`) and
  package-manager caches are the safest gigabytes on the disk.
- **iCloud conflict copies** ("Name 2.md" next to "Name.md") appear in synced
  folders; `scripts/icloud_copies.sh DIR` tells identical from edited.
- **Risks that are not about speed**: no Time Machine destination, firewall
  off, pending security update, Low Power Mode on mains power. They belong in
  the first paragraph.

### 3. Report

Write it in the shape given in `references/report-template.md`: the headline
paragraph, at most eight key findings with numbers, three sections (processes
and autostart, leftovers, disk), then the lists that drive the next step: safe
to remove now, decide, needs the person (sudo block, app-internal steps,
Settings panes), and what was not measured. A "safe" row without a concrete
command or menu path is not finished; a "decide" row carries its two options.
Say each number once. End by asking which group to start with; do not start on
your own.

### 4. Clean up, group by group

Follow `references/cleanup-playbook.md`. The order is the order of safety:

1. Stop what only holds resources: idle VMs, orphaned dev servers, apps idle
   for days, a daemon that needs a reboot or a setting.
2. Autostart: dead agents (`launchctl bootout`, then trash the plist), stale
   Login Items, mounted installer images.
3. Leftovers of uninstalled apps, after the human read, via
   `leftovers.py --paths-out` → edit the list → `trash.sh --from`.
4. Caches and downloads: package managers with their own commands, updater
   leftovers, browser caches with the browser quit, logs, dependency folders
   in retired projects. App-internal caches (Telegram, Slack, Books, Spotify)
   are steps for the person, written out exactly.
5. Large personal data: present the options (external disk, cloud, delete);
   execute only the one the person names, and verify a copy before an
   original goes to the Trash.
6. Settings and hygiene the person does by hand: reboot with the update, Time
   Machine, firewall, energy mode, Spotlight privacy, emptying the Trash.

For every group: list with sizes → wait for the yes → act with the scripts →
`du`/`ls`/`ps` to verify → say what was freed outright, what is in the Trash,
what remains. When something is held by a running app or owned by root, say
so and move on; do not force it.

### 5. Hand back

Close with three numbers (freed, in the Trash, waiting for a decision), the
sudo block if any, the app-internal and Settings steps, and the updated
remaining list. Offer the next group rather than doing it.

## Scripts

All in `scripts/`, all runnable with `bash`/`python3` from any directory, no
dependencies beyond macOS and Python 3. `--help` or the header comment
explains options.

- `snapshot.sh` — system snapshot. Read-only.
- `procs.py` — processes by application, orphans, VMs, system hogs. Read-only.
- `launchd_audit.py` — launch agents, daemons, Login Items, Background Task
  Management, mounted images. Read-only.
- `leftovers.py` — data of uninstalled apps. Read-only; `--paths-out` writes a
  list for `trash.sh`.
- `disk_report.sh` — disk map. Read-only; `--quick` skips the slow searches.
- `holders.sh` — which running processes hold files under a path; the test a
  cache must pass before it is called safe.
- `trash.sh` — moves paths to the Trash with collision-safe names, refuses
  system and personal-data roots, skips root-owned items and prints the sudo
  command for them. `--dry-run` previews.
- `icloud_copies.sh` — finds "Name 2.ext" conflict copies; `--trash` moves the
  byte-identical ones.

## When the tools disagree

`ps` averages CPU over a process's lifetime, `top -l 2` shows now. Energy
mode has three sources (`pmset`, `system_profiler`, the daily diagnostics)
that can disagree; point to the Settings pane instead of picking one.
`mdls` "never used" means no launch recorded, which is also what a CLI-only
app looks like. Say which reading you trust and why, and let the person
resolve the rest.

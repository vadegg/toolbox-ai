# Report template

The report is the deliverable of the audit. It is read by the owner of the machine,
who may not know what `launchd` or RSS means, so every table row says what the
thing is and what to do about it. Write it in the language the person used.

## Shape

```
<Two or three sentences: the single biggest problem, the second one, and the
one risk that is not about speed (no backup, pending security update).>

**Key findings**            at most 8 bullets, each a fact with a number and a consequence

### 1. Processes and autostart
  table: memory by application | what is unnecessary right now (numbered, with the exact command)
  table: autostart by group (login items / own agents / third-party active / switched off / dead)

### 2. Leftovers of uninstalled applications
  table: application | where it lives | size   + total, + what in it is data rather than junk

### 3. Disk: delete or move
  table: where the space is (top-level map)
  table: safe to remove now, with the command or app step and the size
  table: decide (large personal data), with the two options per row

**What needs the person**   sudo block, Trash, app-internal steps, settings panes
**What I did not measure**  TCC-protected folders, skipped slow steps, anything unverified
```

Rules that keep it readable:

- Lead with the answer. The first paragraph must stand alone.
- One number per cell, GiB with one decimal (what `du` reports; say once that
  Finder's GB run about 7% larger), MiB only under 1 GiB. Round; nobody acts on
  12.97 versus 13.0. Do not mix a tool's own decimal figures (`ollama list`,
  `docker system df`) with `du` figures in one table without saying so.
- Name things by what the person sees (app names, folder names), not by process
  names, and give the process name in parentheses when it matters.
- Every recommendation carries its action: a command in backticks, a Settings path
  with arrows, or an app menu path. "Clean up caches" without a how is not a finding.
- Keep "safe now" and "decide" apart. Safe means: no personal data, rebuilt on
  demand, reversible through the Trash. Everything else is a decision.
- Totals: freed outright, moved to the Trash (not yet freed), waiting for a
  decision. A table's total is the sum of its rows: add them up before writing
  the heading, and keep "check first" items out of the "safe" table.
- A risk column says what is permanent and what is reversible. "Risk: none"
  belongs only to actions the Trash can undo; emptying the Trash, `ollama rm`,
  `docker system prune` and package-cache commands are permanent and say so.
- Corrections beat silence: when a later measurement contradicts an earlier line
  (a CPU figure that was elapsed time, a folder that turned out to be in use), say
  so plainly in the next message.

## Thresholds worth flagging (rules of thumb, not laws)

| Signal | Flag when | Say |
|---|---|---|
| Swap in use | > 2 GB, or compressor > 25% of RAM | memory is the bottleneck; name the top consumers |
| Uptime | > 14 days | reboot; WindowServer and daemons accumulate |
| VM or container engine | idle with no containers | its full reservation is wasted RAM |
| Orphaned dev process | parent launchd, > 1 h, not a launchd job | leftover of a closed session |
| Daemon CPU time | > 1 h total or > 50% now | name it and the likely cause |
| Launch agent | program missing | dead, remove plist |
| Login item | `missing value` | stale, remove |
| Leftover owner | > 100 MB, or any launch agent/driver | list it |
| Updater leftovers | > 200 MB | trash or restart the app |
| Package caches | npm/uv/pip/brew > 1 GB each | tool-native clean |
| Dependency folders in archives | any | recreate on demand |
| Apps | never launched or > 6 months, > 500 MB | candidate to remove, confirm |
| Trash | > 5 GB | remind to empty |
| Time Machine | no destination | the biggest risk on the list |
| Firewall | off | one switch |
| Disk-write diagnostics | any in the last week | heavy writers; check Activity Monitor → Disk after reboot |
| Energy mode | Low Power on mains | check System Settings → Battery |
| Sleep blockers | an app holds a sleep assertion for hours while idle | name it; "never sleep" on AC is a setting, not a bug |
| Failing background jobs | non-zero last exit status in `launchctl list` | name the job and its log path |
| Duplicate apps | two versions of the same product installed (old and new, beta and stable) | keep the one in use |
| Stale background items | Login Items entries for apps that no longer exist | remove in System Settings or via `osascript` |
| Security update | pending | install with the reboot |

## Example rows

```
| Application | Where | Size |
|---|---|---|
| MacWhisper (uninstalled) | Application Support: transcript database 6.7, models 6.0; caches 4.3 | 17.3 GB |
| Arc (uninstalled) | Application Support 7.2 + caches 1.6 | 8.8 GB |

| Safe to remove now | How | Frees |
|---|---|---|
| npm cache | `npm cache clean --force` | 13.2 GB |
| Chrome caches, three profiles | quit Chrome first; procedure in the playbook | 5.7 GB |
| Downloaded updates of Cursor, Pen, Typeless | move to Trash, or restart the apps to apply them | 3.1 GB |

| Decide | Size | Options |
|---|---|---|
| Ollama models, service disabled, newest from July | 57 GB | `ollama rm` the unused ones, or move the folder to an external disk |
| iMovie library, app never launched | 43 GB | external disk, or delete after a look inside |
```

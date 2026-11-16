# macOS gotchas for audit and cleanup work

Things that cost real time in practice. Read before writing shell for this skill;
every item here has bitten at least once.

## Shell

- **zsh: never name a variable `path`.** In zsh `path` is an array tied to `PATH`.
  `while read -r path; do …` silently empties `PATH` and every external command
  becomes "command not found" inside the loop. Use `p`, `src`, `entry`.
- **No `timeout`, no `tac`.** macOS ships neither. Use the Bash tool's own timeout,
  `tail -r` instead of `tac`, and `perl -e 'alarm …'` only if you really must.
- **Empty globs abort zsh commands.** `du -sk ~/Library/Developer/*` with no match
  makes zsh fail the whole command line ("no matches found") before `du` runs.
  Prefix with `setopt NULL_GLOB;` in zsh, `shopt -s nullglob` in bash, and check
  that at least one argument survived.
- **`pgrep` has no `-E`**; it takes a single extended-regex pattern already.
  `pgrep -fl 'a|b'` works, `pgrep -E` does not. `ps -axo pid,args | grep -E` is the
  portable fallback.
- **`ps` CPU is a lifetime average.** A process at 90% for the last hour can show 3%.
  Sample `top -l 2 -n 30 -o cpu -stats pid,cpu,command` and read the second block.
- **`lsof +D dir`** lists processes holding files under a directory. Slow on big
  trees; fine for caches. Use it before touching a cache of a running app.
- **`du -x`** stays on one volume; `/System/Volumes/Data` is where user data lives,
  `/` is a sealed system snapshot (12 GB) that is not the disk you are cleaning.
- **Invisible characters in names.** iCloud and Finder produce folder names with a
  narrow no-break space (U+202F, as in "7:25 AM") or NFD accents; a command typed
  with a plain space matches nothing and `rm -rf` says nothing. Copy paths from
  `ls -d` output or a `find -print0` list, never retype them, and check `ls -d
  "$path"` before any command that uses them.
- **Paths with spaces everywhere.** Quote, use `-print0 | xargs -0`, and never parse
  `ls`. Apple's folders ("Application Support", "Mobile Documents") guarantee pain.

## Permissions

- **TCC-protected folders** (`~/Library/Mail`, `Messages`, `Safari`, `Photos`,
  `Containers/com.apple.mail`, parts of `Desktop`/`Documents` for some hosts) answer
  "Operation not permitted" without Full Disk Access. Report them as unmeasured;
  do not retry in a loop.
- **`sudo` needs a password** in an agent shell (`sudo -n true` tells you). Root-owned
  leftovers (`/Library/LaunchDaemons`, `/Library/Audio/Plug-Ins/HAL`,
  `/Library/Application Support/<Vendor>`) go into one command block for the person
  to run, with a one-line explanation per item.
- **Automation prompts.** The first `osascript -e 'tell application "System Events"…'`
  or `tell application "Finder"` can raise a permission dialog for the host app.
  System Events is usually already allowed; Finder often is not, which is why
  `trash.sh` uses `mv` into `~/.Trash` instead of asking Finder.

## launchd, Login Items, Background Task Management

- Three folders: `~/Library/LaunchAgents` (per user), `/Library/LaunchAgents` (all
  users, root-owned), `/Library/LaunchDaemons` (system, root-owned). Apple's own live
  in `/System` and are off limits.
- `launchctl list` shows loaded user jobs: PID (or `-`), last exit status, label.
  A non-zero status on an item with `-` means the last run failed.
- `launchctl print-disabled gui/<uid>` is launchd's own override list. It is **not**
  the same as the switch in System Settings > Login Items.
- `sfltool dumpbtm` prints Background Task Management, which is what the Login Items
  pane shows. Disposition `[enabled, allowed, …]` runs; `[enabled, disallowed, …]`
  means the person switched it off in Settings and launchd will not load it at
  login even though the plist is present and `print-disabled` says enabled.
- A manually `launchctl bootstrap`-ed job can run now and still be disallowed for
  the next login. To make a user's own agent survive a reboot when BTM has it
  disallowed, either flip the switch in Settings (no CLI for that) or re-register it
  under a new label and plist name: BTM treats that as a new item, allowed by
  default. Mention the switch first; relabel only with consent.
- Stop a running job before trashing its plist: `launchctl bootout gui/<uid>/<label>`
  (daemons: `sudo launchctl bootout system/<label>`). Removing the file alone leaves
  the job running until logout.
- `KeepAlive` agents restart the moment they exit; killing the process is useless,
  bootout the job.
- Classic Login Items: `osascript -e 'tell application "System Events" to get the
  name of every login item'`; a path of `missing value` is a stale entry for a deleted
  app; `delete login item "Name"` removes it.
- Electron apps register `ShipIt`/`Sparkle` helper jobs under
  `application.<bundle>…` labels; they vanish with the app and are not plists to
  clean.

## Apps and caches

- **Caches of a running app** are live state. Moving them while the app holds files
  open leaves the app writing into the Trash. Quit the app first or skip it; package
  managers and updaters are the exception because they re-create everything.
- **Updater leftovers** are the easy wins: `~/Library/Caches/<app>.ShipIt/update.*`
  (Electron/Squirrel), `~/Library/Caches/<bundle>/org.sparkle-project.Sparkle`
  (Sparkle), `~/Library/Caches/<app>-updater/pending` + `update.zip`
  (electron-updater). A `pending` folder means the app downloaded an update and is
  waiting for a restart: restarting the app applies it and frees the space, which
  beats deleting and re-downloading.
- **Chrome** keeps the session only if `restore_on_startup` is 1 ("Continue where
  you left off") in each profile's `Preferences` (`session.restore_on_startup`);
  the default is a new tab. Before quitting Chrome for a cleanup, snapshot the open
  tabs with AppleScript (`URL of tabs of windows`) so they can be reopened. Chrome's
  on-device model lives in `Application Support/Google/Chrome/OptGuideOnDeviceModel`
  (around 4 GB) and comes back unless
  `defaults write com.google.Chrome GenAILocalFoundationalModelSettings -int 1`.
- **Telegram, Slack, Books, Spotify, Mail** manage their own caches; their in-app
  "clear cache" or "remove download" is safer than touching their containers.
- **Photos "Shared with You" analysis** (`mediaanalysisd` chewing CPU for hours on
  `~/Library/Photos/Libraries/Syndication.photoslibrary`) is switched off per app in
  `defaults write com.apple.SocialLayer SharedWithYouApps -dict-add com.apple.Photos
  -bool false`, then `killall sociallayerd`.
- **Microsoft AutoUpdate** is quiet when `defaults read com.microsoft.autoupdate2
  HowToCheck` says `Manual` and `StartDaemonOnAppLaunch` is 0.
- **Spotlight** indexes `~/.npm`, `~/.colima`, model folders and `node_modules` unless
  they are in System Settings > Spotlight > Privacy; dozens of `mdworker_shared`
  processes are the symptom.
- **Energy mode** on Apple silicon: `pmset -g custom` shows `powermode` per power
  source (0 automatic, 1 low power, 2 high power). `system_profiler SPPowerDataType`
  and the daily "disk writes" diagnostics in `/Library/Logs/DiagnosticReports` also
  record Low Power Mode, and the three can disagree; point the person at System
  Settings > Battery > Energy Mode rather than asserting one reading.

## Disk space

- Space moved to the Trash is not free until the Trash is emptied; say both numbers.
- iCloud Drive files can be local or evicted; `du` counts only local copies. "Optimize
  Mac Storage" and "Remove Download" are the move, not deletion.
- iCloud creates "Name 2.ext" conflict copies when a sync races a writer; APFS is
  normalization-insensitive, so a copy whose name is in NFD and an original in NFC
  look identical in Finder and differ for git and Linux. `icloud_copies.sh` handles
  the identical ones.
- Mounted `.dmg` installers hold space and clutter Finder: `hdiutil info` lists them,
  `hdiutil detach /Volumes/<name>` ejects, then the `.dmg` in Downloads can go.
- `mdls -name kMDItemLastUsedDate` is null for apps never launched from Finder or
  the Dock, including apps only ever started by a CLI (`code`, `soffice`) or by
  other apps. Treat "never" as "confirm with the person", not as unused.
- Homebrew: `brew cleanup -n --prune=all` previews, without `-n` it deletes old
  versions and the download cache; `npm cache clean --force`, `uv cache clean`,
  `pip cache purge`, `docker system prune -a` (needs the daemon up),
  `ollama rm <model>` are the tool-native ways; they are permanent by design and
  are the only deletions this skill performs without the Trash.

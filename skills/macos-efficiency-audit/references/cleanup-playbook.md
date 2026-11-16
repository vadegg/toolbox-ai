# Cleanup playbook

One group at a time, in this order of safety. For every group: show the exact
paths with sizes, say what the person will lose or notice, wait for a yes, act,
verify, then update the remaining list. A "yes" covers one group, not the session.

Two deletions are allowed, nothing else: moving to the Trash with
`scripts/trash.sh` (reversible until the person empties it), and the tool-native
cache commands listed under "Package managers" (they rebuild on demand). Never
empty the Trash, never `rm -rf` on the person's behalf, never run `sudo`; a
root-owned leftover becomes a command block the person runs themselves.

## 1. Things that only hold resources: stop, do not delete

| Finding | Action | Why it is safe |
|---|---|---|
| Virtual machine or container engine idle (Colima, Docker Desktop, UTM, Parallels) with no running containers | `colima stop`, quit Docker Desktop, suspend the VM | Frees the VM's whole RAM reservation; starts again in seconds |
| Orphaned dev server (parent is launchd, not a launchd job, hours old: `uvicorn`, `npm run dev`, `vite`, `esbuild --service`) | `kill <pid>`, then `kill -9` only if it survives 3 s | It belongs to a terminal or agent session that ended; restarting it is one command |
| App idle for days (video calls, meeting recorders, torrent clients) | Quit it, or say which ones to close | Memory back; nothing on disk changes |
| Daemon spinning for hours (`mediaanalysisd`, `photoanalysisd`, `WindowServer` after weeks of uptime) | Recommend a reboot first; for Photos analysis of Messages media, switch off Shared with You → Photos (`defaults write com.apple.SocialLayer SharedWithYouApps -dict-add com.apple.Photos -bool false && killall sociallayerd`) | A reboot clears the backlog; the setting only stops analysis of shared media |

Killing a `KeepAlive` launchd job is pointless (it respawns): use section 2.

## 2. Autostart

- **Dead agent** (program missing): `launchctl bootout gui/$(id -u)/<label>` (ignore
  "No such process"), then `trash.sh` the plist. Root-owned plists in
  `/Library/LaunchAgents` and `/Library/LaunchDaemons` go to the sudo block.
- **Agent of an uninstalled app** (program exists in `~/Library/Application
  Support/<Vendor>` but the app is gone): bootout, trash the plist and the vendor
  folder together in the leftovers group.
- **Login Item for a deleted app** (`missing value` path): `osascript -e 'tell
  application "System Events" to delete login item "<Name>"'`.
- **Login Item or agent the person does not want**: remove the login item the same
  way; for a launch agent, bootout and move the plist to the Trash. Keep the app
  itself unless asked; say the app may re-register the item when launched.
- **Background items switched off by the person** (BTM "disallowed"): already not
  running; mention them only when the plist points at a missing program.
- **Mounted installer images**: `hdiutil detach "/Volumes/<name>"`, then trash the
  `.dmg` in Downloads.
- Updaters (Google, Microsoft, Zoom, Adobe) are normal; offer to quiet them only when
  asked. Microsoft AutoUpdate: `defaults write com.microsoft.autoupdate2 HowToCheck
  -string Manual` and `StartDaemonOnAppLaunch -bool false`.

## 3. Leftovers of uninstalled applications

Produce the list with `scripts/leftovers.py --paths-out /tmp/leftovers.txt`, then
review it by owner before offering it:

- Drop owners that are clearly live: generic SDK folders (`CEF`, `firestore`,
  `segment`, `launchdarkly`), command-line tools, anything a running process holds
  (`lsof +D <path>`), anything whose name matches an installed app under a different
  bundle id (a rebranded app often keeps its old data folder).
- Call out data that is not junk even though the app is gone: transcript databases,
  recordings, license files, game saves, browser profiles with bookmarks. Offer to
  export or keep those files; trash the rest.
- Audio drivers in `/Library/Audio/Plug-Ins/HAL/<App>.driver` of removed apps stay
  loaded in `coreaudiod`; they are root-owned, so they go to the sudo block with
  `sudo killall coreaudiod` at the end (a second of silence).
- `pkgutil --pkgs` receipts of removed apps are harmless metadata; mention, do not
  chase.

Move the approved paths with `trash.sh --from /tmp/leftovers.txt` after removing
the lines the person wants to keep.

## 4. Caches and downloads

| Group | How | Notes |
|---|---|---|
| Package managers | `npm cache clean --force`, `uv cache clean`, `pip cache purge` (or `python3 -m pip cache purge`), `brew cleanup --prune=all`, `yarn cache clean`, `pnpm store prune`, `go clean -modcache`, `cargo cache` only if installed | Permanent by design, rebuilt on next install; `~/.npm/_npx` can go to the Trash as well |
| Containers and models | `docker system prune -a` (daemon must be up), `ollama rm <model>`, Hugging Face `~/.cache/huggingface/hub/models--*`, `~/.cache/whisper` | Models re-download; ask which ones are still used before anything |
| Updater leftovers | Trash `ShipIt/update.*`, `org.sparkle-project.Sparkle`, `*-updater/pending` + `update.zip`; skip any dir `holders.sh` shows held (an `Updater` or `ShipIt` process is mid-install) | A `pending` dir means an update waiting for restart: suggest restarting the app instead |
| Browser caches | Chrome: see below. Firefox `~/Library/Caches/Firefox/Profiles/*/cache2`, Brave/Arc/Dia/Edge/Vivaldi `~/Library/Caches/<Browser>` | Only with the browser quit |
| App logs | `~/Library/Logs/<App>` for apps with hundreds of MB (Zoom, Adobe, Codex) | Quit the app first or trash only files older than a day |
| Dependency folders in retired projects | `node_modules`, `.venv`, `venv` under archive folders only | `npm install` / `uv sync` recreates them; never touch active projects |
| Mail downloads, Messages attachments, Books audiobooks, News cache, Podcasts | In-app removal (Books: right-click → Remove Download; Mail: Settings → Accounts → Downloads) | Their containers are TCC-protected and owned by the app |
| Telegram, Slack, Spotify, Discord | Telegram → Settings → Data and Storage → Storage Usage → Clear; Slack → Help → Troubleshooting → Clear Cache and Restart; Spotify → Settings → Storage → Clear cache | Describe the steps; do not edit their containers |

### Chrome

1. Check each profile's `~/Library/Application Support/Google/Chrome/<Profile>/
   Preferences` for `session.restore_on_startup == 1`. If it is not set, say so:
   quitting will lose the open tabs unless the person turns on "Continue where you
   left off" (`chrome://settings/onStartup`) first.
2. Snapshot the tabs regardless: `osascript -e 'tell application "Google Chrome" to
   get URL of tabs of windows'` saved to a file.
3. Quit via `osascript -e 'tell application "Google Chrome" to quit'`, wait until
   `pgrep -x "Google Chrome"` is empty (30 s cap), trash
   `~/Library/Caches/Google/Chrome/<Profile>` for each profile, relaunch with
   `open -a "Google Chrome"`, and reopen the saved URLs if the session did not
   restore (`open -a "Google Chrome" url…`; they land in the default profile, say
   so).
4. The on-device model (`OptGuideOnDeviceModel`, ~4 GB) comes back unless the policy
   `defaults write com.google.Chrome GenAILocalFoundationalModelSettings -int 1` is
   set; that disables Chrome's built-in AI features, so it is a separate yes.
5. Service Worker caches and `File System` folders are site data, not cache: leave
   them.

## 5. Large personal data: decide, do not delete

Media libraries, downloaded music, iMovie/Final Cut libraries, recordings,
archives of client work, local copies of iCloud folders, old agent-session
transcripts. For each: size, last touched, and the two options (move to an external
disk or cloud, or delete). Execute only the option the person names, and for a move
confirm the destination has the space and the copy verified (`rsync -a --checksum`
or a size and count comparison) before the original goes to the Trash.

## 6. Settings and hygiene the person does by hand

Offer these at the end, with the exact pane and the reason:

- Reboot after long uptime (swap and compressor pressure, bloated `WindowServer`);
  pair it with a pending security update.
- Time Machine destination when `tmutil destinationinfo` says none.
- Firewall when it is off.
- Energy mode when diagnostics show Low Power Mode on mains power.
- Spotlight → Privacy for package caches and VM disks when `mdworker_shared` crowds
  the process list.
- Empty the Trash: say the number it will free and that it is their click.

## Never offer as "cache"

Folders that look like caches and are not. Listing them under "safe" is the
classic mistake of a hurried audit:

- `~/.claude/projects/*` holds session transcripts **and `memory/` folders**;
  `~/.codex`, `~/.cursor` and the like hold conversation history. They are the
  person's records: "decide", never "safe".
- Browser profile folders (`Default`, `Profile N`), their `Service Worker`,
  `IndexedDB`, `File System` and `Local Storage` subfolders: site data and
  logins, not cache. Only the `Cache`/`Code Cache` folders under
  `~/Library/Caches/<browser>` are cache.
- `~/Library/Application Support/<app>/User`, `*/settings*`, `*/workspaceStorage`:
  editor settings and per-project state.
- Keychains, password-manager containers, Mail, Messages, Photos libraries:
  not on any list.
- The Trash itself: before suggesting "empty it", name its five biggest items
  (`du -sk ~/.Trash/* | sort -rn | head -5`). It may hold the previous
  cleanup, a browser profile or a folder somebody meant to restore. Emptying is
  permanent; say so.

## The sudo block

Collect every root-owned item that the person agreed to remove into one command
block, one line of explanation per item above it, and tell them it is permanent.
Example shape:

```bash
sudo rm -f /Library/LaunchDaemons/com.vendor.agent.plist && \
sudo rm -rf "/Library/Application Support/Vendor" /Library/Audio/Plug-Ins/HAL/VendorAudio.driver && \
sudo killall coreaudiod
```

Verify afterwards with `ls` and `ps`, and report what the shell showed, not what
was expected.

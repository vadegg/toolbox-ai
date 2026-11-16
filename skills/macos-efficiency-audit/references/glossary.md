# Glossary for the report

One plain sentence each, for the people who will read the report. Copy the
line next to the first mention of the term; adapt it to the person's
language. Add to this file when a new term shows up in a report twice.

| Term | What to say |
|---|---|
| swap | Memory the Mac had to park on the SSD because RAM ran out; the more is in use, the more the machine waits on the disk. |
| compressor | RAM that macOS squeezes to fit more in; a large figure means the machine is already short of memory. |
| launch agent / daemon | A background job macOS starts for you at login (agent) or at boot (daemon), described by a small `.plist` file. |
| KeepAlive | A setting that makes macOS restart a background job the moment it stops; killing the process does nothing, the job must be unloaded. |
| Login Items | The list in System Settings of apps and background jobs allowed to start at login. |
| Background Task Management (BTM) | The macOS database behind the Login Items switches; "disallowed" there means the person switched the item off. |
| `WindowServer` | The system process that draws every window; it grows and burns CPU after weeks without a reboot. |
| `mediaanalysisd` | The system process that scans photos and videos for faces, text and objects; it can run for hours after a sync. |
| `mds`, `mdworker` | Spotlight indexing. Many `mdworker` processes mean Spotlight is indexing something large, often a dependency or cache folder. |
| Colima | A small Linux virtual machine that runs Docker on a Mac; it keeps its whole memory reservation even when no container runs. |
| Docker image | A downloaded template for a container; unused ones sit on disk until pruned. |
| ShipIt / Sparkle / `pending` folder | The auto-updater of a desktop app and the update it downloaded; a `pending` folder is waiting for the app to restart. |
| Electron app | A desktop app built like a website (Slack, Cursor, ChatGPT, Claude); each runs several helper processes and uses memory like a browser tab set. |
| helper process | A worker a big app spawns for a tab, a window or a plug-in; the count shows how heavy the app is, the memory is in the sum. |
| orphaned process | A program whose parent (a terminal, an agent session) has ended but which kept running; usually a dev server nobody will reach again. |
| RSS | The memory a process has in RAM right now; summed per app it ranks consumers but double-counts shared libraries. |
| cache | Data an app can rebuild or re-download; safe to clear when the app is not running. |
| container (`~/Library/Containers`) | The private folder macOS gives a sandboxed app for its data; it is deleted with the app only by hand. |
| group container | A folder shared by an app and its extensions; often survives the app's removal. |
| leftover | Data of an app that is no longer installed: settings, caches, containers, launch agents. |
| iCloud conflict copy | A file named "Name 2.ext" that iCloud created when two writers changed the same file; identical copies are junk, differing ones are an unmerged edit. |
| `brctl evict` | Tells iCloud Drive to keep only the cloud copy of a file and drop the local bytes. |
| TCC | The macOS permission system; folders like Mail and Photos answer "Operation not permitted" to tools without Full Disk Access. |
| SMART | The SSD's own health self-report; "Verified" means no failure predicted. |
| Low Power Mode | An energy mode that slows the CPU to save battery; on mains power it only slows the Mac. |
| Time Machine destination | The disk or network share backups go to; "none configured" means there is no backup at all. |
| Trash | Deleted files that still take space until the person empties it; everything this audit removes goes there first. |

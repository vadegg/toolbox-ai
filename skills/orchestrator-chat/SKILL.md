---
name: orchestrator-chat
description: >-
  Use when the user wants one long-lived Claude Code chat to become the orchestrator of a
  big project: a pinned chat that is compacted instead of archived, answers questions about
  the project's other chats with any tool, searches, archives and unarchives them, and
  carries its own editable prompt that is re-injected after every compaction and whenever
  the file changes. Also use to rebind that role to another chat (after a fork), to change
  which instruction files it watches, or to retire it. Triggers: "make this chat the
  orchestrator", "orchestrator for project X", "личный промпт для чата", "сделай этот чат
  оркестратором", "чат, который никогда не архивируется", "перепривяжи оркестратор".
---

# Orchestrator chat

Turn one Claude Code chat into the standing orchestrator of a project. Claude Code only;
Codex has no compaction hook to carry the prompt.

## Where the prompt lives, and why

```text
<project-root>/orchestrator/
├── PROMPT.md     the chat's own prompt; the owner edits "Owner's rules" by hand
├── session-id    the one chat this prompt belongs to
├── watch         optional: instruction files to re-inject when edited, one path per line
├── AGENTS.md     what this folder is, for other agents
└── .state/       snapshots of watched files; never committed
```

- **In the project, not in `~/.claude/`.** The prompt is about the project and the owner
  edits it beside the project's `AGENTS.md`; it moves with the project when the project is
  archived, and every path in it is relative to one root.
- **One folder per project, one chat per folder.** `session-id` binds the prompt to a
  single chat, so the project's other chats, which share the same instruction files, never
  receive it. A fork gets a new id and starts without the prompt until rebound.
- **One global hook, not one per project.** `scripts/inject-prompt.sh` is registered once in
  `~/.claude/settings.json`. It walks up from the session's `cwd` to the nearest
  `orchestrator/session-id` and stays silent unless that file names the current chat. A new
  orchestrator then needs only its folder, and team repositories never get a personal hook
  in their committed `.claude/settings.json`.
- **Desktop and CLI ids both work.** The script matches `CLAUDE_CODE_HOST_SESSION_ID`
  (desktop app, `local_…`, stable across restarts) or the hook input's `session_id` (CLI).

**Compaction is manual.** The default is auto-compact off for every session
(`autoCompactEnabled: false` in `~/.claude/settings.json`), and the orchestrator is compacted
only when the owner runs `/compact`, so a summary never lands mid-task without warning. The
prompt tells the chat to remind the owner once when the conversation grows long.

What reloads: compaction re-reads `CLAUDE.md`/`AGENTS.md` itself; the `SessionStart` hook
(matcher `compact|resume`) adds `PROMPT.md`; the `UserPromptSubmit` hook adds any watched
file edited since its snapshot — whole up to 8 000 bytes, as a diff above that, because hook
output over ~10 KB reaches the chat only as a preview. Skills and settings reload live.
**MCP servers do not reload:** compaction does not reconnect them, and nothing inside a chat
can. A dropped stdio server or one newly added to `.mcp.json` needs the chat's process
restarted (resume keeps the conversation). Say this to the owner; never promise otherwise.

## Set up a new orchestrator

1. **Pick the chat and the root.** Default: the current chat, rooted at its `cwd`. Get the
   id with `get_session("self")` (desktop) or `$CLAUDE_CODE_SESSION_ID` (CLI). If the root
   already has `orchestrator/session-id` naming another live chat, ask before taking over.
2. **Keep the chat alive.** Pin it (`set_pinned("self", true)` in the desktop app; pinned
   chats are skipped by auto-archiving) and read `auto_archive_inactive_days` with
   `get_settings`. Report the value; change it only if the owner asks. Rename the chat only
   if the owner gives a title. Check that `autoCompactEnabled` is `false` in
   `~/.claude/settings.json`; if it is not, give the owner that line to set rather than
   editing the file yourself, since it switches auto-compact off for every session.
3. **Create the folder.** Fill `assets/PROMPT.template.md` (`{{PROJECT}}`, `{{ROOT}}`,
   `{{TITLE}}`, `{{SESSION_ID}}`) into `orchestrator/PROMPT.md`, write the id into
   `session-id`, and write a short `orchestrator/AGENTS.md` describing the folder. Add
   `.state/` to `orchestrator/.gitignore`. In a Git repository the owner does not want this
   committed in, add `/orchestrator/` to `.git/info/exclude` instead. If the project's root
   `AGENTS.md` keeps a layout list, add one line for `orchestrator/`.
4. **Install the global hook once.** Make sure this skill is linked into `~/.claude/skills/`
   (`bin/skills link-global orchestrator-chat --agent claude` in the toolbox), then check
   `~/.claude/settings.json` for a hook already calling `orchestrator-chat/scripts/inject-prompt.sh`.
   If it is missing, merge these entries into the existing `hooks` arrays without dropping
   any other hook:

   ```json
   "SessionStart": [{ "matcher": "compact|resume", "hooks": [{ "type": "command",
     "command": "\"$HOME/.claude/skills/orchestrator-chat/scripts/inject-prompt.sh\" full",
     "timeout": 10 }] }],
   "UserPromptSubmit": [{ "hooks": [{ "type": "command",
     "command": "\"$HOME/.claude/skills/orchestrator-chat/scripts/inject-prompt.sh\" changed",
     "timeout": 10 }] }]
   ```

   Auto mode usually refuses an agent's edit to settings files as self-modification. When it
   does, give the owner the snippet and the file path and stop there; do not look for a way
   around the refusal. If the project already carries an older per-project hook for its own
   orchestrator script, remove that entry when the global one goes in, or the prompt
   arrives twice.
5. **Seed and verify.** Pipe a fake hook input through the script and check three cases:

   ```bash
   s=~/.claude/skills/orchestrator-chat/scripts/inject-prompt.sh
   echo '{"cwd":"<root>","session_id":"<id>"}' | "$s" full | head -3      # prints PROMPT.md
   echo '{"cwd":"<root>","session_id":"<id>"}' | "$s" changed | wc -l     # 0: nothing edited
   echo '{"cwd":"<root>","session_id":"other"}' | CLAUDE_CODE_HOST_SESSION_ID= "$s" full | wc -l  # 0
   ```

   The first `full` run also writes the snapshots, so the next message does not re-send
   unchanged files. Ask the owner to run `/compact` once and confirm the prompt came back.

## Rebind, change what is watched, retire

- **Rebind** (a fork, or a fresh chat takes over): write the new id into `session-id` and
  run step 5 for it. Only one chat holds the role at a time.
- **Watch other files:** list them in `orchestrator/watch`, one path per line, `~` allowed,
  `#` for comments. The file replaces the default list; `PROMPT.md` is always watched.
- **Retire:** empty `session-id` to silence the hook at once, then archive the folder the
  way the project archives anything else. Leave the global hook; it costs nothing without a
  bound folder.

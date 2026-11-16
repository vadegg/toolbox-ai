# Toolbox - AI

This repository is the source of truth for personal Agent Skills and related
developer tooling. Each skill lives in `skills/<skill-name>/` and can be enabled
for Codex, Claude Code, or both, either globally or only for a selected project.

## Layout

```text
toolbox-ai/
├── skills/
│   ├── macos-efficiency-audit/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   ├── references/
│   │   └── scripts/
│   ├── orchestrator-chat/
│   │   ├── SKILL.md
│   │   ├── assets/
│   │   └── scripts/
│   └── ship/
│       ├── SKILL.md
│       └── agents/openai.yaml
├── bin/
│   ├── check
│   └── skills
└── .github/workflows/validate.yml
```

Add future skills as sibling directories under `skills/`. Keep credentials,
machine-specific configuration, and generated output outside this repository.

## Enable a skill

List the available skills:

```bash
./bin/skills list
```

Enable a skill globally for Codex, Claude Code, or both:

```bash
./bin/skills link-global ship
./bin/skills link-global ship --agent claude
./bin/skills link-global ship --agent all
```

Enable a skill only for one project:

```bash
./bin/skills link-project ship /path/to/project
./bin/skills link-project ship /path/to/project --agent claude
./bin/skills link-project ship /path/to/project --agent all
```

Codex project links live in `<project>/.agents/skills/`; Claude Code project
links live in `<project>/.claude/skills/`. In a Git project, the command adds
the exact personal link to the repository's local exclude file, so it does not
appear in `git status` and cannot be committed accidentally.

If a project-local skill should be shared with every contributor, copy it into
the agent's project skill directory and commit that copy instead of using a
personal link.

`orchestrator-chat` (Claude Code only) turns one long-lived chat into a project's
orchestrator. Its prompt lives in `<project>/orchestrator/PROMPT.md`, bound to one chat by
`orchestrator/session-id`, and `scripts/inject-prompt.sh`, registered once as global
`SessionStart` and `UserPromptSubmit` hooks, re-injects it after compaction and on edits.
Link it for Claude only:

```bash
./bin/skills link-global orchestrator-chat --agent claude
```

## Skill settings

`macos-efficiency-audit` audits a Mac (processes, startup items, leftovers of
removed apps, disk space, system health) and cleans up one confirmed group at a
time. It never deletes: removals go to the Trash through `scripts/trash.sh`, and
root-owned items become a command for you to run. The scripts in `scripts/` are
plain Bash and Python 3 with no dependencies and can be used on their own:

```bash
skills/macos-efficiency-audit/scripts/snapshot.sh
skills/macos-efficiency-audit/scripts/procs.py --live
skills/macos-efficiency-audit/scripts/launchd_audit.py
skills/macos-efficiency-audit/scripts/leftovers.py --min-mb 20
skills/macos-efficiency-audit/scripts/disk_report.sh --quick
```

## Update

Pull the toolbox repository normally:

```bash
git pull --ff-only
./bin/check
```

Linked skills immediately resolve to the pulled files. Claude Code watches
existing skill directories for `SKILL.md` changes. For Codex, start a new task
after changing skill metadata so discovery is refreshed.

## Use on another machine

Clone this repository to any stable location, then run the appropriate link
commands. The checkout path does not need to match across machines.

```bash
git clone git@github.com:YOUR_ACCOUNT/toolbox-ai.git ~/toolbox-ai
cd ~/toolbox-ai
./bin/skills link-global ship --agent all
```

## Add another skill

Create `skills/<name>/SKILL.md`, optionally add `agents/`, `scripts/`,
`references/`, or `assets/`, then run:

```bash
./bin/check
```

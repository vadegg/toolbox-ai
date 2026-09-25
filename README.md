# Toolbox - AI

This repository is the source of truth for personal Agent Skills and related
developer tooling. Each skill lives in `skills/<skill-name>/` and can be enabled
for Codex, Claude Code, or both, either globally or only for a selected project.

## Layout

```text
toolbox-ai/
├── skills/
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

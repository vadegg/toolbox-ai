# Codex Toolbox

This repository is the source of truth for personal Codex skills and related
developer tooling. Each skill lives in `skills/<skill-name>/` and can be enabled
globally or only for a selected project.

## Layout

```text
codex-toolbox/
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

Enable a skill for every Codex project on the current machine:

```bash
./bin/skills link-global ship
```

Enable a skill only for one project:

```bash
./bin/skills link-project ship /path/to/project
```

The project command creates `<project>/.agents/skills/<skill-name>` as a
symlink to this checkout. In a Git project it also adds that exact path to the
repository's local exclude file, so the personal link does not appear in
`git status` and cannot be committed accidentally.

If a project-local skill should be shared with every contributor, copy it into
the project's `.agents/skills/` directory and commit that copy instead of using
a personal link.

## Update

Pull the toolbox repository normally:

```bash
git pull --ff-only
./bin/check
```

Linked skills immediately resolve to the pulled files. Start a new Codex task
after changing skill metadata so skill discovery is refreshed.

## Use on another machine

Clone this repository to any stable location, then run the appropriate link
commands. The checkout path does not need to match across machines.

```bash
git clone git@github.com:YOUR_ACCOUNT/codex-toolbox.git ~/codex-toolbox
cd ~/codex-toolbox
./bin/skills link-global ship
```

## Add another skill

Create `skills/<name>/SKILL.md`, optionally add `agents/`, `scripts/`,
`references/`, or `assets/`, then run:

```bash
./bin/check
```

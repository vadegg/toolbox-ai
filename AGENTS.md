# Repository instructions

- Treat `skills/<name>/` as the canonical source for every personal skill.
- Keep the skill directory name equal to the `name` in its `SKILL.md`
  frontmatter.
- Put only reusable instructions and resources in Git. Never commit secrets,
  credentials, machine-specific paths, session data, or generated output.
- Keep global and project activation outside the source tree by using
  `bin/skills`; do not duplicate a skill merely to change its scope.
- Run `./bin/check` after changing any skill or repository helper.
- Do not publish, push, or change a Git remote unless the user explicitly asks.

---
name: ship
description: >-
  Use when the user asks to ship the current session's changes: commit them,
  land them on the repository mainline, push, deploy when the project defines a
  deployment, clean up safely, and archive the completed task when the host
  supports task archiving — for example "ship", "ship it", "отгрузи", "отгрузи
  и задеплой", or "влей, запушь и выкати".
---

# Ship

Take the changes made in this coding-agent session all the way to a verified
deployment.
Invoking this skill authorizes the relevant test run, commit, merge, ordinary
push, and an unambiguous project-defined deployment. It does not authorize force
pushes, bypassing branch protection, deleting remote branches, rolling back a
failed release, or destructive cleanup before the release is verified. It does
authorize removing the current linked worktree and deleting the fully landed
local source branch during final cleanup once every prior step has succeeded;
never delete the selected base branch.

Preserve unrelated changes that predate the session. Never claim success until
the mainline push and, when applicable, deployment verification have succeeded.

## 1. Preflight before mutations

Read repository instructions such as `AGENTS.md` and `CLAUDE.md`, then inspect in
one pass:

- repository root, absolute Git dir, common Git dir, current branch or detached
  `HEAD`, status, upstream, unpushed commits, remotes, and `git worktree list
  --porcelain`;
- local and remote `main` and `develop` refs after fetching the relevant remote;
- the session's tool history and diff, so session-created changes can be separated
  from pre-existing user WIP;
- test commands from repository instructions, manifests, and CI configuration;
- deployment behavior from repository documentation, scripts, and CI/CD config,
  including the target and the documented success check.

Select the base deterministically:

1. If both `main` and `develop` exist locally or on the relevant remote, use
   `develop`.
2. If exactly one exists, use it.
3. If neither exists, stop and ask which branch is the mainline. Do not guess.

Resolve deployment ambiguity before committing or pushing. A push-triggered
deployment counts as the launch; do not also start a duplicate manual deployment.
If several environments or deploy commands are plausible and the repository does
not define a default, ask the user which target to use.

Nothing to ship means: no uncommitted session changes, no unpushed session
commits, and the candidate source commit is already contained in the selected
base. Report that and stop without deploying.

## 2. Tests exactly when needed

Determine whether the project has an applicable test suite. Use the repository's
documented command rather than inventing one.

- If no applicable tests exist, record that fact and continue.
- If a successful applicable test run already happened in this session after the
  last test-affecting edit, reuse that result. Do not run the same passing suite a
  second time merely because shipping started.
- Otherwise run the applicable suite once before committing. A failed or aborted
  run is not a successful verification: fix an in-scope failure and rerun only as
  needed to obtain a pass.
- Any later conflict resolution or other test-affecting edit invalidates the
  earlier result. Run the relevant tests again before pushing the resolved result.

Do not conceal unrelated pre-existing failures. If they prevent a defensible
ship, stop with the exact failure and what would be needed to continue.

## 3. Commit only this session's work

Never use `git add .` or `git add -A`.

- Stage modified tracked paths or hunks that this session changed, and stage only
  session-created untracked files that belong to the requested work.
- Leave pre-existing user WIP, ignored files, secrets, credentials, build output,
  and unrelated generated artifacts untouched. Honor repository confidentiality
  rules.
- If session edits and pre-existing edits share a file, use patch-level staging
  and verify both the staged and unstaged diffs. If the intentions cannot be
  separated confidently, ask rather than absorbing or discarding user work.
- Review the complete staged diff, then write a meaningful commit message based on
  the change and any repository commit conventions.

Record the source commit SHA. Detached `HEAD` is valid; do not create a permanent
branch merely to make landing possible unless the repository workflow requires
one.

## 4. Land on the selected mainline

Bring the selected base up to date with its remote, then merge the source commit
into it without rewriting published history. Respect the repository's documented
landing workflow and branch protection. A temporary detached landing worktree is
often the safest choice when the base is checked out elsewhere or its owning
worktree has unrelated WIP; remove that temporary worktree after use.

If a base-owning worktree must be used, preserve its staged, unstaged, untracked,
and ignored state. Restore and verify that state after landing; never include it in
the session commit.

For conflicts:

1. Inspect the base, source, and surrounding code to understand both intentions.
2. Resolve the smallest coherent result; never choose an entire side merely to
   clear conflict markers.
3. Verify there are no unmerged index entries or conflict markers.
4. Re-run affected tests because the resolution is a new edit.
5. Commit the merge or resolution normally.

If the correct resolution requires product intent or information not present in
the repository or conversation, abort or leave the merge in a recoverable state,
do not push a conflicted result, and report the conflicting paths and decision
needed from the user.

## 5. Push safely

Push the landed result to the selected remote base and verify that the remote base
contains the final landing commit. Push a feature branch only when the repository
workflow requires it.

Never force-push. If the remote base moved, fetch it, integrate the new tip,
resolve and retest if necessary, then retry an ordinary push. If branch protection
requires a pull request or human approval, use the documented flow when it is
available and already authorized; otherwise report the gate instead of bypassing
it.

## 6. Deploy and verify

After the successful mainline push:

- If pushing the base triggers deployment, monitor the project-provided status or
  CI signal rather than triggering another deploy.
- If the repository defines an unambiguous manual deployment for the selected
  target, run it once.
- If the project has no deployment mechanism, say so and treat this step as not
  applicable. This is a successful no-deploy outcome for pipeline purposes: do
  not stop here, and continue through branch and worktree cleanup exactly as
  after a successful deployment.

Use the documented deployment status, health check, or smoke test as proof. A
command returning zero is sufficient only when the project itself defines that as
success. If deployment fails, report the pushed commit, failing stage, and useful
logs; do not roll back or tear down the worktree unless the user explicitly asks.

## 7. Branch and worktree cleanup

Only after the push and deployment (or the explicit no-deploy determination) are
successful, decide whether the current checkout is a linked worktree by comparing
the absolute Git dir and common Git dir and consulting `git worktree list`.

Identify the local source branch captured during preflight. If the source was a
detached `HEAD`, there is no source branch to delete. Otherwise, the source branch
must be different from the selected base, its tip must be an ancestor of the
verified remote base, and it must contain no commits absent from that base. Delete
only such a fully landed local source branch, using lowercase `git branch -d`.
Never delete the remote source branch implicitly.

If this is not a linked worktree, switch the current checkout to the selected
base, or to a safe detached copy of the verified base when that branch is owned by
another worktree, then delete the fully landed local source branch. If `-d`
refuses, do not use `-D`; report the commits Git still considers unmerged. Finish
with the report below only after deletion succeeds or there was no source branch.

If it is a linked worktree:

1. Do not ask the user whether to remove it. Successful invocation of this skill
   already authorizes automatic final cleanup.
2. Re-check that the path is still the same worktree, that the landing commit
   remains on the verified remote base, and that no new uncommitted work appeared.
   If any check fails, preserve the worktree and report the exact blocker.
3. Prefer an app-provided worktree cleanup or handoff action when available.
   Otherwise run cleanup from a stable checkout outside the target worktree.
4. In one final tool call, use ordinary `git worktree remove` and then lowercase
   `git branch -d` for the fully landed local source branch, if one exists. Never
   delete a remote branch implicitly. Do not force removal past source changes or
   use `-D` without new explicit authorization.

Prepare the final report before removing a linked worktree. Make the cleanup
sequence that removes it the final shell or filesystem action of the task.
Manually removing the active execution directory can invalidate later shell work,
so do not plan any filesystem verification or cleanup after that action.

## 8. Archive the completed task when supported

After the push, deployment or explicit no-deploy determination, branch cleanup,
and worktree cleanup have all succeeded, archive the current task without asking
the user when the host exposes a task- or thread-archival capability. In Codex,
prefer `set_thread_archived` with `archived: true`; omit the thread id when that
targets the calling task. Archiving is organization, not deletion.

Claude Code has no equivalent standard task-archival operation. When the host
does not expose one, do not simulate archival by deleting session data, closing
the terminal, or removing additional files. Treat archival as unavailable, not
as a shipping failure, and report that outcome honestly.

Make archival the final app tool call, after the final shell action, then return
the already prepared textual report. Do not archive when any shipping or cleanup
step failed, was skipped, is still running, or needs user input. If the archival
tool fails, leave the task unarchived and report that honestly.

## Report

Keep the handoff compact but auditable:

- source and landing commit SHA/message;
- selected base and why it was selected;
- test command and whether it was run now or reused from this session;
- push destination and result;
- deployment mechanism, target, and verification evidence, or why deployment was
  not applicable;
- conflicts resolved or the exact blocker;
- local source-branch cleanup result;
- worktree cleanup result;
- task archival result.

Do not imply that a push, deployment, cleanup, or archival succeeded when it was
skipped, still running, or failed.

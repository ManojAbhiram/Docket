# AGENTS.md

The standard every AI coding agent follows in this repository (Claude Code,
Cursor, Codex, Gemini CLI, Copilot). It loads into every session, so it holds
only what applies on every turn; the skills carry each step's detail.

Each step of the workflow names one skill, from Bearing, Superpowers, gstack,
or another installed pack. Unsure which one: `workflow` names the next step and its
skill.

## Skill packs

- Bearing owns task setup, workflow routing, technology decisions, handoff,
  and the definition of done.
- Use installed Superpowers skills for brainstorming, writing and executing
  plans, test-driven development, systematic debugging, code review, and
  verification before completion when relevant to the task.
- Use installed gstack skills for product and engineering plan reviews,
  code review, browser inspection, QA, and design review when relevant to
  the task.
- Discover each pack in the current agent's available skills or installed
  skill directories, and read the relevant `SKILL.md` before using it.
  If a required skill is unavailable, report it rather than inventing its
  instructions or claiming it ran.
- These packs supplement Bearing's workflow. Repository ground rules still
  apply, including to branch-finishing, shipping, and deployment skills.
  Prepare prohibited commands for the engineer; never execute them.

## Ground rules

Breaking one gets the change rejected, whatever else it does.

1. Never commit to `main` (or the trunk the snapshot names). Work on a task branch.
2. Never push, open a merge or pull request, merge, tag or deploy. Prepare the
   command and hand it to the engineer.
3. Never commit a secret, key, certificate or `.env` file, and never read one
   into context.
4. Never touch a production system, database or bucket, not even to read.
5. Never rewrite history: no amend, rebase, force-push, `reset --hard`.
6. Never weaken a guardrail to go green: no lint suppression, no `any` or
   `@ts-ignore`, no skipped test, no lowered threshold, no relaxed CI rule.
7. Never add a dependency nobody asked for; propose it with the reason.
8. Never invent an API, field, table, variable or command; find it in the code first.
9. Stay in scope. What you notice in passing goes under "Noticed", unfixed.
10. Report honestly: a check you did not run is "not run", never "passing".
11. No AI attribution in commits, requests or documents.
12. No em dashes in prose; rewrite the sentence.

## Working here

- Every change has a task id and a branch: `start-task` creates
  `feature|bugfix|chore|docs/<ID>-<PascalName>`. One task per session.
- Every command is a Makefile target; `make help` lists them and `make check`
  is the gate CI runs.
- Search before reading, open only what you located, and copy the shape,
  naming and tests of the closest existing example.
- More than three files, or a change to a schema, API contract, auth or
  billing: agree a plan before the first edit.
- A technology choice is never silent: `tech-decision` gives options and a
  recommendation, the engineer decides, `adr` records it.
- Commits are Conventional with the task id at the end of the subject:
  `feat(auth): add OTP lockout [TASK-142]`.
- State that must outlive the session: `.bearing/state/` via `session-handoff` (local, ignored); shared progress: `docs/progress/<ID>.md` (committed).
  Scratch: `.scratch/`. Nothing at the root such as `NOTES.md`.
- Done means `definition-of-done` passed with evidence. Code, database, testing and
  security rules live in `.claude/rules/` and load with the files they cover.

## Reporting

End every task in this shape: `## Changed` (path: what and why), `## Verified`
(the command and the tail of its output), `## Not done` (asked, not delivered,
why), `## Noticed` (seen in passing, not fixed). No full diffs, no restating
the task.

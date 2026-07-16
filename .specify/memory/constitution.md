<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: MINOR — four new engineering-discipline principles added
(VII–X). No existing principle removed or redefined; no governance change.

Principles added in 1.1.0:
- VII. Think Before Coding
- VIII. Simplicity First
- IX. Surgical Changes
- X. Goal-Driven Execution

Principles carried forward from 1.0.0 (unchanged):
- I. Local-Only Operation
- II. Privacy of Transcript Data
- III. Read-Only Toward Claude Code
- IV. Observer, Not Participant
- V. Correctness Over Completeness
- VI. Simple to Run

Sections (unchanged): Technology Constraints; Development Workflow & Quality Gates.
Removed: none.

Templates & docs consistency:
- ✅ .specify/templates/plan-template.md — "Constitution Check" gate references
  the constitution generically and remains compatible; no change required.
- ✅ .specify/templates/spec-template.md — no constitution-specific content; compatible.
- ✅ .specify/templates/tasks-template.md — no constitution-specific content; compatible.
- ✅ .claude/skills/*/SKILL.md (speckit command definitions) — no outdated or
  contradicting references; compatible.
- N/A README.md / docs/ — none present in repository.

Deferred TODOs: none.

History:
- 1.0.0 (2026-07-15): Initial ratification. Six founding principles (I–VI),
  Technology Constraints, Development Workflow & Quality Gates, Governance.
-->

# Throughline Constitution

## Core Principles

### I. Local-Only Operation

The tool MUST NOT open any network connection. No telemetry, no cloud services, no
remote APIs, no account or login systems, no automatic update checks, no analytics
beacons — nothing that transmits or receives over a network. All data the tool
produces and consumes MUST remain on the user's machine.

This is a hard constraint, not a preference. No feature, convenience, performance
optimization, or future integration justifies an exception.

**Rationale**: The tool handles sensitive local data (see Principle II). The only
way to guarantee that data never leaves the machine is to guarantee the tool never
speaks over a network. Absence of network code is verifiable; promises about network
behavior are not.

### II. Privacy of Transcript Data

The tool reads Claude Code session transcripts, which contain source code, file
contents, and user prompts. This data MUST NOT be transmitted anywhere (this follows
from Principle I and is restated here as a data obligation). The tool MUST NOT write
transcript data — or anything derived from it — outside its own working directory.

**Rationale**: Transcripts are among the most sensitive artifacts on a developer's
machine. Confining every derived byte to the tool's own working directory gives the
user a single, well-defined place to inspect, trust, and delete.

### III. Read-Only Toward Claude Code

All Claude Code files — transcripts, configuration, and session state — MUST be
treated as read-only inputs. The tool MUST NOT modify, delete, truncate, or corrupt
them. When processing could touch these files, the tool MUST copy the data into its
own working directory first and operate only on the copy.

The single permitted write into Claude Code's domain is the opt-in logging hook
described in Principle IV; nothing else in Claude Code's files may be altered.

**Rationale**: The tool is a measurement instrument layered on top of a system the
user depends on. Damaging that system to measure it is an unacceptable outcome, so
the source data is treated as immutable by default.

### IV. Observer, Not Participant

The tool measures; it MUST NOT change how Claude Code behaves. The one exception is
installing lightweight, passive logging hooks, and only when the user has explicitly
opted in. Such hooks MUST log only — they MUST NOT alter Claude Code's outputs,
decisions, prompts, or control flow.

**Rationale**: A measurement that perturbs the thing being measured is not a
measurement. Keeping the tool passive preserves the integrity of every number it
reports and keeps the user in control of the only intervention it is allowed to make.

### V. Correctness Over Completeness

Every number the tool reports MUST be defensible. A metric that can only be
approximated (for example, utilization) MUST be explicitly labeled as an estimate and
MUST state the method used to derive it. The tool MUST NOT present a proxy as ground
truth. When forced to choose, the tool reports fewer trustworthy metrics rather than
more dubious ones.

**Rationale**: A tool whose numbers cannot be trusted is worse than no tool, because
it produces confident wrong answers. Labeling estimates and disclosing methods lets
the user calibrate their trust rather than guess at it.

### VI. Simple to Run

Collection MUST be a single command. Viewing MUST be a single command. The tool MUST
NOT require a long-running daemon or background service the user has to start, watch,
or babysit.

**Rationale**: A tool that is annoying to run will not be run, and unused
instrumentation measures nothing. Two commands with no persistent process keep the
mental and operational cost near zero.

### VII. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs. Before implementing:

- State your assumptions explicitly; when uncertain, ask rather than guess.
- When multiple interpretations exist, present them — never pick one silently.
- When a simpler approach exists, say so; push back when warranted.
- When something is unclear, stop, name what is confusing, and ask.

**Rationale**: Silent assumptions produce work that solves the wrong problem. Naming
uncertainty before writing code is far cheaper than reversing a wrong build after.

### VIII. Simplicity First

Write the minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No flexibility or configurability that was not requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

The test: would a senior engineer call this overcomplicated? If yes, simplify. This
principle extends Principle VI (Simple to Run) from how the tool runs to how it is built.

**Rationale**: Every speculative line is a line someone must read, test, and maintain
for no delivered value. Simplicity is the default; complexity must earn its place.

### IX. Surgical Changes

Touch only what you must. Clean up only your own mess. When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor what isn't broken.
- Match the existing style, even where you would choose differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports, variables, and functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line MUST trace directly to the request.

**Rationale**: Unrequested edits inflate the review surface, obscure the real change,
and risk regressions in code that was already working.

### X. Goal-Driven Execution

Define success criteria, then loop until they are verified. Transform tasks into
verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass."
- "Fix the bug" → "Write a test that reproduces it, then make it pass."
- "Refactor X" → "Ensure tests pass before and after."

For multi-step tasks, state a brief plan, each step paired with its verification:

1. [step] → verify: [check]
2. [step] → verify: [check]
3. [step] → verify: [check]

**Rationale**: Strong, checkable success criteria let work proceed independently to
completion. Weak criteria ("make it work") force constant clarification and leave
"done" undefined.

## Technology Constraints

- **Language**: The implementation MUST be Python.
- **Dependencies**: The Python standard library is the default. Any third-party
  dependency MUST be justified in writing — what it does and why the standard library
  is insufficient — and that justification MUST be recorded (e.g., in the plan and
  dependency manifest). Unjustified dependencies are rejected.
- **Working-directory boundary**: The tool has exactly one place it may write: its own
  working directory. Every output, cache, copy, and intermediate artifact lives there.

## Development Workflow & Quality Gates

- Every implementation plan MUST pass a Constitution Check before work begins, and the
  check MUST be re-run after design.
- The following are violations that MUST block a change until resolved:
  - any outbound network call;
  - any write outside the tool's working directory;
  - any modification of Claude Code files, except an opt-in logging hook per Principle IV;
  - presenting an approximated metric without an estimate label and a stated method;
  - adding a third-party dependency without recorded written justification.
- Code review MUST verify compliance with every principle above; a reviewer who cannot
  confirm compliance MUST treat the change as non-compliant.
- Before release, any estimated metric MUST be confirmed to carry its label and method
  in the tool's actual output, not merely in documentation.

## Governance

This constitution supersedes all other practices, conventions, and preferences. When
guidance conflicts, this document wins.

Amendments require: a documented rationale, a version bump per the policy below, and
propagation of the change to dependent templates and docs (recorded in the Sync Impact
Report at the top of this file).

Versioning policy (semantic):

- **MAJOR**: Backward-incompatible governance changes, or removal/redefinition of a
  principle.
- **MINOR**: A new principle or section, or materially expanded guidance.
- **PATCH**: Clarifications, wording, and non-semantic refinements.

Compliance review: every plan and every pull-request review MUST verify adherence to
these principles. Any deviation MUST be justified in the plan's Complexity Tracking
section; deviations that cannot be justified MUST be rejected. Principles I through IV
are absolute hard constraints and are NOT subject to "justified exception" — they may
be changed only by amending this constitution, never waived case by case.

**Version**: 1.1.0 | **Ratified**: 2026-07-15 | **Last Amended**: 2026-07-15

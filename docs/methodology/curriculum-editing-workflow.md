# How this curriculum is edited: a human directing two AI agents

This document describes the working method behind the Berkeley Housing Pipeline
curriculum — how a single person, with no team, builds and maintains a 15-notebook
data-science course by directing two different AI agents, each with a distinct job.

It is written down for two reasons. First, so the process is repeatable: anyone
extending this work (to another city, or another subject) can adopt the same division
of labor. Second, because the method is itself part of what the curriculum teaches —
the course's later notebooks (JN0g, JN0h) describe the agent-assisted workflow, and
this is that workflow, applied to the curriculum's own construction.

## The three roles

The work is split among three participants, and the split is deliberate. Each role
does what it is best at, and — importantly — each role is kept *away* from what it is
bad at.

**The human (the director).** Owns every decision and every irreversible action.
Decides what to build, what "done" means, and what is true. Performs all
publish-to-the-world steps personally (commits to the public branch, pushes, deploys).
Reviews the actual rendered result, not a description of it.

**chat-Claude (planning, words, and judgment).** Designs the change before it is made;
drafts prose; fact-checks public claims before they ship; reviews voice and
beginner-readability; reasons about architecture. It produces *specifications and
text* — it does not touch the repository's files. Its value is thinking and verifying
against reality, not typing.

**Claude Code / "CC" (the hands).** Performs all filesystem, notebook, database, and
git operations. Edits code cells, runs notebooks to verify they execute, applies the
same change consistently across many files, and prepares commits. Its value is precise
execution and verification — running the code, diffing the result, proving nothing
unintended changed.

The human sits between the other two: asks chat-Claude to design and check, hands the
resulting instructions to CC to execute, watches the result, and approves.

## Who edits what

The single most useful rule is knowing, for any given change, which participant should
make it.

**The human edits directly** when the change is *prose they already know they want* —
rewording a sentence, fixing a typo, rewriting an explanation, adjusting a caption.
These are Markdown-only edits, made in a local editor (VS Code with the Jupyter
extension), where the change renders immediately. If the edit would touch executable
code or a number, it is not a direct edit — it goes to CC.

**CC edits** when the change touches **code, output, numbers, cross-file consistency,
or version control.** That includes: adding or changing a code cell; anything that must
be *run* to confirm it works (a displayed table, a computed value); any number that
appears in prose (which must be injected from live data, never typed); any change that
must stay identical across many notebooks; and all commits, branches, and pushes. CC
makes the change, runs the notebook to verify, and reports a reviewable diff.

**chat-Claude is consulted** when the need is *judgment or words that don't exist yet*
— "is this claim true?", "how should I phrase this?", "what's the right structure for
this section?", "does this read well for a beginner?", "is this the right approach?".
chat-Claude produces a draft or a specification; it never edits the repository itself.

The natural flow combines all three: **ask chat-Claude** to design, draft, or
fact-check; **the human or CC applies it** (the human for prose they'll type, CC for
code and output and sweeps); **the human watches it render** and approves; **CC
commits.**

## The live-render verification loop

A recurring weakness of working with a text-only AI assistant is that it reports a
*summary* of what it did, and a summary can be confidently wrong. This method closes
that gap with a simple arrangement: the human keeps the notebook open in VS Code while
CC edits it. As CC changes a cell, the change renders on screen. The human sees the
actual result — the real table, the real wording — and approves or corrects in real
time, rather than trusting a description after the fact.

This makes the human the live render-check that a text-only handoff lacks. It is fast
(no report-and-re-report cycle), and it catches the subjective things — voice, density,
whether a wide table is unreadable on a phone — at the moment they happen.

Two limits keep it safe:

- **Watching verifies prose and structure; it does not verify that code runs.** Seeing
  a code change appear on screen shows the new source, not that the cell still executes
  correctly. For any change that adds or alters executable lines, CC must still *run*
  the notebook and report the executed output. The human's live view and CC's execution
  are complementary, not redundant.

- **One editor per file at a time.** While CC is editing a notebook, the human watches
  and does not also type into it; editing the same file from two sides at once risks
  silently losing one side's work. To hand-edit, the human first tells CC to stand down
  on that file.

## Standing rules

These hold across all curriculum editing:

- **Numbers in prose are injected from live variables, never typed.** A debrief that
  states a count computes that count at run time and renders it; a hand-typed number
  silently drifts from the data the moment the data changes. (This is also the
  curriculum's own first lesson, enforced on the curriculum itself.)

- **Code cells stay unchanged except for intended logic.** When CC adds explanatory
  comments or display lines, it verifies the executable logic is otherwise identical and
  that every checkpoint still produces the same value. A moved checkpoint means
  something was disturbed.

- **Prose inside a code cell is still prose.** Some explanatory text lives inside a
  code cell (a rendered-Markdown call). Editing that text changes the cell's content but
  not its logic; it is treated as a prose edit, even though it is technically inside
  code.

- **Public factual claims are checked before they ship.** Statements about how a city
  operates, a person's name, a count, or a historical fact are verified against a source
  before they go live. In practice this catches real errors — claims that seemed settled
  but were wrong on inspection.

- **Commits stay with CC, and publishing stays with the human.** CC prepares commits
  with disciplined messages and tight scope; the human approves them, and personally
  performs every push and deploy. Nothing reaches the public site without an explicit
  human action.

## Why it is arranged this way

Each rule exists because the alternative failed at least once. Numbers are injected
because a typed number drifted. One-editor-per-file exists because two editors collided.
Public claims are checked because a confident assertion turned out false. The method is
not a theory imposed in advance — it is the accumulated residue of mistakes, written
down so they are not repeated. That, too, is the spirit of the course: state the rule,
show why it earns its place, and let the work prove it.

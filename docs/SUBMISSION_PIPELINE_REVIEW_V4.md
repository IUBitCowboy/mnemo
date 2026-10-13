# Skeptical Review — Submission Assessment Pipeline Design Spec (v4)

**Reviewer:** Claude (Opus 5)
**Date:** 2026-08-15
**Target:** `docs/SUBMISSION_PIPELINE_DESIGN.md` (Draft v4)
**Prior review:** `docs/SUBMISSION_PIPELINE_REVIEW.md` (v2)

---

## Top-line

v4 addresses the v2 review adequately at the architectural level. Killing the
cloud call from the PII path was the whole point, and it took Pass 2, the regex
sanitizer, the verification diff, and the audit-trail-as-control with it. The
compliance story is now "nothing leaves the machine," which is a real guarantee
rather than a probabilistic one. The instructor gate moved before the optional
cloud call and does double duty. Pass 1b is a script. Provenance is spelled
correctly. All 14 priority items from the v2 review are addressed in substance.

What v4 gets wrong is almost entirely in the newly-added machinery, and two of
those defects are load-bearing:

1. **Evidence verification silently deletes absence issues** — the highest-value
   category of finding in student work.
2. **Student-level cell-size suppression is the wrong k-anonymity unit for team
   assignments** — a FERPA regression introduced by v4's own changelog, which
   presents it as a refinement.

Fix those two before anything else.

A note on versioning: this document is labeled **Draft v4** and carries a v3→v4
changelog responding to a second review round. Where v4's changes made something
worse than v3 had it, that is called out below.

---

## 1. New issues, ranked

### 1.1 Evidence verification systematically deletes absence issues

The Pass 1a prompt says: *"Quote the EXACT text from the diff or source that is
evidence of the issue ... If you cannot quote exact text, do not report the
issue."*

There is no verbatim quote for a thing that is not there. The highest-frequency
issues in student work are absences: no tests, no error handling, no AI
disclosure, no design rationale in the PR description, no README update. The
spec's own `quality_signals` block is four-fifths absence claims
(`test_coverage: missing`, `ai_disclosure: missing`, `design_quality: missing`),
and the canonical matrix example throughout both design and review documents is
"missing tests."

As written, the pipeline reports the issues it can quote — naming, dead code,
long functions, a bad conditional — and drops the ones that matter
pedagogically. This is not a tuning problem; it is a structural mismatch between
one verification mechanism and a claim class it cannot handle.

**Fix: make evidence typed, with a verifier per type.**

```json
"evidence": { "kind": "quote",    "text": "def process(data):" }
"evidence": { "kind": "absence",  "predicate": "no_files_matching",
              "arg": "tests/**" }
"evidence": { "kind": "locator",  "file": "src/clock.py", "symbol": "tick" }
```

- `quote` → exact string match against diff + touched files (as today).
- `absence` → deterministic checker the *script* runs, from a closed enumeration
  of predicates the model may cite (`no_files_matching`, `no_symbol_matching`,
  `no_diff_hunk_in`, `pr_body_lacks_section`). The model asserts the predicate;
  the script decides whether it holds. The model cannot invent a predicate.
- `locator` → existence check on file/symbol.

Anything that fails its verifier is dropped, same as today. This preserves the
hallucination filter while making absence issues expressible and *more*
trustworthy than quoted ones, because the script adjudicates them.

### 1.2 "Exact string match" is under-specified and will misfire

Models normalize whitespace, strip diff `+`/`-` markers, reflow long lines,
convert smart quotes, and elide with `...`. A naive `quote in source` check
drops a large fraction of *correct* evidence.

The spec then reads a low pass rate as a model-quality signal: "if <70% survive,
the model is hallucinating too much — try a different model." You will swap
models to fix a normalization bug.

**Fix:** specify the canonicalization explicitly — strip leading diff markers,
collapse runs of whitespace to single spaces, normalize quote characters, reject
rather than expand ellipses, case-sensitive. Then hand-label evidence on 20–30
issues and test the checker against them *before* the pass rate is used as a
model-selection input. Report the two failure modes separately in the audit
object: `evidence_unmatched` (quote not found) vs `evidence_malformed` (quote
failed canonicalization preconditions).

### 1.3 Student-level suppression is the wrong unit — v4 regressed here

v4 changelog item 8 changed cell-size suppression from n<5 teams to n<5
students, reasoning that "an issue appearing in 3 of 14 teams may still affect
15 students (if those are 5-person teams) — that clears a student-level n<5
threshold."

That reasoning inverts the privacy property. On a team assignment, the students
on a team are **not independent observations** — they share the issue by
construction, because they share one submission. Counting five teammates as five
affected individuals inflates the apparent cell size by the team size, uniformly.

The consequence: an issue present in exactly **one** 5-person team clears a
student-level n≥5 threshold and lands in the class-facing matrix. That issue
identifies one team unambiguously to its own members, and — if described
specifically enough to be pedagogically useful ("team implemented the wall clock
with a busy-wait loop") — to their classmates. The v2 review's whole point about
the class-facing matrix was that the "reasonable person *without* personal
knowledge" carve-out does not protect you from classmates, who have personal
knowledge.

The change also happens to make the threshold *look* satisfied more often, which
is why it reads as a refinement in the changelog and is in fact a weakening of
the control the v2 review asked for.

**Fix:** the suppression unit must be the unit of independent observation.

- Team assignments: suppress issues appearing in fewer than **k distinct teams**.
  With 12–16 teams, k=3 is ~20% prevalence — comparable in protective strength to
  n=5 of 50 individuals.
- Individual assignments: n<5 students, as v3 had it.
- If you want a student count as a secondary gate, fine — but it must be an
  additional condition, never a substitute.

```yaml
ferpa:
  cell_size_suppression:
    team_assignment:       { unit: "teams",    min: 3 }
    individual_assignment: { unit: "students", min: 5 }
```

### 1.4 Suppression breaks matrix citation numbering

TA guides emit `matrix_citations: [{ "issue_number": 3 }]`, and the product pitch
is that TAs write "See Issue #3 in the matrix." But there are now two matrices:
`full_matrix.json` (instructor, all issues) and `corrective_matrix.md`
(class-facing, suppressed). Nothing in the spec states that issue numbers are
stable across them.

Three ways this breaks:

- **Renumbered:** every TA citation points at the wrong issue in the document the
  student actually reads.
- **Stable with gaps:** the class-facing matrix shows #1, #2, #4, #7 — visible
  gaps that disclose how many low-frequency issues were suppressed, and invite
  exactly the guessing the suppression rule exists to prevent.
- **Either way:** a TA citing a *suppressed* issue points a student at a document
  that does not contain it.

**Fix:** use opaque stable labels rather than sequential integers (e.g.
`M-7F2`), assigned at matrix-approval time and identical in both artifacts. Have
Phase 4 detect any TA-guide citation whose target is suppressed and rewrite it in
the guide as prose ("not in the shared matrix — describe directly") rather than
as a citation.

### 1.5 Clustering thresholds are set against each other so the split-flag always fires

Phase 2 merges at cosine distance 0.35 with **average** linkage, then sets
`contains_distinguishable_subcases` when intra-cluster average distance > 0.2.

Average linkage merges when the *mean* pairwise distance falls below the
threshold. So essentially every non-degenerate cluster lands with intra-cluster
mean distance somewhere in the 0.2–0.35 band, and the flag fires on nearly every
cluster. That is the same failure the v2 review identified for the verification
diff: a check that flags constantly produces flag fatigue, which produces
rubber-stamping — at the one gate that is now both the quality control and the
FERPA control.

**Fix:** make the flag relative, not absolute. Either
`intra_cluster_mean / merge_threshold > 0.8`, or use silhouette width and flag
the bottom-quartile clusters, or simply flag the *three* highest-variance
clusters regardless of absolute value so the instructor gets a bounded,
prioritized list. Tune on SP26 data; do not ship asserted constants.

### 1.6 The document conflates students and submissions, and every quantitative claim inherits it

`--type team-best` is the primary use case, but the spec says "50 submissions,"
"50 PRs," `ASSESSMENT-001`–`ASSESSMENT-050`, and estimates 2–6 hours for Phase 1
(line 272), with "Phase 1 (50 PRs, 2-6 hours)" and "Phase 3 (50 PRs, 1-3 hours)"
in the turnaround model (lines 894–896).

For a team assignment there are ~12–16 submissions, not 50. Which means:

- Phase 1 is closer to **1–1.5 hours**, not 2–6.
- The issue pool is ~85 strings, not the stated 150–200 — changing what 5–15
  clusters means and how the distance threshold should be tuned.
- Suppression prevalence math (§1.3) is stated in the wrong units.
- The ID space and the throughput model describe a workload that only occurs for
  individual assignments, which are deferred to v3 (C291 support).

Every quantitative claim in the design is expressed in the units that do not
apply to the main assignment type. Fix the units before anyone implements
against them; state both cases explicitly where they differ.

### 1.7 Confidence is self-reported and uncalibrated; the config key is backwards

Thresholding on a 4-bit local model's self-assessed confidence assumes
calibration you have no evidence for. In practice models rarely emit `low`, so
the filter drops almost nothing — while the precision target (≥80%) is *defined
after* the filter, making the headline acceptance number depend on an unvalidated
control.

**Fix:** during SP26 validation, record the confidence distribution and compute
precision *per bucket*. If high/medium/low precision comes out at 82/78/75, the
field is noise and should be dropped rather than thresholded. If it comes out at
90/65/40, it is a real control and you can set the threshold from data.

Separately, the config key is a naming bug:

```yaml
drop_below: "low"       # "low" = drop low, keep medium+high
```

Read literally, "drop below low" drops nothing. Someone will implement the
literal reading. Rename to `min_confidence: "medium"`.

### 1.8 `team_commit_share` reintroduces the participation judgment v4 claims to have removed

v4 changelog item 1 states the fix as "deterministic counts from Pass 1b ... No
LLM judgment about participation." But `team_commit_share: 0.25` in a TA-facing
artifact **is** a participation judgment. It has been laundered into a number,
which makes it look more authoritative than the hedged LLM prose it replaced.

The v2 review's actual finding (§1.4, item 1) was that commit attribution is
unreliable *by default*: pair programming, wrong `git config user.email`, one
member pushing for a teammate with a dead laptop, squash merges destroying
authorship, GitHub web-edit commits, org membership problems. Determinism fixes
none of these. It makes the wrong number reproducible.

The specific killer: if the course teaches squash-merge PR workflows — and SE1
plausibly does — `commits_attributed` on the merged branch is close to
meaningless, and `team_commit_share` computed from it is actively misleading.

**Fix:**

- Drop `team_commit_share`. A raw count invites less over-reading than a
  normalized share that looks like a contribution percentage.
- Print the known failure modes **in the TA-facing artifact itself**, adjacent to
  the numbers — not in the design doc, where no TA will read them.
- Have Pass 1b detect and report the conditions that invalidate the counts
  (squash-merged PR, single-author history with `Co-authored-by` trailers, commits
  from an email not in the roster mapping) rather than silently producing a
  number computed over them.

### 1.9 Injection suppression is under-mitigated and the stated mitigation is circular

The spec's mitigation for suppression attacks is: "If a TA guide is suspiciously
thin, the TA does their own assessment."

This requires the failure to be visible, and it degrades exactly as the tool
succeeds. After 49 accurate guides, a TA under deadline pressure will not treat
the 50th thin one as suspicious — that is what reliance means. The claim "the
pipeline cannot *cause* a bad grade — it can only fail to *help*" also
understates it: `intervention_level: none` actively directs TA attention away
from that submission.

**Two cheap deterministic controls, both roughly ten lines, neither present:**

1. **Anomaly routing.** Any assessment with zero or near-zero issues after
   verification and thresholding is flagged and routed to the same human queue as
   pre-flight failures. Empty output becomes a visible event rather than a quiet
   one.
2. **Pre-flight injection scan.** Grep student-authored content for
   injection-shaped strings (`ignore previous instructions`, `AUTOMATED GRADER`,
   `system prompt`, `disregard the rubric`) and flag those submissions for manual
   review before any model sees them.

Neither stops a determined attacker. Both convert a silent failure into a visible
one, which is precisely what the advisory-design argument needs in order to hold.

### 1.10 SSH distribution trades a small disclosure risk for a large access-control problem

The TA distribution section rules out email, Slack, and cloud drives, and
prescribes: TAs SSH into the Mac Studio and read their slice.

That means TA shell accounts on the machine holding the **full spool, the
roster, and the ID↔name mapping**. "Secured with filesystem permissions" is doing
enormous unspecified work. Per-TA POSIX isolation on a shared macOS box, over a
tree at `~/.local/share/submission_pipeline/` owned by the instructor, is fiddly
to get right, easy to get silently wrong, and has no audit log and no revocation
story when a TA leaves mid-semester.

The blanket rejection of cloud storage is also overbroad: IU has institutional
agreements covering Microsoft 365 and Box, both approved for Restricted data,
both providing per-user ACLs, access logging, and revocation you will not build
yourself. That is a stronger control than hand-rolled file permissions, not a
weaker one.

**Fix:** ask the data steward which institutional storage is approved for
Restricted data — the same one-email question already flagged for the cloud
provider — and prefer an institutionally-managed share with per-TA ACLs. If SSH
stays, specify the account model: separate accounts, a group per TA, mode 0700 on
the output root, slices written 0640 to the TA's group, and the spool/roster/ID
map outside any path a TA account can traverse.

### 1.11 The turnaround comparison is apples-to-oranges

"Total: ~1 day from deadline to TA guides. This must beat the current turnaround
(3-5 days)."

The 3–5 day baseline is deadline→**grades returned**. The ~1 day figure is
deadline→**TAs start work**. The pipeline does not shorten the TA grading pass;
it changes what TAs do during it. It also omits the human handling of the 10–20%
not-assessable submissions, and it budgets the instructor gate at 30–60 minutes,
which will realistically run 2–3 hours on first use — with the whole pipeline
blocked behind it.

**Fix:** compare like with like, or drop the speed claim and lead with
consistency, which the document already (correctly) identifies as the more
defensible benefit.

### 1.12 Validation is under-powered and single-annotator

Ten PRs at ~6 issues each is ~60 judgments. An 80% precision estimate on 60
judgments carries roughly ±10 points at 95% confidence — which cannot
distinguish two candidate models, and the plan calls for comparing two or three.

Worse, step 1 has "a TA or the instructor" produce the blind ground truth, and
the same person then scores the pipeline's output. That is the same person
defining what counts as a real issue and adjudicating the pipeline's extra
findings — the confirmation bias the section warns against two paragraphs later.

**Fix:**

- 20–25 PRs if the SP26 data supports it.
- Separate the roles: one person labels blind, a different person adjudicates
  pipeline output. If only one person is available, blind-mix human-found and
  pipeline-found issues into a single shuffled list and adjudicate without
  knowing the source.
- **Pre-register the adjudication rule** for pipeline-found issues the labeler
  missed. Those are the ambiguous ones, and they decide the precision number.
  Without a written rule, precision is whatever mood the adjudicator is in.

---

## 2. Still unaddressed from the v2 review

- **The MoE throughput recommendation** (v2 §3.1). The v2 review suggested a
  30B-A3B MoE for substantially better throughput on Apple silicon. v4's config
  pins a dense 32B and the recommendation vanished without discussion. On this
  hardware that is plausibly the difference between a 2-hour and a 40-minute
  Phase 1 — which matters more now that the design is committed to an overnight
  batch model.
- **Encryption at rest** (v2 §1.3). You got retention and a hand-wave at
  permissions. FileVault state on the Mac Studio is not mentioned, and neither is
  Time Machine, which will copy the retained spool to whatever it backs up to.
  The v3→v4 move to `~/.local/share/` does resolve the iCloud sync concern by
  construction — worth stating so, since it was raised.
- **Spec-to-code ratio** (v2 §2.4). v2 was 640 lines for a ~600-line program. v4
  is 1,066 lines and the v1 build list *grew*: pre-flight validator, typed
  evidence verification, git provenance extraction, roster mapping build,
  embeddings, agglomerative clustering, matrix authoring, per-TA slicing,
  suppression, content-hash caching, resume, egress chokepoint plus tests. Risk
  went down; parts count went up. This is still being built during the semester.
- **Prompts for Pass 3 and matrix-naming** (v2 §2.5). The v2 review's claim was
  that the prompts are the entire product. v4 wrote one, for Pass 1a. The
  matrix-naming prompt determines whether clusters get split correctly — the
  thing the instructor gate is supposed to catch. Pass 3's prompt produces the
  artifact TAs actually consume.
- **Member ID randomization.** `ASSESSMENT-001`–`050` is correctly randomized per
  §99.31(b)(2). `TEAM-001-MEMBER-1` is sequential within team and nothing states
  it is permuted. If it follows roster or commit order, it is derived from
  student information — the identical finding, unapplied one level down.

---

## 3. Internal inconsistencies to fix before implementation

- **Line 478 contradicts line 503.** The assessment schema contains
  `"branches_created": ["feature-branch-name"]`, while the Key Changes note says
  "`pr_url` and `branches_created` with usernames are kept in a local-only side
  table, never in the assessment JSON." This is the exact leak the v2 review
  caught in v2's own illustration (`mission_statement_jsmith`) — reintroduced in
  the schema that was supposed to fix it. Branch names carry usernames by
  convention; keep names in the side table and put a count in the schema, as the
  TA guide schema already does at line 539.
- **Line 842 vs line 240.** CLI shows `--type team-best|individual`; the text
  defines three types including `team-collaboration`.
- **Line 871.** "all model inference for Passes 1a, 1b (script), and 3" — 1b has
  no model inference.
- **Line 783: `mlx-community/Qwen3-32B-Coder-4bit`** is almost certainly not a
  real model ID. Qwen3-Coder shipped as 30B-A3B and 480B; the dense 32B coder is
  Qwen2.5-Coder-32B-Instruct. Verify before pinning — and see §2 on the MoE.
  Verify `mlx-community/all-MiniLM-L6-v2` exists as well.
- **Line 799: `claude-sonnet-4-20250514`** is two generations stale as of this
  document's date. Current is the Claude 5 family (`claude-sonnet-5`,
  `claude-opus-5`).
- **Audit example vs Phase 2 text.** The audit object pins
  `embedding_model: all-MiniLM-L6-v2` while Phase 2 recommends considering
  `bge-small-en-v1.5` for its 512-token window and better code handling. Pick
  one, or mark the audit value clearly as a placeholder.

---

## 4. Priority order

1. **Typed evidence with per-type verifiers** (§1.1). Without this the pipeline
   cannot report the issues that matter most.
2. **Suppression unit → teams for team assignments** (§1.3). This is the one
   FERPA regression in v4.
3. **Specify evidence canonicalization and test it** before using pass rate as a
   model signal (§1.2).
4. **Fix the students/submissions conflation** throughout, and restate all
   quantitative claims in the right units (§1.6).
5. **Opaque stable matrix IDs** and suppressed-citation handling in Phase 4
   (§1.4).
6. **Drop `team_commit_share`; surface attribution failure modes in the TA
   artifact** (§1.8).
7. **Anomaly routing for near-empty assessments + pre-flight injection grep**
   (§1.9). Ten lines each, converts silent failures to visible ones.
8. **Relative split-flag threshold** for clustering (§1.5).
9. **Rename `drop_below` → `min_confidence`; measure per-bucket precision during
   validation** (§1.7).
10. **Resolve TA distribution with the data steward** rather than defaulting to
    SSH accounts on the machine holding everything (§1.10).
11. **Two-annotator validation with a pre-registered adjudication rule** (§1.12).
12. **Write the Pass 3 and matrix-naming prompts** (§2).
13. Fix the schema/CLI/model-ID inconsistencies in §3.
14. Randomize member IDs (§2).

---

## 5. Verdict

The architecture is now right. The v2 review's central claim — that the FERPA
boundary was a lot of machinery protecting the weakest justification for a cloud
call — was accepted and acted on, and the design is materially better for it.

The remaining defects are implementation-level, but two of them are the kind that
look fine in a spec and fail quietly in production: absence issues disappearing
from the output, and a suppression threshold that passes on a single team. Both
are cheap to fix now and expensive to discover in Week 6.

The v2 review's assessment of the single biggest risk still stands and is
unchanged by anything in v4: **precision, not FERPA.** Everything above is in
service of it — typed evidence, calibrated confidence, honest validation — or in
service of not creating an unrecoverable human problem while chasing it.

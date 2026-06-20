# POST-MORTEM ANALYSIS ROUTINE (Opus analysis-to-promotion pipeline)

The standing routine for turning each slate's post-mortems into tracked
candidate method changes and promotion recommendations. Mark (owner) approves
every promotion — the analysis step NEVER edits method docs on its own.

To run: ask Opus to "run the post-mortem analysis routine for <date>" (or the
`/analyze-postmortems` command once enabled). Follow the steps below.

## Inputs

- **Target date:** a slate date `YYYY-MM-DD`. Default to the most recent dated
  folder under `picks/mlb/`.
- **Active models ONLY:** read `docs/model_roster.md` → MLB section. Ignore
  deprecated V1 legacy models (fable, manus, chatgpt5.5, gpt-5.2-high) even if
  stale files exist on disk.

## Steps

1. **Read the slate post-mortem** — `picks/mlb/<date>/post_mortem_<date>.txt`
   (combined file, all models). If absent, stop and report.

2. **Extract per-model S4 proposals and S3 data requests.** A valid candidate is
   a change to how the model weighs/interprets data it ALREADY receives — NOT a
   request for new data (that is an S3 item) and NOT a rewrite of a fixed
   competition rule (slate ceiling, edge gate, unit map, anti-hindsight — these
   are off-limits → log as REJECTED with the reason).

3. **Check anti-hindsight integrity.** If an S4 cites a game OUTCOME as evidence
   ("X won, so..."), flag it. It may still be logged, but mark the evidence as
   outcome-biased.

4. **Update per-model candidate logs** — append to
   `picks/candidates/candidate_changes_<model>.md` in the existing format.
   READ the file first and check whether the theme already appears:
   - New theme → `## CANDIDATE (building) — <date>. <summary>. Status: first
     observation, needs recurrence or CLV confirmation before promotion. NOT
     adopted.` + the proposal text.
   - Recurring theme → append a dated recurrence note ("recurs <date>, now seen
     Nx") and update the status line; do not duplicate the block.
   - Off-limits / invalid evidence → `## REJECTED — <date>.` with the reason.

5. **Note cross-model convergence** — 2+ models filing the same theme on one
   slate is a stronger promotion signal.

6. **Produce a PROMOTION RECOMMENDATION list** (in the reply, NOT in method
   docs). PROMOTE candidates that meet criteria — recurred across slates OR
   cross-model convergence OR CLV confirmation — with model, change, target
   version `method_<model>_v<N+1>.md`, and evidence trail. Everything else =
   STILL BUILDING with what it waits on.

7. **Stop for owner review.** Present recommendations. Only after Mark agrees:
   edit the method doc (new version, never overwrite) AND append the decision to
   `docs/promotion_log.md`.

## Promotion criteria (the gate)

A candidate is eligible for a PROMOTE recommendation when at least one holds:
- It has recurred across 2+ slates, OR
- 2+ models independently converged on the same theme, OR
- Closing-line-value data confirms the edge it targets.

One slate alone is never enough — that is the anti-hindsight trap.

## Outputs

- Per-model entries appended to `picks/candidates/candidate_changes_<model>.md`
- Promotion decisions (after owner sign-off) in `docs/promotion_log.md`
- New method versions in `docs/methods/` only after approval

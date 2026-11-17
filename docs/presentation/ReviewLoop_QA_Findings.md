# ReviewLoop: live QA findings

Inspected 17 November 2026. All four live sections opened successfully without authentication. Source: https://reviewloop-demo-264.streamlit.app/ and https://github.com/devaki264/reviewloop.

## What works

| Test | Observed result |
|---|---|
| Five-character seeded deck | All five synthetic text briefs and expert reviews displayed. No actual character artwork is inspected. |
| Aster Bloom, rubric v1 | Needs revision: generic praise lacks specificity and actionability. |
| Kite Ren, rubric v1 | Accepted: critique contains specific cues and actionable changes. This does not verify the truth of visual claims. |
| Mirei Echo, rubric v1 | Needs revision, including originality; feedback duplicates Aster's. |
| Same synthetic review under v1 and v2 | Review ending “I give it 8/10.” passed v1, then failed v2 for rating justification. |
| Reviewer disagreement | A v2 false acceptance was overridden to revision_needed; rating_justification was saved with the original recommendation in correction history. |
| Rubric change | v2 activation and approval event were recorded. |
| Manual Improvement loop | Two cycles completed. Both recorded baseline 0.2 and adapted 0.2 exact-match accuracy, zero promotions and zero validated adaptation examples. |

The cycle metric concerns five synthetic **design-description** holdout cases, not expert-review QA. Twenty percent means one of five exact label-set matches. It is not a production benchmark or evidence of learning.

## Important implementation gaps

1. **Rating justification is a shallow heuristic.** “I give it 8/10 because that score feels right to me” passes v2 despite failing its intended evidence requirement. The rule looks for a reason marker after a recognized score; it does not assess whether the evidence supports that score. Some numerical formats can also evade the score pattern.
2. **Stored corrections do not train or update the review-QA auditor.** Its recommendations use text, rubric version, and prior feedback for duplicate detection. Correction history is not a learning input.
3. **Validation status can disagree with the reviewer override.** The save path derives its validated flag from automatic checks rather than the final human QA verdict. A false acceptance rejected by a reviewer can therefore remain marked validated for retrieval. This is a code-supported risk, not a measured production incident.
4. **The improvement experiment is separate from expert-review QA.** It uses design-label predictions and simulated reviewers. Simulated rows are excluded from the validated-majority adaptation path. The UI marks a submission reviewed after one saved review, while majority adaptation expects at least two eligible reviews.
5. **Repeated cycles do not drain the queue.** Cycle-generated reviews are simulations and do not mark submissions reviewed; the oldest pending cases can be processed repeatedly. Two live cycles added 30 simulated review rows, with the queued count still 10.
6. **The rubric update is predefined.** Activating the supplied proposal enables the implemented rating rule; this does not demonstrate arbitrary plain-English policy compilation.
7. **The audit checks the feedback text.** Separate strengths/weaknesses fields and the truth of visual claims are not verified. Some seeded numeric metadata differs from the score written in the feedback; the presentation avoids treating those numbers as ground truth.
8. **Correction rationale is limited.** The UI stores verdict, violation tags and submitted feedback; it does not provide a separate detailed reviewer-rationale field.

## Not verified or not demonstrated

- A persistent deployed worker running independently of the UI. `worker.py` exists, but an always-on process was not established.
- Durable storage across hosting restarts or redeployments. The app uses SQLite; no restart was performed.
- Improvement on unseen expert-review cases, reduced false approvals, reduced review time, or customer impact.
- Continuous learning from adjudicated corrections and the complete action → measurement → adaptation → validation → repetition loop.

## Test footprint and reproducibility

No reset, deletion, repository edit, or deployment was performed. Existing reviews were preserved. Authorized synthetic demo actions left rubric v2 active, one new Lumen Vale submission (ID 16), one saved reviewer override, one rubric event, and two cycle records. The reviewer persona Avery was selected by the QA tester; this is a workflow demonstration, not an independent human-participant study.

Lumen Vale feedback used for v1/v2 comparison:

> The cape silhouette is distinct and the teal palette supports the courier identity. Simplify the collar to improve readability. I give it 8/10.

For the false-acceptance test, the last sentence was changed to:

> I give it 8/10 because that score feels right to me.

Repository's five supplied unit tests passed. Additional cycle checks used an isolated temporary SQLite database. Live tests and local tests are distinct; local v1 cycle results are not used as live performance claims.

Source snapshots: app.py SHA `833b289651b1e7d37caba251271f1d1b6375905e`; engine.py SHA `66499ae26d2faf10604ba273a432bec426b7f254`.

## Pitch guidance

Lead with the contributor's wait for feedback. Use Aster versus Kite to explain what the product evaluates. Use the false acceptance and saved override as the honest technical centerpiece. Describe measured cycle results plainly and pitch the learning loop as the next milestone. Personal Handshake AI and Mercor observations are motivation, not verified company-wide statistics.

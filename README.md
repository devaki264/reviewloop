# ReviewLoop

ReviewLoop is a prototype for automating the review of expert submissions. The goal is to learn how experienced reviewers decide which submissions to accept or send back, then use those decisions to speed up routine reviews and reduce the backlog.

## From submission to decision

An expert submits work. A reviewer decides whether it meets the rubric. In the SundAI demo, the expert’s submission happens to be a written design critique. For example, Aster’s critique gives the design a score and calls it polished. Kite’s identifies a specific problem with the silhouette and suggests a change. ReviewLoop flags Aster’s submission for revision and recommends accepting Kite’s.

The prototype makes a first-pass recommendation using rubric rules, shows the text behind a flag, and lets a human override the result. It records both the recommendation and the final decision. Learning from those decisions is the next step for this queue. Today, saving a correction does not change how the next expert submission is scored.

To test whether this helps clear a backlog, the next evaluation should compare assisted and manual review on held-out submissions. Measure reviewer minutes per submission, submissions cleared per hour, and how often work is accepted when an experienced reviewer would send it back. Backlog reduction is a product goal and has yet to be measured.

## SundAI presentation and live demo

[Open the live app](https://reviewloop-demo-264.streamlit.app/)

The 11-slide pitch from the November 15, 2026 SundAI hackathon at MIT uses authentic application screenshots, conversational speaker notes, and live QA findings from **17 November 2026**.

| Resource | Download |
|---|---|
| Editable PowerPoint with speaker notes | [Presentation](docs/presentation/ReviewLoop_SundAI_Final_Refined.pptx) |
| PDF presentation backup | [PDF](docs/presentation/ReviewLoop_SundAI_Final.pdf) |
| Authentic application screenshots | [Screenshots ZIP](docs/presentation/ReviewLoop_Real_Screenshots.zip) |
| Slide-by-slide speaking script | [Speaking script](docs/presentation/ReviewLoop_Speaking_Script.md) |
| Verified behavior, limitations, and test footprint | [QA findings](docs/presentation/ReviewLoop_QA_Findings.md) |

**What the live demo demonstrated:** Aster's generic feedback was flagged, Kite's actionable critique was accepted, rubric v2 added a rating-justification check, and a human override was saved after that heuristic falsely accepted a weak explanation.

**Separate learning experiment.** A second workflow retrieves similar, previously reviewed synthetic design descriptions. In two manual cycles, baseline and adapted exact-match accuracy both stayed at 20%, so neither candidate was promoted. This experiment measures design-description predictions. The expert-submission queue still uses the rubric checks described above.

## Quick start

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the address Streamlit displays (normally http://localhost:8501).

To keep processing automatically, run this in a **second terminal**:

```bash
python worker.py --interval 60
```

The worker persists history in `reviewloop.db` (created on first run). Existing databases are retained; schema changes for QA verdicts are additive. Use the app's **Run cycles** to demonstrate the separate design-description improvement loop. Rubric v2 is activated explicitly via the Rubric Manager tab.

## Review QA demo behavior

- The active official rubric checks feedback specificity and actionability, and detects repeated feedback. Version 2 adds an explicit numeric-rating justification requirement.
- The AI recommendation is computed from each submitted feedback text and the active rubric. A human can override the recommendation; both recommendation and final verdict are recorded.
- The five seeded outcomes are: Aster Bloom — **Needs revision**; Kite Ren — **Accepted**; Mirei Echo — **Needs revision**; Obsidian Wren — **Accepted**; Sora Vanta — **Accepted** unless an active rubric violation is found in the written feedback.
- Flagged QA violations display their exact supporting text. Artwork shortcomings do not count as reviewer violations.
- No image input is provided, so the demo does not claim to have visually verified any artwork or the expert's visual claims.

## Honest MVP limitations

- Expert-review QA checks and design-description checks are rule-based heuristics, **not an LLM**. The separate design improvement loop uses TF-IDF similarity to historically reviewed cases with a conservative threshold. It does not retrain model weights.
- Four named reviewers are **simulated** with an explicit error rate; they are not human experts. Human correction is supported through the interface.
- The demonstration's synthetic ground truth is embedded in the seeded cases and should not be treated as unbiased evidence of quality.
- Improvement is **not guaranteed**. Promotion occurs only if a candidate beats the baseline on a fixed, separate synthetic holdout set. This limited gate is not sufficient to prove production readiness.
- User-authored submissions are flagged for human review and are never automatically assigned synthetic ground truth.
- Rubric version change is a predefined v1→v2 expert-review rule addition with human approval, not a free-form language parser.
- Deployment requires a persistent SQLite volume and a separate scheduled worker; Streamlit alone does not provide always-on autonomous operation. Egbe integration should be verified against available capabilities.

## Development priorities

1. Connect historical reviewer decisions to the expert-submission queue and compare its recommendations with a rubric-only baseline on held-out work.
2. Add a plain-language rubric change proposal parser with approval and versioned diffs.
3. Replace simulated reviewer votes with real, consented, non-confidential human feedback.
4. Improve evaluation: sealed holdout by rubric version; metrics for false approvals, reviewer minutes, disagreement, and calibration.
5. Deploy Streamlit and schedule `worker.py` with a reliable job service, perhaps using Egbe if supported.

# ReviewLoop

I built ReviewLoop on November 15, 2026, at MIT as part of a SundAI hackathon. The idea came from my experience as an expert on Mercor and Handshake AI, two AI training platforms. On some projects I worked on, every expert submission had to wait for a manual review before it could go to the client, typically a frontier AI lab. When submissions piled up, even routine decisions could hold up delivery. I wanted to see whether a system could learn from the decisions reviewers were already making and help them work through that backlog faster.

## The problem

When an AI team asks domain experts to evaluate work, each expert’s write-up becomes another piece of work someone has to review. An expert might submit a rating and an explanation. Before the team can use that submission, a reviewer has to read it, check it against the project’s criteria, and decide whether to accept it or ask the expert for a revision.

When submissions come in faster than reviewers can clear them, experts wait for feedback and the team waits for usable work. Even a familiar issue, like a rating with no explanation, takes another reviewer’s time to catch. Earlier decisions contain examples of what the team accepts and what it sends back. ReviewLoop grew out of a question: could those decisions teach a system to handle recurring cases and leave reviewers more time for difficult ones?

## How the prototype works

ReviewLoop gives the reviewer a first pass on an expert’s submission. The demo uses fictional written critiques of character designs. The expert’s job is to critique the design. The reviewer’s job is to decide whether that critique meets the project’s requirements. ReviewLoop helps with this second job.

For example, one sample submission ends with “I would give it an 8/10. Great job overall.” A reviewer looking for feedback the designer can act on would have to send that back. ReviewLoop flags the generic critique for revision. Another sample explains that the waistline is hard to distinguish and calls for a clearer stance. ReviewLoop recommends accepting that critique because it identifies a problem and gives the designer a concrete change to make.

The prototype checks the submitted text against rules for specificity, actionable feedback, and repetition. A reviewer can activate a second rubric version that also checks whether the expert justified their rating. The app shows the text behind a flag and records both its recommendation and the reviewer’s final decision. The reviewer can override a mistake, including a weak explanation that passes the automated check.

[Try the review queue](https://reviewloop-demo-264.streamlit.app/)

## What the demo establishes

The expert-submission queue can apply a consistent first pass and capture human corrections. Its recommendations currently come from rubric rules. Saving an override preserves an example for future learning, but it does not yet change the next recommendation.

The app also includes a separate experiment on synthetic design descriptions: it retrieves similar previously reviewed cases and tests whether they improve predictions. In two recorded runs, accuracy on held-out examples stayed at 20% with and without retrieval. The demo uses synthetic data and has yet to measure time saved or backlog reduction in a working review queue.

## Where this goes next

1. **Learn from actual review decisions.** Collect permissioned examples of submissions, the rubric in effect, and reviewers’ final decisions. Test whether past cases help the system handle a new submission more reliably than the current rules alone.
2. **Identify which decisions can be automated.** Evaluate recommendations on submissions the system has never seen. Track both weak work it would accept and good work it would send back unnecessarily. Use those results to decide which recurring cases can move automatically and which need a reviewer.
3. **Test whether the queue actually moves faster.** Compare manual and assisted review on comparable batches. Measure reviewer minutes per submission, time from submission to decision, and outstanding backlog alongside decision quality.

## Run locally

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell users can activate with .venv\Scripts\Activate.ps1 instead
pip install -r requirements.txt
streamlit run app.py
```

Open the local address printed by Streamlit. Review history is stored in `reviewloop.db`. To run the separate design-description experiment, use **Run cycles** in the app or start `python worker.py --interval 60` in a second terminal.

## Hackathon materials

| Resource | Download |
|---|---|
| Editable PowerPoint with speaker notes | [Presentation](docs/presentation/ReviewLoop_SundAI_Final_Refined.pptx) |
| PDF presentation backup | [PDF](docs/presentation/ReviewLoop_SundAI_Final.pdf) |
| Authentic application screenshots | [Screenshots ZIP](docs/presentation/ReviewLoop_Real_Screenshots.zip) |
| Slide-by-slide speaking script | [Speaking script](docs/presentation/ReviewLoop_Speaking_Script.md) |
| Verified behavior, limitations, and test footprint | [QA findings](docs/presentation/ReviewLoop_QA_Findings.md) |

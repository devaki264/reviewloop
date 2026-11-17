# ReviewLoop speaking script

Approximately 5–6 minutes. Speaker notes are also embedded in the PowerPoint.

## Slide 1

Imagine spending an hour evaluating an AI response, submitting it, and only later finding out that your explanation missed the rubric. That delay is what got me interested in this problem. I built ReviewLoop to check expert feedback earlier and keep the reviewer in control. Today I can show a real, rule-based prototype. The larger learning loop is the next step. Let me first explain where it fits.

## Slide 2

A lab defines a task and a rubric. An expert writes an evaluation or critique. A QA reviewer checks whether that work meets the standard before it goes downstream. The expert and the QA reviewer are doing different jobs. When submissions wait in that third stage, avoidable mistakes take longer to correct. ReviewLoop's hypothesis is that an earlier check can help, while reviewers still make the final decision.

## Slide 3

I've worked as a contributor on Handshake AI and Mercor. At Handshake, I encountered automated auditing capabilities. At Mercor, I experienced delays before reviewer feedback came back. Those are my own observations, not company-wide statistics. The product question I wanted to test was simple: can I give experts useful feedback sooner and leave QA reviewers more time for cases that need judgment?

## Slide 4

To make that concrete, I used five fictional anime character designs. These are text briefs with synthetic assessments, not images the app has inspected. The distinction is in the two right-hand columns: a design can be accepted while the review needs revision. A flawed design can also receive a useful review. I'll show Aster and Kite because they make that distinction very clear.

## Slide 5

Aster's feedback says the character is strong and polished, but it doesn't explain what supports that judgment or what to improve. ReviewLoop asks for revision. Kite's critique names problems with the lower-body silhouette and the stance, then proposes changes. That review passes even though the fictional design has flaws. These screenshots are real app outputs. Passing means the text cleared these prototype checks, not that its visual claims are true.

## Slide 6

Here is the more interesting failure. This review includes specific details and a next step, then says eight out of ten because that score feels right. The v2 heuristic accepts it. During QA testing, we used the reviewer override to mark it needs revision and tagged rating justification. The log preserves both decisions. This is why writing a rubric is not enough: the checker still has to interpret evidence correctly. Also, saving that correction does not mean the system has learned from it.

## Slide 7

Version one checks specificity, actionability, and originality. Version two adds score justification. We tested the same review ending in I give it eight out of ten. It passed v1 and failed v2. So the version change genuinely affects recommendations. But this is a predefined rule addition with approval, not a system that can implement any policy written in English. And the previous slide shows that the new heuristic can still miss a weak explanation.

## Slide 8

I also ran the Improvement loop twice. It recorded results, but baseline and adapted exact-match accuracy stayed at twenty percent on five synthetic design cases. No candidate was promoted. Crucially, this is a separate design-description experiment, not a measurement of expert-review QA. I would not pitch it as self-improvement. The useful result is that the measurement interface exists and the test exposes the work still needed.

## Slide 9

The MVP demonstrates a synthetic review queue, explainable rule-based recommendations, saved reviewer decisions, and a versioned rubric change. It does not yet demonstrate QA learning from corrections or improvement on unseen expert reviews. It doesn't inspect artwork, and we haven't verified an always-on worker or durable production hosting. That is the honest boundary of this build. The next slide is the loop I want to complete.

## Slide 10

The next loop would act on a new review, measure agreement against adjudicated human feedback, propose a change, and validate that change on unseen reviews for that rubric version. Only a candidate that improves the chosen quality measures would be promoted, then tested again on the next batch. That could support earlier pre-submission feedback and better reviewer prioritization. This is planned architecture, not a completed result.

## Slide 11

To know whether this is worth using, I'd measure time to useful feedback, false approvals, and reviewer minutes per resolved submission. The hypothesis is that catching avoidable problems earlier reduces waiting without lowering the quality bar. There are no measured savings yet. What I want to build toward is this: every correction should make the next review easier to get right.

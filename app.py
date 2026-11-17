import json

import pandas as pd
import streamlit as st

from engine import (
    DB,
    RULES,
    REVIEW_RULES,
    REVIEWERS,
    add_submission,
    audit_expert_review,
    connect,
    create_review,
    cycle,
    current_version,
    feedback_quality_flags,
    get_config,
    get_design_deck,
    get_design_rubric_summary,
    get_rubric_summary,
    init,
    majority_labels,
    predict,
    record_human_correction,
    reset,
    retrieve_validated_examples,
    update_rubric,
)

EXPERT_REVIEWS = {
    1: {
        "rating": 8.2,
        "strengths": [
            "The shrine-guardian silhouette is readable and memorable.",
            "The coral-and-jade color story supports the warm, protective mood.",
            "The kneeling pose feels calm and inviting without drifting into stiffness."
        ],
        "weaknesses": [
            "The collar framing could be slightly sharper to preserve silhouette clarity in a thumbnail.",
            "Some costume layers compete for attention near the neckline.",
            "The expression reads as friendly, but a touch more tension would sharpen character intent."
        ],
        "feedback_text": "This is a very strong character. The concept is appealing and the visual style feels polished. I would give it an 8/10. Great job overall.",
    },
    2: {
        "rating": 6.4,
        "strengths": [
            "The street-racer identity is clear from the jacket silhouette and orange-and-charcoal palette.",
            "The overall mood reads as energetic and dramatic.",
            "The palette gives the design a strong visual anchor."
        ],
        "weaknesses": [
            "The waistline and boots blur into a single mass, reducing legibility.",
            "The pose lacks a firm center of gravity and feels rushed.",
            "Facial features and costume transitions could better support clarity at small size."
        ],
        "feedback_text": "The concept is strong, but the silhouette gets messy in the lower body and the pose feels unstable. I would mark this as a 6.5/10 because the costume has too much visual clutter and the face is not as legible as it should be. The design needs a cleaner line for the waist and a clearer stance before it works as a marketable character sheet.",
    },
    3: {
        "rating": 8.1,
        "strengths": [
            "The character feels polished and composed with a strong profile silhouette.",
            "The violet-and-silver palette communicates elegance without becoming muddy.",
            "The cape and standing pose add stage presence while keeping the design readable."
        ],
        "weaknesses": [
            "A little more contrast in the cape edge would help the silhouette read even more clearly.",
            "The expression is elegant but could carry a small hint of drama for stronger character intent.",
            "Some secondary accessories could be simplified to reduce visual noise."
        ],
        "feedback_text": "This is a very strong character. The concept is appealing and the visual style feels polished. I would give it an 8/10. Great job overall.",
    },
    4: {
        "rating": 4.6,
        "strengths": [
            "The dark mood and sentinel identity are legible on a first pass.",
            "The metal armor texture suggests a strong world-building direction.",
            "The silhouette does communicate a heavy armored presence."
        ],
        "weaknesses": [
            "The palette shifts between blue, red, and gold without a clear hierarchy.",
            "The eye shapes are mismatched, which makes the expression uneasy and inconsistent.",
            "The pose collapses into chaotic motion rather than a stable or threatening stance."
        ],
        "feedback_text": "The design has a strong mood and a believable armored silhouette, but the color story is too chaotic and the face does not support the intended menace. I would score it 4.5/10 because the pose and expression feel inconsistent and the costume needs simplification. The character could work if the palette is narrowed to one dominant hue, the eye shapes are unified, and the stance is made more deliberate.",
    },
    5: {
        "rating": 7.3,
        "strengths": [
            "The moonlit scout concept is evocative and visually distinct.",
            "The hair rhythm gives the silhouette strong motion and identity.",
            "The soft pastel palette supports the nighttime mood."
        ],
        "weaknesses": [
            "The hands disappear into the costume, limiting readability.",
            "The expression feels muted and the pose is static instead of tactical.",
            "Some silhouette edges blur, which weakens the read at small size."
        ],
        "feedback_text": "The design has a compelling mood and a memorable hair silhouette, but the athlete pose does not feel confident enough and the face loses clarity in a thumbnail. I would rate it 7.3/10 because the costume and pose need a stronger stance, clearer hands, and more visible expression. This would improve with a more decisive silhouette and a simpler lower-body shape.",
    }
}

st.set_page_config(page_title="ReviewLoop | Expert Review QA", page_icon="🎨", layout="wide")
init()

st.title("🎨 ReviewLoop | Expert Review QA")
st.caption("Synthetic demo for quality-assuring human expert reviews. Character design assessments and expert-review QA are separate; no artwork images are supplied or visually verified.")

with connect() as c:
    version = current_version(c)
    pending = c.execute("SELECT COUNT(*) FROM submissions WHERE reviewed = 0 AND status = 'pending'").fetchone()[0]
    reviewed = c.execute("SELECT COUNT(*) FROM submissions WHERE reviewed = 1").fetchone()[0]
    n_cycles = c.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
    examples = len(majority_labels(c, version))

cols = st.columns(4)
for col, name, value in zip(cols, ["Queued design reviews", "Reviewed submissions", "Improvement cycles", "Validated examples"], [pending, reviewed, n_cycles, examples]):
    col.metric(name, value)

st.info("ReviewLoop evaluates whether written expert feedback follows the active rubric. Design assessments describe seeded opinions about the artwork and never determine the expert-review QA verdict.")

tab1, tab2, tab3, tab4 = st.tabs(["🧠 Review queue", "🧩 Seeded design deck", "📜 Rubric & corrections", "📈 Improvement loop"])

with tab1:
    st.subheader("Human expert review queue")
    with connect() as c:
        version = current_version(c)
        rows = c.execute(
            "SELECT id, body, rubric_version, reviewed, status FROM submissions WHERE reviewed = 0 AND status = 'pending' ORDER BY id LIMIT 100"
        ).fetchall()
        if not rows:
            st.info("No pending design reviews. Add a new submission or reset the synthetic demo.")
        else:
            choices = {f"#{row['id']} · {row['body'][:90]}": row for row in rows}
            selection = st.selectbox("Queued design submission", list(choices))
            item = choices[selection]
            st.write(item["body"])
            st.caption("Text-only design brief. No artwork image is supplied or visually verified.")
            examples = majority_labels(c, version)
            enabled = get_config(c, "adaptation_enabled") == "1"
            issues, mode = predict(item["body"], version, examples, enabled)
            st.write(
                "**Design-description signal (not expert-review QA):** "
                f"{', '.join(issues) if issues else 'No major issues'} · method: `{mode}`"
            )

            examples_for_item = retrieve_validated_examples(c, item["body"], 3)
            if examples_for_item:
                st.caption("Retrieved validated review examples for future matching")
                for example in examples_for_item:
                    st.markdown(
                        f"- Similarity: {example['similarity']} | Labels: {', '.join(example['issue_labels']) or 'none'} | {example['note']}"
                    )

            previous_feedback = [
                review["feedback_text"]
                for seeded_id, review in EXPERT_REVIEWS.items()
                if seeded_id != item["id"]
            ]
            previous_feedback.extend(
                row["note"]
                for row in c.execute(
                    "SELECT note FROM reviews WHERE note IS NOT NULL AND note != '' AND simulated = 0"
                ).fetchall()
            )
            note = st.text_area(
                "Submitted expert feedback",
                value="",
                height=120,
                key=f"review_note_{item['id']}",
            )
            audit = audit_expert_review(note, version, previous_feedback)
            st.markdown(
                "**ReviewLoop expert-review QA recommendation "
                f"(active rubric v{version}; rule-based prototype):** "
                f"{audit['recommendation']}"
            )
            for violation in audit["violations"]:
                st.markdown(f"- **{violation['rule_key'].replace('_', ' ').title()}** — {violation['reason']}")
                st.markdown(f"  - Evidence in submitted text: > {violation['evidence']}")

            with st.form("review_form"):
                reviewer = st.selectbox("Reviewer", REVIEWERS)
                rating = st.selectbox(
                    "Expert's design assessment",
                    ["accepted", "revision_needed", "escalated"],
                )
                chosen = st.multiselect(
                    "Design issues identified by the expert",
                    list(RULES[version].keys()),
                    default=issues,
                )
                qa_verdict = st.selectbox(
                    "Final Expert Review QA (human override)",
                    ["accepted", "revision_needed", "escalated"],
                    index=["accepted", "revision_needed", "escalated"].index(audit["verdict"]),
                    format_func=lambda value: {
                        "accepted": "Accepted",
                        "revision_needed": "Needs revision",
                        "escalated": "Escalated",
                    }[value],
                )
                qa_violations = st.multiselect(
                    "Human-confirmed expert-review rubric violations",
                    list(REVIEW_RULES[version].keys()),
                    default=[item["rule_key"] for item in audit["violations"]],
                )
                submit = st.form_submit_button("Save expert review")
                if submit:
                    flags = feedback_quality_flags(
                        c,
                        note,
                        rating,
                        chosen,
                        version,
                        previous_feedback,
                    )
                    if flags["generic_comment"] or flags["repeated_feedback"] or flags["poor_justification"]:
                        st.warning(
                            "The written feedback has active expert-review rubric violations. "
                            "The human decision will be saved, but this review will not be promoted as a validated exemplar."
                        )
                    else:
                        st.success("Saved as a validated reviewer correction and retrievable future example.")

                    create_review(c, item["id"], reviewer, chosen, note, False, rating, 3)
                    row_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                    validated = 0 if any([flags["generic_comment"], flags["repeated_feedback"], flags["poor_justification"]]) else 1
                    c.execute(
                        "UPDATE reviews SET validated = ?, qa_recommendation = ?, qa_verdict = ?, qa_violations = ? WHERE id = ?",
                        (
                            validated,
                            audit["verdict"],
                            qa_verdict,
                            json.dumps(qa_violations),
                            row_id,
                        ),
                    )
                    record_human_correction(
                        c,
                        item["id"],
                        reviewer,
                        issues,
                        chosen,
                        note,
                        audit["verdict"],
                        qa_verdict,
                        qa_violations,
                    )
                    c.commit()
                    st.rerun()

    st.divider()
    st.subheader("Add a new synthetic design submission")
    body = st.text_area(
        "Paste a fictional anime character-design pitch",
        value="A moonlit shrine guardian with a tapered silhouette, rose-gold palette, clear eye shape, and strong kneeling pose. The costume remains readable at thumbnail size and the mood feels calm and warm.",
        height=120,
    )
    if st.button("Queue new review submission"):
        add_submission(body)
        st.success("New design submission queued for review.")
        st.rerun()

with tab2:
    st.subheader("Five-design synthetic deck")
    st.caption("Design Assessment is seeded synthetic metadata. Expert Review QA is computed from each written critique and the active official rubric; artwork is not visually verified.")
    with connect() as c:
        version = current_version(c)
        deck = get_design_deck(c)
    previous_feedback = []
    for design in deck:
        status = design["status"]
        true_issues = json.loads(design["true_issues"]) if design["true_issues"] else []
        review = EXPERT_REVIEWS.get(design["id"], {
            "rating": 7.0,
            "strengths": ["The concept is clear and consistent."],
            "weaknesses": ["The design needs more precise visual evidence."],
            "feedback_text": "This review is intentionally generic and lacks clear evidence.",
        })
        audit = audit_expert_review(review["feedback_text"], version, previous_feedback)
        previous_feedback.append(review["feedback_text"])
        design_label = status.replace("_", " ").upper()
        with st.container():
            st.markdown(f"### {design['title']}")
            st.write(design["body"])
            st.markdown(f"**Design Assessment:** {design_label}")
            st.caption(
                "Seeded synthetic assessment and design issue labels; not an image-based verification. "
                f"Design notes: {', '.join(true_issues) if true_issues else 'none'}"
            )

            st.markdown("**Fictional expert's stated design rating:**")
            st.write(f"{review['rating']:.1f}/10")

            st.markdown("**Fictional expert's stated strengths:**")
            for item in review["strengths"]:
                st.write(f"- {item}")

            st.markdown("**Fictional expert's stated weaknesses:**")
            for item in review["weaknesses"]:
                st.write(f"- {item}")

            st.markdown("**Fictional expert's feedback text:**")
            st.write(review["feedback_text"])

            st.markdown(
                "**Expert Review QA:** "
                f"{audit['recommendation']} (active rubric v{version})"
            )
            if audit["violations"]:
                st.write("Flagged violations with exact supporting evidence:")
                for violation in audit["violations"]:
                    st.markdown(f"- **{violation['rule_key'].replace('_', ' ').title()}**")
                    st.caption(violation["rule"])
                    st.markdown(f"  - Evidence in submitted feedback: > {violation['evidence']}")
                    st.write(f"  - Why flagged: {violation['reason']}")
            else:
                st.write("No active expert-review rubric violations found in the submitted text.")

            st.markdown("---")

with tab3:
    st.subheader("Official Expert Review QA rubric")
    with connect() as c:
        version = current_version(c)
        current_rules = get_rubric_summary(c)
        st.caption(f"Active version: v{version}")
        for key, value in current_rules.items():
            st.write(f"**{key.replace('_', ' ').title()}** — {value}")
        st.caption(
            "The rubric assesses the written evaluation only. Without image input, ReviewLoop does not "
            "claim to have visually verified any artwork or the truth of visual claims."
        )

    with st.expander("Separate design-assessment criteria (not the active expert-review rubric)"):
        with connect() as c:
            design_rules = get_design_rubric_summary(c)
        for key, value in design_rules.items():
            st.write(f"**{key.replace('_', ' ').title()}** — {value}")

    st.subheader("Human-approved plain-English rubric update")
    st.caption("Human-approved rubric versions and change events are stored in SQLite. The design-assessment labels remain separate.")
    proposal = st.text_area(
        "Plain-English proposal",
        value="Add a rule that every rating must cite at least one specific visual cue, like silhouette, pose, or palette, instead of relying on a vague impression.",
        height=120,
    )
    if st.button("Approve and activate rubric update"):
        result = update_rubric(approver="Demo design manager", proposal=proposal)
        if result:
            st.success("Rubric update approved and activated as the new versioned policy.")
            st.rerun()
        else:
            st.info("The active rubric is already on the latest version for this demo.")

    st.divider()
    st.subheader("Human corrections log")
    with connect() as c:
        corrections = pd.read_sql_query("SELECT * FROM human_corrections ORDER BY id DESC LIMIT 50", c)
        if corrections.empty:
            st.info("No human corrections yet.")
        else:
            st.dataframe(corrections, use_container_width=True)

with tab4:
    st.subheader("Recurring improvement loop")
    st.write("Each cycle processes queued design descriptions, compares design-issue predictions against the synthetic hold-out deck, and records whether example-based adaptation improved results over the baseline. This loop is separate from expert-review QA.")
    num = st.slider("Cycles to execute", 1, 5, 2)
    batch = st.slider("Queued submissions per cycle", 2, 12, 5)
    if st.button("▶ Run design review cycles", type="primary"):
        results = [cycle(batch_size=batch) for _ in range(num)]
        st.json(results)
        st.rerun()

    st.divider()
    with connect() as c:
        cycles = pd.read_sql_query("SELECT * FROM cycles ORDER BY cycle DESC", c)
        reviews = pd.read_sql_query("SELECT * FROM reviews ORDER BY id DESC LIMIT 150", c)
        rubric_events = pd.read_sql_query("SELECT * FROM rubric_events ORDER BY id DESC", c)

        if not cycles.empty:
            st.subheader("Cycle metrics")
            st.dataframe(cycles, use_container_width=True)
            chart_data = cycles.sort_values("cycle").set_index("cycle")[["baseline_accuracy", "adapted_accuracy"]]
            st.line_chart(chart_data)
        else:
            st.info("Run at least one cycle to populate the improvement dashboard.")

        st.subheader("Reviewer records")
        st.dataframe(reviews, use_container_width=True)

        st.subheader("Rubric version history")
        st.dataframe(rubric_events, use_container_width=True)

st.sidebar.header("Demo controls")
st.sidebar.caption("All characters, artwork assessments, and reviewer feedback are synthetic demo data.")
if st.sidebar.button("Reset synthetic demo data"):
    reset()
    st.success("Synthetic ReviewLoop state reset.")
    st.rerun()

st.sidebar.code("python worker.py --interval 60", language="bash")
st.sidebar.caption("The worker can run a recurring loop in a separate process; this UI keeps the end-to-end demo visible and interactive.")

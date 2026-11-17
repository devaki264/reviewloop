import json
import tempfile
import unittest
from pathlib import Path

from engine import (
    REVIEW_RULES,
    audit_expert_review,
    connect,
    current_version,
    init,
    record_human_correction,
    update_rubric,
)


class ExpertReviewQATests(unittest.TestCase):
    def test_generic_feedback_needs_revision_with_exact_evidence(self):
        feedback = (
            "This is a very strong character. The concept is appealing and the visual "
            "style feels polished. I would give it an 8/10. Great job overall."
        )

        audit = audit_expert_review(feedback, 1)

        self.assertEqual(audit["verdict"], "revision_needed")
        specificity = next(item for item in audit["violations"] if item["rule_key"] == "specificity")
        self.assertEqual(specificity["evidence"], "This is a very strong character.")

    def test_specific_actionable_critique_is_accepted_despite_design_flaws(self):
        feedback = (
            "The waistline and boots blur together, reducing legibility, and the pose "
            "feels unstable. The design needs a cleaner line for the waist and a clearer stance."
        )

        audit = audit_expert_review(feedback, 1)

        self.assertEqual(audit["verdict"], "accepted")
        self.assertEqual(audit["violations"], [])

    def test_repeated_feedback_flags_both_exact_submitted_texts(self):
        original = "The concept has a clear silhouette. Narrow the palette to improve readability."
        repeated = "The concept has a clear silhouette. Narrow the palette to improve readability."

        audit = audit_expert_review(repeated, 1, [original])

        originality = next(item for item in audit["violations"] if item["rule_key"] == "originality")
        self.assertIn(f'Current review: "{repeated}"', originality["evidence"])
        self.assertIn(f'Matching review: "{original}"', originality["evidence"])

    def test_version_two_flags_unjustified_numeric_rating(self):
        audit = audit_expert_review("The pose and palette look good. I would rate it 8/10.", 2)

        self.assertIn("rating_justification", {item["rule_key"] for item in audit["violations"]})
        self.assertIn("rating_justification", REVIEW_RULES[2])

    def test_rubric_update_and_human_qa_override_are_persisted_additively(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Path(temp_dir) / "reviewloop.db"
            init(db)

            self.assertTrue(
                update_rubric(
                    db,
                    approver="Demo reviewer",
                    proposal="Every rating should cite a specific visual cue and explain the evidence.",
                )
            )
            c = connect(db)
            try:
                self.assertEqual(current_version(c), 2)
                self.assertIn("rating_justification", REVIEW_RULES[current_version(c)])
                submission_columns = {
                    row["name"] for row in c.execute("PRAGMA table_info(submissions)")
                }
                self.assertIn("body", submission_columns)
                review_columns = {row["name"] for row in c.execute("PRAGMA table_info(reviews)")}
                self.assertIn("qa_recommendation", review_columns)

                record_human_correction(
                    c,
                    1,
                    "Avery",
                    [],
                    [],
                    "Specific feedback with a clear next step.",
                    "revision_needed",
                    "accepted",
                    ["actionability"],
                )
                correction = c.execute(
                    "SELECT qa_recommendation, qa_verdict, qa_violations FROM human_corrections"
                ).fetchone()
                self.assertEqual(correction["qa_recommendation"], "revision_needed")
                self.assertEqual(correction["qa_verdict"], "accepted")
                self.assertEqual(json.loads(correction["qa_violations"]), ["actionability"])
            finally:
                c.close()


if __name__ == "__main__":
    unittest.main()

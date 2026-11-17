"""ReviewLoop MVP: quality assurance for human expert reviews."""
import json
import random
import re
import sqlite3
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DB = Path(__file__).with_name("reviewloop.db")

RULES = {
    1: {
        "silhouette": "Silhouette must read clearly from a distance without fused anatomy or noisy outlines.",
        "color_story": "Palette should communicate identity using a clear dominant hue and supporting accent colors.",
        "readability": "Facial features, costume anchors, and key props must remain legible at small sizes.",
        "expression": "Expression should communicate the character's intent or emotion without visual clutter.",
        "pose": "Pose and gesture should reveal action, confidence, or tension with a clear center of gravity.",
        "consistency": "The visual language across costume, hair, expression, and accessories must feel cohesive.",
    },
    2: {
        "silhouette": "Silhouette must read clearly from a distance without fused anatomy or noisy outlines.",
        "color_story": "Palette should communicate identity using a clear dominant hue and supporting accent colors.",
        "readability": "Facial features, costume anchors, and key props must remain legible at small sizes.",
        "expression": "Expression should communicate the character's intent or emotion without visual clutter.",
        "pose": "Pose and gesture should reveal action, confidence, or tension with a clear center of gravity.",
        "consistency": "The visual language across costume, hair, expression, and accessories must feel cohesive.",
        "evidence": "Every rating must cite at least one specific visual cue or design detail rather than a vague impression.",
    },
}

REVIEW_RULES = {
    1: {
        "specificity": "Feedback must name concrete details from the submitted review rather than rely on generic praise or criticism.",
        "actionability": "When identifying a weakness, feedback must offer a concrete next step.",
        "originality": "Feedback must be tailored to the submission and not copied from another review.",
    },
    2: {
        "specificity": "Feedback must name concrete details from the submitted review rather than rely on generic praise or criticism.",
        "actionability": "When identifying a weakness, feedback must offer a concrete next step.",
        "originality": "Feedback must be tailored to the submission and not copied from another review.",
        "rating_justification": "Every numeric rating must cite at least one specific visual cue and explain its relevance.",
    },
}

_SPECIFIC_REVIEW_CUES = re.compile(
    r"\b(silhouette|outline|palette|color story|hue|accent|waistline|boots?|"
    r"pose|stance|gesture|center of gravity|face|facial|eyes?|mouth|hair|"
    r"hands?|cape|costume|armor|collar|expression|thumbnail|readab|legib|"
    r"contrast|shape|line|lower[- ]body)\b",
    re.IGNORECASE,
)
_ACTIONABLE_LANGUAGE = re.compile(
    r"\b(could|should|needs?\s+(?:a|an|the|to)?\s*\w+|recommend|suggest|would improve|"
    r"simplif\w*|narrow\w*|clarif\w*|sharpen\w*|strengthen\w*|"
    r"unif\w*|add|remove|reduce|focus|make .{1,35} clearer|"
    r"make .{1,35} more)\b",
    re.IGNORECASE,
)

REVIEWERS = ["Avery", "Blair", "Casey", "Drew", "Mina"]

DESIGN_DECK = [
    {
        "id": 1,
        "title": "Aster Bloom",
        "status": "accepted",
        "body": "Aster Bloom is a cheerful shrine guardian with a clear fan silhouette, coral-and-jade palette, expressive eyes, and a calm kneeling pose. The costume layers stay readable at small size and the hair outline remains distinct from the collar.",
        "true_issues": [],
    },
    {
        "id": 2,
        "title": "Kite Ren",
        "status": "revision_needed",
        "body": "Kite Ren is a street racer with a busy jacket silhouette and a faintly readable face. The orange and charcoal palette is dramatic, but the waistline and boots blur together and the pose feels rushed without a clear center of gravity.",
        "true_issues": ["silhouette", "pose", "readability"],
    },
    {
        "id": 3,
        "title": "Mirei Echo",
        "status": "accepted",
        "body": "Mirei Echo is an elegant stage mage with a clean profile, violet-and-silver color story, composed expression, and a balanced standing pose. The cape sits in a single coherent shape and the costume anchors remain visible even in a quick thumbnail.",
        "true_issues": [],
    },
    {
        "id": 4,
        "title": "Obsidian Wren",
        "status": "escalated",
        "body": "Obsidian Wren is a lone sentinel with a dark silhouette, over-saturated accents, mismatched eye shapes, and a pose that collapses into random motion. The armor texture competes with the face and the color story shifts between blue, red, and gold without one clear identity.",
        "true_issues": ["color_story", "expression", "pose", "consistency"],
    },
    {
        "id": 5,
        "title": "Sora Vanta",
        "status": "revision_needed",
        "body": "Sora Vanta is a moonlit scout with a slightly blurred silhouette and a soft pastel palette. The hair has a strong rhythm but the expression is muted, the hands disappear into the costume, and the pose reads as static instead of tactical or confident.",
        "true_issues": ["silhouette", "expression", "pose", "readability"],
    },
]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db=DB):
    con = sqlite3.connect(db, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def _ensure_columns(c, table_name, columns):
    existing = {row[1] for row in c.execute(f"PRAGMA table_info({table_name})").fetchall()}
    for col_name, col_sql in columns.items():
        if col_name in existing:
            continue
        sql = (col_sql or "").strip()
        if "CURRENT_TIMESTAMP" in sql.upper():
            sql = sql.replace("DEFAULT CURRENT_TIMESTAMP", "DEFAULT '1970-01-01T00:00:00+00:00'")
        if "NOT NULL" in sql.upper() and "DEFAULT" not in sql.upper():
            sql = sql.replace("NOT NULL", "").strip()
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {sql}")

        if col_name == "status":
            c.execute(f"UPDATE {table_name} SET status = 'pending' WHERE status IS NULL OR status = ''")
        elif col_name == "created_at":
            c.execute(f"UPDATE {table_name} SET created_at = ? WHERE created_at IS NULL OR created_at = ''", (now(),))
        elif col_name == "rating":
            c.execute(f"UPDATE {table_name} SET rating = 'revision_needed' WHERE rating IS NULL OR rating = ''")
        elif col_name == "confidence":
            c.execute(f"UPDATE {table_name} SET confidence = 3 WHERE confidence IS NULL")
        elif col_name == "validated":
            c.execute(f"UPDATE {table_name} SET validated = 0 WHERE validated IS NULL")


def init(db=DB):
    with connect(db) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY,
                body TEXT NOT NULL,
                rubric_version INTEGER NOT NULL,
                true_issues TEXT NOT NULL,
                reviewed INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                reviewer TEXT NOT NULL,
                issue_labels TEXT NOT NULL,
                note TEXT NOT NULL,
                simulated INTEGER NOT NULL DEFAULT 0,
                rating TEXT NOT NULL DEFAULT 'revision_needed',
                confidence INTEGER NOT NULL DEFAULT 3,
                validated INTEGER NOT NULL DEFAULT 0,
                qa_recommendation TEXT,
                qa_verdict TEXT,
                qa_violations TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle INTEGER,
                submission_id INTEGER,
                predicted_issues TEXT NOT NULL,
                baseline_issues TEXT NOT NULL,
                model TEXT NOT NULL,
                rubric_version INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cycles (
                cycle INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                batch_count INTEGER,
                baseline_accuracy REAL,
                adapted_accuracy REAL,
                promoted INTEGER,
                disagreements INTEGER,
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS rubric_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER,
                rule_key TEXT,
                action TEXT,
                approved_by TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS design_deck (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL,
                true_issues TEXT NOT NULL,
                rubric_version INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS human_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                reviewer TEXT NOT NULL,
                original_prediction TEXT NOT NULL,
                corrected_labels TEXT NOT NULL,
                note TEXT NOT NULL,
                qa_recommendation TEXT,
                qa_verdict TEXT,
                qa_violations TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );
            """
        )

        _ensure_columns(c, "reviews", {
            "rating": "TEXT NOT NULL DEFAULT 'revision_needed'",
            "confidence": "INTEGER NOT NULL DEFAULT 3",
            "validated": "INTEGER NOT NULL DEFAULT 0",
            "qa_recommendation": "TEXT",
            "qa_verdict": "TEXT",
            "qa_violations": "TEXT NOT NULL DEFAULT '[]'",
        })
        _ensure_columns(c, "human_corrections", {
            "qa_recommendation": "TEXT",
            "qa_verdict": "TEXT",
            "qa_violations": "TEXT NOT NULL DEFAULT '[]'",
        })
        _ensure_columns(c, "submissions", {
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "created_at": "TEXT NOT NULL DEFAULT '1970-01-01T00:00:00+00:00'",
        })

        # Backfill legacy rows in existing deployments without altering the live database file.
        c.execute("UPDATE submissions SET status = 'pending' WHERE status IS NULL OR status = ''")
        c.execute("UPDATE submissions SET created_at = ? WHERE created_at IS NULL OR created_at = ''", (now(),))
        c.execute("UPDATE reviews SET rating = 'revision_needed' WHERE rating IS NULL OR rating = ''")
        c.execute("UPDATE reviews SET confidence = 3 WHERE confidence IS NULL")
        c.execute("UPDATE reviews SET validated = 0 WHERE validated IS NULL")

        c.execute("INSERT OR IGNORE INTO config VALUES ('rubric_version', '1')")
        c.execute("INSERT OR IGNORE INTO config VALUES ('adaptation_enabled', '1')")

        if c.execute("SELECT COUNT(*) FROM design_deck").fetchone()[0] == 0:
            for design in DESIGN_DECK:
                c.execute(
                    "INSERT INTO design_deck (id, title, body, status, true_issues, rubric_version) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        design["id"],
                        design["title"],
                        design["body"],
                        design["status"],
                        json.dumps(design["true_issues"]),
                        1,
                    ),
                )

        if c.execute("SELECT COUNT(*) FROM submissions").fetchone()[0] == 0:
            for design in DESIGN_DECK:
                c.execute(
                    "INSERT INTO submissions (id, body, rubric_version, true_issues, reviewed, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        design["id"],
                        design["body"],
                        1,
                        json.dumps(design["true_issues"]),
                        1,
                        design["status"],
                        now(),
                    ),
                )
            for idx in range(6, 16):
                prompt = (
                    "A moonlit school idol with a clear silhouette, cool palette, readable eyes, balanced pose, "
                    "and cohesive costume. The design should feel confident and polished in thumbnail size."
                )
                c.execute(
                    "INSERT INTO submissions (id, body, rubric_version, true_issues, reviewed, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (idx, prompt, 1, "[]", 0, "pending", now()),
                )

        if c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0:
            for design in DESIGN_DECK:
                labels = design["true_issues"]
                note = (
                    "VALIDATED reviewer note: The design is polished and supported by explicit visual cues."
                    if not labels
                    else "VALIDATED reviewer note: The design requires closer attention to silhouette, readability, and pose because the relevant cues are weak."
                )
                rating = "accepted" if not labels else "revision_needed" if len(labels) <= 2 else "escalated"
                c.execute(
                    "INSERT INTO reviews (submission_id, reviewer, issue_labels, note, simulated, rating, confidence, validated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        design["id"],
                        "Mina",
                        json.dumps(labels),
                        note,
                        0,
                        rating,
                        4,
                        1,
                        now(),
                    ),
                )


def get_config(c, key):
    row = c.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    if row is None:
        return ""
    return row[0]


def current_version(c):
    return int(get_config(c, "rubric_version"))


def baseline(text, version):
    """Deterministic heuristic for design QA. Key rule words are specific and objective."""
    text_lower = text.lower()
    issues = set()
    checks = [
        ("silhouette", ["silhouette", "profile", "outline", "contour", "shape"]),
        ("color_story", ["palette", "color", "hue", "accent", "contrast"]),
        ("readability", ["readability", "readable", "clarity", "legible", "face", "feature", "small size", "thumbnail"]),
        ("expression", ["expression", "emotion", "eyes", "mouth", "facial"]),
        ("pose", ["pose", "stance", "gesture", "motion", "center of gravity"]),
        ("consistency", ["consistent", "cohesive", "costume", "style", "uniform", "accessories"]),
    ]
    if version >= 2:
        checks.append(("evidence", ["evidence", "visual cue", "specific", "justification", "detail", "anchor"]))
    for rule_key, vocabulary in checks:
        if not any(term in text_lower for term in vocabulary):
            issues.add(rule_key)
    return sorted(issues)


def majority_labels(c, version):
    rows = c.execute(
        """
        SELECT r.submission_id, r.issue_labels, s.body
        FROM reviews r
        JOIN submissions s ON s.id = r.submission_id
        WHERE s.rubric_version = ? AND r.simulated = 0 AND r.validated = 1
        """,
        (version,),
    ).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["submission_id"], {"body": row["body"], "votes": []})["votes"].append(set(json.loads(row["issue_labels"])))

    labels = {}
    for sid, payload in grouped.items():
        votes = payload["votes"]
        if len(votes) < 2:
            continue
        rule_keys = list(RULES[version].keys())
        major = {key for key in rule_keys if sum(key in vote for vote in votes) > len(votes) / 2}
        if major:
            labels[sid] = (payload["body"], major)
    return labels


def predict(text, version, examples=None, enabled=False):
    base = baseline(text, version)
    if not enabled or not examples:
        return base, "baseline"
    pairs = list(examples.values())
    if not pairs:
        return base, "baseline"
    corpus = [body for body, _ in pairs] + [text]
    tf = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(corpus)
    sims = cosine_similarity(tf[-1], tf[:-1]).ravel()
    best_idx = int(sims.argmax()) if sims.size else -1
    if best_idx >= 0 and sims[best_idx] >= 0.78:
        return sorted(pairs[best_idx][1]), "reviewer-example"
    return base, "baseline"


def create_review(c, sid, reviewer, issues, note="", simulated=False, rating="revision_needed", confidence=3):
    version = current_version(c)
    keys = set(RULES[version])
    issue_list = sorted(set(issues) & keys)
    note = note or "No explicit evidence was written in this review note."
    c.execute(
        "INSERT INTO reviews (submission_id, reviewer, issue_labels, note, simulated, rating, confidence, validated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sid,
            reviewer,
            json.dumps(issue_list),
            note,
            int(simulated),
            rating,
            confidence,
            0 if simulated else 1,
            now(),
        ),
    )
    c.execute("UPDATE submissions SET reviewed=1, status='reviewed' WHERE id=?", (sid,))


def record_human_correction(
    c,
    sid,
    reviewer,
    original_prediction,
    corrected_labels,
    note,
    qa_recommendation=None,
    qa_verdict=None,
    qa_violations=(),
):
    c.execute(
        "INSERT INTO human_corrections (submission_id, reviewer, original_prediction, corrected_labels, note, qa_recommendation, qa_verdict, qa_violations, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            sid,
            reviewer,
            json.dumps(original_prediction),
            json.dumps(corrected_labels),
            note,
            qa_recommendation,
            qa_verdict,
            json.dumps(qa_violations),
            now(),
        ),
    )


def detect_generic_comment(text):
    comment = (text or "").strip().lower()
    if not comment:
        return True
    generic_phrases = [
        "looks good",
        "nice job",
        "good work",
        "great design",
        "strong overall",
        "nice",
        "cool design",
        "looks great",
        "well done",
        "excellent",
        "very strong character",
        "concept is appealing",
        "visual style feels polished",
        "great job overall",
    ]
    if any(phrase in comment for phrase in generic_phrases) and not _SPECIFIC_REVIEW_CUES.search(comment):
        return True
    words = re.findall(r"[a-zA-Z]+", comment)
    return len(words) < 10


def _normalized_feedback(text):
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _evidence_excerpt(text):
    sentences = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return next((sentence for sentence in sentences if sentence), "")


def audit_expert_review(comment, version, previous_feedback=()):
    """Assess reviewer-written text only; this does not verify claims about unseen artwork."""
    text = (comment or "").strip()
    rules = REVIEW_RULES.get(version, REVIEW_RULES[max(REVIEW_RULES)])
    violations = []
    specific = bool(_SPECIFIC_REVIEW_CUES.search(text)) and not detect_generic_comment(text)

    def flag(rule_key, evidence, reason):
        violations.append({
            "rule_key": rule_key,
            "rule": rules[rule_key],
            "evidence": evidence,
            "reason": reason,
        })

    if not specific:
        flag(
            "specificity",
            _evidence_excerpt(text) or "(No feedback was submitted.)",
            "The submitted text does not cite a concrete design detail.",
        )

    if not _ACTIONABLE_LANGUAGE.search(text):
        flag(
            "actionability",
            _evidence_excerpt(text) or "(No feedback was submitted.)",
            "No concrete next step for the expert or artist appears in the submitted text.",
        )

    normalized = _normalized_feedback(text)
    if normalized:
        for earlier in previous_feedback:
            earlier_text = earlier.get("feedback_text", "") if isinstance(earlier, dict) else earlier
            earlier_normalized = _normalized_feedback(earlier_text)
            if earlier_normalized and SequenceMatcher(None, normalized, earlier_normalized).ratio() >= 0.9:
                flag(
                    "originality",
                    f'Current review: "{text}"\nMatching review: "{earlier_text}"',
                    "The review closely repeats feedback already submitted for another item.",
                )
                break

    if version >= 2:
        rating_match = re.search(
            r"\b(?:rate|rating|score|give it|mark this|score it)\b.{0,50}\b\d+(?:\.\d+)?\s*(?:/10)?",
            text,
            re.IGNORECASE,
        )
        if rating_match and not re.search(r"\b(because|since|as|given that)\b", text[rating_match.start():], re.IGNORECASE):
            flag(
                "rating_justification",
                rating_match.group(0),
                "The numeric rating is not connected to a reason or cited detail in the submitted text.",
            )

    verdict = "revision_needed" if violations else "accepted"
    return {
        "rubric_version": version,
        "verdict": verdict,
        "recommendation": "NEEDS REVISION" if verdict == "revision_needed" else "ACCEPTED",
        "violations": violations,
        "summary": (
            f"{len(violations)} active expert-review rubric violation(s) found."
            if violations
            else "No active expert-review rubric violations found in the submitted text."
        ),
    }


def detect_repeated_feedback(comment, c, threshold=0.82):
    candidate = (comment or "").strip()
    if not candidate:
        return False
    rows = c.execute(
        "SELECT note FROM reviews WHERE note IS NOT NULL AND note != '' AND simulated = 0"
    ).fetchall()
    if not rows:
        return False
    corpus = [row["note"] for row in rows] + [candidate]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    tf = vectorizer.fit_transform(corpus)
    sims = cosine_similarity(tf[-1], tf[:-1]).ravel()
    return bool(sims.size and sims.max() >= threshold)


def feedback_quality_flags(c, comment, rating, issues, version=None, previous_feedback=()):
    active_version = version if version is not None else current_version(c)
    stored_feedback = [
        row["note"]
        for row in c.execute(
            "SELECT note FROM reviews WHERE note IS NOT NULL AND note != '' AND simulated = 0"
        ).fetchall()
    ]
    audit = audit_expert_review(
        comment,
        active_version,
        list(previous_feedback) + stored_feedback,
    )
    violation_keys = {item["rule_key"] for item in audit["violations"]}
    flags = {
        "generic_comment": "specificity" in violation_keys,
        "repeated_feedback": "originality" in violation_keys,
        "poor_justification": bool(violation_keys - {"specificity", "originality"}),
        "audit": audit,
    }
    return flags


def retrieve_validated_examples(c, query_text, limit=3):
    rows = c.execute(
        "SELECT r.submission_id, r.issue_labels, r.note, s.body FROM reviews r JOIN submissions s ON s.id = r.submission_id WHERE r.validated = 1 AND r.simulated = 0 ORDER BY r.created_at DESC"
    ).fetchall()
    if not rows:
        return []
    corpus = [row["note"] or row["body"] for row in rows] + [query_text or ""]
    tf = TfidfVectorizer(ngram_range=(1, 2)).fit_transform(corpus)
    sims = cosine_similarity(tf[-1], tf[:-1]).ravel()
    ranked = sorted(enumerate(sims), key=lambda pair: pair[1], reverse=True)
    examples = []
    for idx, similarity in ranked[:limit]:
        row = rows[idx]
        examples.append(
            {
                "submission_id": row["submission_id"],
                "similarity": round(float(similarity), 3),
                "issue_labels": json.loads(row["issue_labels"]),
                "note": row["note"],
                "body": row["body"],
            }
        )
    return examples


def simulate_votes(c, sid, true_issues, version, rng):
    keys = list(RULES[version])
    true_set = set(true_issues) & set(keys)
    for reviewer in rng.sample(REVIEWERS, 3):
        vote = set(true_set)
        if rng.random() < 0.2:
            key = rng.choice(keys)
            if key in vote:
                vote.remove(key)
            else:
                vote.add(key)
        if not vote:
            rating = "accepted"
            note = "SIMULATED reviewer judgment: accepted because the silhouette, palette, expression, and pose all align with the design brief."
        elif len(vote) <= 2:
            rating = "revision_needed"
            note = "SIMULATED reviewer judgment: revision needed because a handful of cues remain unclear, especially readability and pose."
        else:
            rating = "escalated"
            note = "SIMULATED reviewer judgment: escalated because multiple core rule violations undermine readability, expression, and identity."
        c.execute(
            "INSERT INTO reviews (submission_id, reviewer, issue_labels, note, simulated, rating, confidence, validated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, reviewer, json.dumps(sorted(vote)), note, 1, rating, 3, 0, now()),
        )
    return true_set


def accuracy(items, version, examples, enabled):
    if not items:
        return None
    score = 0
    for body, truth in items:
        pred, _ = predict(body, version, examples, enabled)
        score += set(pred) == truth
    return score / len(items)


def cycle(db=DB, batch_size=8):
    init(db)
    with connect(db) as c:
        version = current_version(c)
        examples = majority_labels(c, version)
        enabled = get_config(c, "adaptation_enabled") == "1"
        pending = c.execute(
            "SELECT * FROM submissions WHERE reviewed = 0 AND status = 'pending' ORDER BY id LIMIT ?",
            (batch_size,),
        ).fetchall()
        if not pending:
            return {"status": "no_pending", "message": "No pending design submissions. Add more queue items or reset the demo."}

        rng = random.Random(200 + c.execute("SELECT COUNT(*) FROM cycles").fetchone()[0])
        cycle_id = c.execute("SELECT COALESCE(MAX(cycle), 0) + 1 FROM cycles").fetchone()[0]
        disagreements = 0
        for row in pending:
            sid = row["id"]
            body = row["body"]
            truth = set(json.loads(row["true_issues"])) & set(RULES[version])
            baseline_issues = baseline(body, version)
            predicted, model = predict(body, version, examples, enabled)
            c.execute(
                "INSERT INTO predictions (cycle, submission_id, predicted_issues, baseline_issues, model, rubric_version, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (cycle_id, sid, json.dumps(predicted), json.dumps(baseline_issues), model, version, now()),
            )
            if set(predicted) != truth:
                disagreements += 1
            simulate_votes(c, sid, truth, version, rng)

        holdout = []
        for row in c.execute("SELECT body, true_issues FROM design_deck ORDER BY id").fetchall():
            holdout.append((row["body"], set(json.loads(row["true_issues"])) & set(RULES[version])))

        candidate_examples = majority_labels(c, version)
        base_acc = accuracy(holdout, version, candidate_examples, False)
        adapt_acc = accuracy(holdout, version, candidate_examples, True)
        promoted = bool(len(candidate_examples) >= 3 and adapt_acc is not None and adapt_acc > base_acc)
        if promoted:
            c.execute("UPDATE config SET value='1' WHERE key='adaptation_enabled'")
        else:
            c.execute("UPDATE config SET value='0' WHERE key='adaptation_enabled'")

        notes = (
            f"{len(candidate_examples)} validated design examples. Held-out evaluation uses the synthetic design deck; "
            "promotion requires improvement over the baseline model."
        )
        c.execute(
            "INSERT INTO cycles (created_at, batch_count, baseline_accuracy, adapted_accuracy, promoted, disagreements, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (now(), len(pending), base_acc, adapt_acc, int(promoted), disagreements, notes),
        )
        return {
            "status": "ok",
            "cycle": cycle_id,
            "processed": len(pending),
            "disagreements": disagreements,
            "baseline": base_acc,
            "adapted": adapt_acc,
            "promoted": promoted,
            "validated_examples": len(candidate_examples),
            "notes": notes,
        }


def parse_rubric_update(proposal_text):
    text = (proposal_text or "").lower()
    if not text.strip():
        return {}

    def hit(*tokens):
        return any(token in text for token in tokens)

    mapping = {
        "rating_justification": hit("rating", "visual cue", "specific", "justification", "evidence"),
    }
    return {
        key: REVIEW_RULES[2][key]
        for key, active in mapping.items()
        if active
    }


def update_rubric(db=DB, approver="Demo project manager", proposal=None):
    with connect(db) as c:
        current = current_version(c)
        if current >= 2:
            return False

        if proposal:
            parsed = parse_rubric_update(proposal)
            if not parsed:
                parsed = {"rating_justification": REVIEW_RULES[2]["rating_justification"]}
            next_version = 2
            c.execute("UPDATE config SET value=? WHERE key='rubric_version'", (str(next_version),))
            c.execute("UPDATE config SET value='0' WHERE key='adaptation_enabled'")
            for key, description in parsed.items():
                c.execute(
                    "INSERT INTO rubric_events (version, rule_key, action, approved_by, created_at) VALUES (?, ?, ?, ?, ?)",
                    (next_version, key, "Human-approved plain-English rule update", approver, now()),
                )
            c.execute("UPDATE submissions SET rubric_version = ? WHERE reviewed = 0", (next_version,))
            return True

        c.execute("UPDATE config SET value='2' WHERE key='rubric_version'")
        c.execute("UPDATE config SET value='0' WHERE key='adaptation_enabled'")
        c.execute(
            "INSERT INTO rubric_events (version, rule_key, action, approved_by, created_at) VALUES (?, ?, ?, ?, ?)",
            (2, "rating_justification", "Added explicit rating-justification requirement", approver, now()),
        )
        c.execute("UPDATE submissions SET rubric_version = 2 WHERE reviewed = 0")
        return True


def add_submission(body, db=DB):
    init(db)
    with connect(db) as c:
        version = current_version(c)
        c.execute(
            "INSERT INTO submissions (body, rubric_version, true_issues, reviewed, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (body, version, "[]", 0, "pending", now()),
        )
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_design_deck(c):
    return c.execute("SELECT * FROM design_deck ORDER BY id").fetchall()


def reset(db=DB):
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(db) + suffix)
        if path.exists():
            path.unlink()
    init(db)


def evaluate_review_quality(comment, rating, issues, version=1, previous_feedback=()):
    audit = audit_expert_review(comment, version, previous_feedback)
    violations = {item["rule_key"] for item in audit["violations"]}
    return {
        "generic": "specificity" in violations,
        "poor_justification": "actionability" in violations or "rating_justification" in violations,
        "needs_evidence": "specificity" in violations,
        "audit": audit,
    }


def get_rubric_summary(c):
    version = current_version(c)
    return REVIEW_RULES.get(version, REVIEW_RULES[max(REVIEW_RULES)])


def get_design_rubric_summary(c):
    version = current_version(c)
    return RULES.get(version, RULES[max(RULES)])

"""Exact validation-only balanced-accuracy selection with disk-backed scores."""

import math
from pathlib import Path
import sqlite3


POLICY = "validation_balanced_accuracy_v1"
TIES = "closest finite threshold to0.5, then higher; all-negative last"


def probability(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Binary probability must be finite numeric and in[0,1]")
    return float(value)


def threshold_prediction(score, rule):
    score = probability(score)
    if rule == {"kind": "all_negative", "value": None}:
        return 0
    if (not isinstance(rule, dict) or set(rule) != {"kind", "value"} or
            rule["kind"] != "score_at_least"):
        raise ValueError("Unknown frozen threshold rule")
    return int(score >= probability(rule["value"]))


def select_threshold(observations, spool):
    """Consume (id, probability, label) from validation only; never a test iterator."""
    spool = Path(spool)
    spool.parent.mkdir(parents=True, exist_ok=True)
    with spool.open("xb"):
        pass
    connection = sqlite3.connect(spool)
    try:
        connection.execute("PRAGMA cache_size = -4096")
        connection.execute("PRAGMA temp_store = FILE")
        connection.execute("CREATE TABLE scores (id TEXT PRIMARY KEY, score REAL, label INTEGER)")
        count, positives = 0, 0
        for identifier, score, label in observations:
            if not isinstance(identifier, str) or not identifier or type(label) is not int or label not in (0, 1):
                raise ValueError("Validation rows require distinct IDs and integer0/1 labels")
            try:
                connection.execute("INSERT INTO scores VALUES (?,?,?)", (identifier, probability(score), label))
            except sqlite3.IntegrityError as error:
                raise ValueError("Repeated validation ID") from error
            count += 1
            positives += label
            if count % 1000 == 0:
                connection.commit()
        negatives = count - positives
        if not positives or not negatives:
            raise ValueError("Threshold selection requires both validation classes")
        connection.commit()
        tp, fp, candidates = 0, 0, 0
        best_rank, best = None, None

        def consider(value):
            nonlocal best_rank, best, candidates
            tn, fn = negatives - fp, positives - tp
            # Compare exact integer objectives rather than rounded float recalls.
            objective = tp * negatives + tn * positives
            rank = (objective, -abs(value - .5), value) if value is not None else (objective, -math.inf, -math.inf)
            candidates += 1
            if best_rank is None or rank > best_rank:
                best_rank = rank
                best = dict(rule=dict(kind="score_at_least" if value is not None else "all_negative", value=value),
                            confusion_matrix_true_by_predicted=[[tn, fp], [fn, tp]],
                            balanced_accuracy=objective / (2 * positives * negatives),
                            objective_numerator=objective, objective_denominator=2 * positives * negatives)

        consider(None)
        half_seen = False
        for score, positive_count, group_count in connection.execute(
                "SELECT score,SUM(label),COUNT(*) FROM scores GROUP BY score ORDER BY score DESC"):
            if not half_seen and score < .5:
                consider(.5)
                half_seen = True
            tp += positive_count
            fp += group_count - positive_count
            consider(score)
            half_seen |= score == .5
        if not half_seen:
            consider(.5)
        best.update(policy=POLICY, objective="balanced_accuracy", partition="validation",
                    structures=count, class_counts=[negatives, positives], candidate_count=candidates,
                    tie_policy=TIES, test_labels_used_for_selection=False)
        return best
    finally:
        connection.close()

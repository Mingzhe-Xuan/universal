"""Scalar-element regression and exact, disk-backed binary classification metrics."""

import math
from pathlib import Path
import sqlite3


def balanced_accuracy(confusion):
    if (not isinstance(confusion, (list, tuple)) or len(confusion) != 2 or
            any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in confusion) or
            any(type(value) is not int or value < 0 for row in confusion for value in row)):
        raise ValueError("Binary confusion matrix requires 2x2 nonnegative integer counts")
    tn, fp = confusion[0]
    fn, tp = confusion[1]
    if not (tn + fp) or not (tp + fn):
        return None
    return .5 * (tn / (tn + fp) + tp / (tp + fn))


def flatten(value):
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from flatten(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)
    else:
        raise ValueError("Metrics require numeric scalars or nested numeric sequences")


class RegressionMetrics:
    """Each update is one structure; missing target elements are masked explicitly."""

    def __init__(self):
        self.structures = self.elements = self.masked_elements = 0
        self.absolute = self.squared = self.frobenius = self.relative = 0.
        self.relative_structures = self.zero_norm_targets = 0

    def update(self, prediction, target):
        prediction, target = list(flatten(prediction)), list(flatten(target))
        if len(prediction) != len(target) or not prediction:
            raise ValueError("Prediction and target element counts must match and be nonempty")
        if any(not math.isfinite(value) for value in prediction):
            raise FloatingPointError("Nonfinite evaluation prediction")
        pairs = [(p, y) for p, y in zip(prediction, target) if math.isfinite(y)]
        self.masked_elements += len(target) - len(pairs)
        if not pairs:
            return
        errors = [p - y for p, y in pairs]
        squared = math.fsum(value * value for value in errors)
        norm = math.sqrt(math.fsum(y * y for _, y in pairs))
        frobenius = math.sqrt(squared)
        if not math.isfinite(frobenius) or not math.isfinite(norm):
            raise FloatingPointError("Evaluation error/norm overflow")
        self.structures += 1
        self.elements += len(pairs)
        self.absolute += math.fsum(abs(value) for value in errors)
        self.squared += squared
        self.frobenius += frobenius
        if norm > 0:
            self.relative += frobenius / norm
            self.relative_structures += 1
        else:
            self.zero_norm_targets += 1

    def result(self):
        if not self.elements:
            raise ValueError("No finite evaluation labels")
        return {"structures": self.structures, "finite_elements": self.elements,
                "masked_target_elements": self.masked_elements,
                "mae": self.absolute / self.elements, "rmse": math.sqrt(self.squared / self.elements),
                "mean_structure_frobenius_error": self.frobenius / self.structures,
                "mean_relative_structure_frobenius_error": self.relative / self.relative_structures
                if self.relative_structures else None,
                "relative_error_structures": self.relative_structures,
                "zero_norm_target_structures": self.zero_norm_targets,
                "weighting": "MAE/RMSE by finite scalar elements; Frobenius by labelled structure",
                "relative_error_policy": "zero-norm targets excluded from relative error only"}


class BinaryClassificationMetrics:
    """Store scores on disk for exact tie-aware AUROC, with bounded Python memory."""

    def __init__(self, spool):
        spool = Path(spool)
        spool.parent.mkdir(parents=True, exist_ok=True)
        # Prevent mixing rows from another evaluation or overwriting its scores.
        with spool.open("xb"):
            pass
        self.connection = sqlite3.connect(spool)
        self.connection.execute("PRAGMA cache_size = -4096")
        self.connection.execute("PRAGMA temp_store = FILE")
        self.connection.execute("CREATE TABLE scores (score REAL NOT NULL, label INTEGER NOT NULL)")
        self.confusion = [[0, 0], [0, 0]]
        self.count = 0

    def update(self, positive_probability, target, *, predicted_class=None):
        if (isinstance(target, bool) or not isinstance(target, int) or target not in (0, 1)):
            raise ValueError("Binary target must be integer 0 or 1")
        score = float(positive_probability)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Binary probability must be finite and in [0,1]")
        predicted = int(score >= .5) if predicted_class is None else predicted_class
        if isinstance(predicted, bool) or not isinstance(predicted, int) or predicted not in (0, 1):
            raise ValueError("Predicted class must be integer 0 or 1")
        self.connection.execute("INSERT INTO scores VALUES (?, ?)", (score, target))
        self.confusion[target][predicted] += 1
        self.count += 1
        if self.count % 1000 == 0:
            self.connection.commit()

    def result(self):
        if not self.count:
            raise ValueError("No evaluation labels")
        self.connection.commit()
        tn, fp = self.confusion[0]
        fn, tp = self.confusion[1]
        positives, negatives = tp + fn, tn + fp
        negatives_before, favourable = 0, 0.
        cursor = self.connection.execute(
            "SELECT score, SUM(label), COUNT(*) FROM scores GROUP BY score ORDER BY score")
        for _, positive_count, count in cursor:
            negative_count = count - positive_count
            favourable += positive_count * (negatives_before + .5 * negative_count)
            negatives_before += negative_count
        precision = tp / (tp + fp) if tp + fp else 0.
        recall = tp / positives if positives else 0.
        return {"structures": self.count, "confusion_matrix_true_by_predicted": self.confusion,
                "accuracy": (tp + tn) / self.count, "precision": precision, "recall": recall,
                "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.,
                "balanced_accuracy": balanced_accuracy(self.confusion),
                "balanced_accuracy_policy": "mean of both true-class recalls; single-class null",
                "roc_auc": favourable / (positives * negatives) if positives and negatives else None,
                "roc_auc_policy": "exact Mann-Whitney probability; tied scores count as one half; single-class null"}

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

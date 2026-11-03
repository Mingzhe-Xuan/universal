import math
from pathlib import Path
import tempfile
import unittest

from universal_gnn.engine.evaluation import BinaryClassificationMetrics, RegressionMetrics


class EvaluationMetricTests(unittest.TestCase):
    def test_element_weights_tensor_norms_missing_and_zero_targets(self):
        metrics = RegressionMetrics()
        metrics.update([[1., 2.], [3., 4.]], [[0., 0.], [0., 0.]])
        metrics.update([3., 99.], [1., float("nan")])
        result = metrics.result()
        self.assertEqual(result["finite_elements"], 5)
        self.assertEqual(result["masked_target_elements"], 1)
        self.assertAlmostEqual(result["mae"], 12 / 5)
        self.assertAlmostEqual(result["rmse"], math.sqrt(34 / 5))
        self.assertAlmostEqual(result["mean_structure_frobenius_error"], (math.sqrt(30) + 2) / 2)
        self.assertEqual(result["mean_relative_structure_frobenius_error"], 2)
        self.assertEqual(result["zero_norm_target_structures"], 1)

    def test_invalid_regression_and_no_labels(self):
        for prediction, target, error in [([1], [], ValueError), ([float("inf")], [1], FloatingPointError),
                                           (["bad"], [1], ValueError)]:
            with self.assertRaises(error):
                RegressionMetrics().update(prediction, target)
        metrics = RegressionMetrics()
        metrics.update([0.], [float("nan")])
        with self.assertRaises(ValueError):
            metrics.result()

    def test_exact_auc_ties_confusion_and_repeat_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.sqlite"
            with BinaryClassificationMetrics(path) as metrics:
                for score, target in [(.1, 0), (.4, 0), (.4, 1), (.8, 1)]:
                    metrics.update(score, target)
                result = metrics.result()
                self.assertEqual(result, metrics.result())
                self.assertEqual(result["confusion_matrix_true_by_predicted"], [[2, 0], [1, 1]])
                self.assertEqual(result["accuracy"], .75)
                self.assertAlmostEqual(result["f1"], 2 / 3)
                self.assertEqual(result["roc_auc"], .875)
            with self.assertRaises(FileExistsError):
                BinaryClassificationMetrics(path)

    def test_single_class_and_explicit_argmax_tie(self):
        with tempfile.TemporaryDirectory() as directory:
            with BinaryClassificationMetrics(Path(directory) / "scores.sqlite") as metrics:
                metrics.update(.5, 0, predicted_class=0)
                result = metrics.result()
                self.assertEqual(result["accuracy"], 1)
                self.assertIsNone(result["roc_auc"])
                for score, target in [(float("nan"), 1), (1.1, 0), (.2, 2), (.2, True)]:
                    with self.assertRaises(ValueError):
                        metrics.update(score, target)


if __name__ == "__main__":
    unittest.main()

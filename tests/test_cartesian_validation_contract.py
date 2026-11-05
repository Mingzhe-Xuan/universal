"""Pure protocol guards; actual model transformations are tested in CPU Slurm."""
import unittest
import hashlib
from pathlib import Path

from universal_gnn.benchmarks.validation.cartesian import response_rank, rotation_subscripts
from universal_gnn.properties import property_spec


class CartesianValidationContract(unittest.TestCase):
    def test_registered_tensor_formats(self):
        for name, rank in [("dielectric", 2), ("piezoelectric", 3), ("elastic", 4)]:
            with self.subTest(name=name):
                spec = property_spec(name)
                self.assertEqual(response_rank(spec.shape, spec.scope), rank)
                self.assertEqual(len(spec.response_indices) + len(spec.auxiliary_indices), rank)
                self.assertEqual(spec.construction, "derivative")

    def test_no_node_or_nontensor_acceptance(self):
        for shape, scope in [((3, 3), "node"), ((3,), "graph"), ((3,) * 5, "graph"),
                             ((3, 6), "graph"), ((3, 3.0), "graph"), ((), "graph")]:
            with self.subTest(shape=shape, scope=scope), self.assertRaises(ValueError):
                response_rank(shape, scope)

    def test_every_cartesian_axis_has_one_independent_rotation(self):
        for rank in [2, 3, 4]:
            with self.subTest(rank=rank):
                left, right = rotation_subscripts(rank).split("->")
                factors = left.split(",")
                self.assertEqual(len(factors), rank + 1)
                self.assertEqual(factors[-1][0], right[0])
                self.assertEqual(len(factors[-1]), rank + 1)
                self.assertEqual(len(right), rank + 1)
                self.assertEqual(len(set(factors[-1])), rank + 1)
                self.assertEqual(len(set(right)), rank + 1)
                for axis in range(rank):
                    self.assertEqual(factors[axis], right[axis + 1] + factors[-1][axis + 1])
                self.assertTrue(set(factors[-1][1:]).isdisjoint(right))

    def test_invalid_rank_is_rejected(self):
        for rank in [True, 1, 5, 3., "3", None]:
            with self.subTest(rank=rank), self.assertRaises(ValueError):
                rotation_subscripts(rank)

    def test_independent_post_binds_cartesian_validation_source(self):
        from universal_gnn.benchmarks.prediction_assessment.runtime import validation_sources
        sources = validation_sources()
        name = "src/universal_gnn/benchmarks/validation/cartesian.py"
        self.assertEqual(len(sources), 4)
        self.assertEqual(sources[name], hashlib.sha256(Path(name).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()

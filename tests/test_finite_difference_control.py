import math
import unittest

from universal_gnn.benchmarks.validation.finite_difference import converged_difference


class FiniteDifferenceControlTests(unittest.TestCase):
    def test_local_derivative_requires_convergence_inside_topology_boundary(self):
        def potential(x):
            return 2*x + x*x + (1. if x > .00075 else 0.)
        result = converged_difference([2.], lambda h: [(potential(h)-potential(-h))/(2*h)])
        self.assertTrue(result['passed'])
        self.assertEqual(result['selected_steps'], [.0005, .00025])
        self.assertFalse(result['attempts'][0]['matches_analytic'])
        self.assertFalse(result['attempts'][1]['matches_analytic'])

    def test_wrong_analytic_and_isolated_coincidence_are_rejected(self):
        self.assertFalse(converged_difference([3.], lambda h: [2.])['passed'])
        self.assertFalse(converged_difference([0.], lambda h: [0. if h == .001 else 1.])['passed'])
        alternating = iter([.0015, -.0015, .0015, -.0015, .0015])
        result = converged_difference([0.], lambda h: [next(alternating)], rtol=0)
        self.assertFalse(result['passed'])
        self.assertTrue(all(item['matches_analytic'] for item in result['attempts']))

    def test_largest_stable_pair_retained_before_small_step_roundoff(self):
        visited=[]
        def estimate(h):
            visited.append(h)
            return [1., -2.] if h >= .001 else [99., 99.]
        result = converged_difference([1., -2.], estimate)
        self.assertTrue(result['passed'])
        self.assertEqual(visited, [.002, .001])
        self.assertEqual(result['selected_steps'], visited)

    def test_invalid_steps_and_nonfinite_estimates_fail_explicitly(self):
        for steps in [(1.,), (0., .001), (.001, .002), (.001, .001), (True, .1), (math.inf, .1)]:
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                converged_difference([1.], lambda h: [1.], steps=steps)
        with self.assertRaises(FloatingPointError):
            converged_difference([1.], lambda h: [math.nan])
        with self.assertRaises(ValueError):
            converged_difference([1.], lambda h: [])


if __name__ == '__main__':
    unittest.main()

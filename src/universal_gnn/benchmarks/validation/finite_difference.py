"""Step convergence controls independent of any model, graph library or numerical package."""
import math


STEPS = (.002, .001, .0005, .00025, .000125)


def converged_difference(analytic, estimate, *, steps=STEPS, rtol=.02, atol=.002):
    steps = tuple(steps)
    if (len(steps) < 2 or any(type(h) not in (int, float) or not math.isfinite(h) or h <= 0 for h in steps)
            or any(a <= b for a, b in zip(steps, steps[1:]))):
        raise ValueError('Finite-difference steps must be strictly decreasing positive finite numbers')
    if any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in (rtol, atol)):
        raise ValueError('Finite-difference tolerances must be nonnegative finite numbers')
    analytic = list(analytic)
    if not analytic or any(type(x) not in (int, float) or not math.isfinite(x) for x in analytic):
        raise ValueError('Analytic derivative must be a nonempty finite vector')

    def close(a, b):
        return all(abs(x-y) <= atol + rtol*abs(y) for x, y in zip(a, b))

    attempts = []
    for step in steps:
        numeric = list(estimate(step))
        if len(numeric) != len(analytic):
            raise ValueError('Finite-difference vector size differs from analytic derivative')
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in numeric):
            raise FloatingPointError('Nonfinite finite-difference estimate')
        current = dict(step=step, numeric=numeric, matches_analytic=close(numeric, analytic),
                       max_abs_error=max(abs(x-y) for x, y in zip(numeric, analytic)))
        previous = attempts[-1] if attempts else None
        current['matches_previous'] = close(numeric, previous['numeric']) if previous else None
        attempts.append(current)
        if previous and current['matches_analytic'] and previous['matches_analytic'] and current['matches_previous']:
            return dict(passed=True, selected_steps=[previous['step'], step], numeric=previous['numeric'],
                        attempts=attempts, rtol=rtol, atol=atol)
    return dict(passed=False, selected_steps=None, numeric=attempts[-1]['numeric'], attempts=attempts,
                rtol=rtol, atol=atol)

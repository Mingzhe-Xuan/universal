"""Absolute tensor errors grouped by observed target components, without projection."""
import math

from universal_gnn.engine.evaluation.metrics import RegressionMetrics


def tensor_values(value, shape, *, missing=False):
    if shape:
        if not isinstance(value, (list, tuple)) or len(value) != shape[0]:
            raise ValueError('Tensor shape differs from the declared component layout')
        return [scalar for item in value for scalar in tensor_values(item, shape[1:], missing=missing)]
    if missing and value is None:
        return [float('nan')]
    if type(value) not in (int, float):
        raise ValueError('Tensor components must be numeric scalars')
    scalar = float(value)
    if not missing and not math.isfinite(scalar):
        raise FloatingPointError('Nonfinite tensor prediction')
    return [scalar]


class GroupedRegressionMetrics:
    """Fixed component layout; each update is one labelled or wholly masked structure."""

    def __init__(self, shape):
        if (not isinstance(shape, (list, tuple)) or not shape or
                any(type(size) is not int or size < 1 for size in shape)):
            raise ValueError('Tensor shape requires positive integer dimensions')
        self.shape = tuple(shape)
        self.structures = self.unlabelled = 0
        self.metrics = {name: RegressionMetrics() for name in ('overall', 'zero', 'nonzero')}
        self.components = {name: dict(count=[0] * math.prod(shape), absolute=[0.] * math.prod(shape),
                                      squared=[0.] * math.prod(shape)) for name in self.metrics}
        self.element_groups = {name: dict(count=[0] * math.prod(shape), absolute=[0.] * math.prod(shape),
                                          squared=[0.] * math.prod(shape)) for name in ('zero', 'nonzero')}

    def update(self, prediction, target):
        predicted = tensor_values(prediction, self.shape)
        observed = tensor_values(target, self.shape, missing=True)
        finite = [value for value in observed if math.isfinite(value)]
        group = ('nonzero' if any(value != 0. for value in finite) else 'zero') if finite else None
        names = ['overall'] + ([group] if group else [])
        for name in names:
            self.metrics[name].update(predicted, observed)
            counts = self.components[name]
            for index, (p, y) in enumerate(zip(predicted, observed)):
                if math.isfinite(y):
                    error = p - y
                    counts['count'][index] += 1
                    counts['absolute'][index] += abs(error)
                    counts['squared'][index] += error * error
        for index, (p, y) in enumerate(zip(predicted, observed)):
            if math.isfinite(y):
                counts = self.element_groups['zero' if y == 0. else 'nonzero']
                error = p - y
                counts['count'][index] += 1
                counts['absolute'][index] += abs(error)
                counts['squared'][index] += error * error
        self.structures += 1
        self.unlabelled += group is None
        return group

    @staticmethod
    def _component_result(values):
        return dict(component_finite_counts=list(values['count']),
                    component_mae=[error / count if count else None for error, count in
                                   zip(values['absolute'], values['count'])],
                    component_rmse=[math.sqrt(error / count) if count else None for error, count in
                                    zip(values['squared'], values['count'])])

    def _result(self, name):
        metrics = self.metrics[name]
        return dict(metrics=metrics.result() if metrics.elements else None,
                    **self._component_result(self.components[name]))

    def _element_result(self, values):
        count = sum(values['count'])
        return dict(finite_elements=count,
                    mae=math.fsum(values['absolute']) / count if count else None,
                    rmse=math.sqrt(math.fsum(values['squared']) / count) if count else None,
                    **self._component_result(values))

    def result(self):
        return dict(structures=self.structures, unlabelled_structures=self.unlabelled,
                    shape=list(self.shape), component_order='C order, final axis varies fastest',
                    zero_policy='all observed finite target components exactly zero; no threshold',
                    missing_policy='nonfinite/null targets masked; wholly masked structures in neither group',
                    overall=self._result('overall'),
                    groups={name: self._result(name) for name in ('zero', 'nonzero')},
                    component_label_groups={name: self._element_result(values)
                                            for name, values in self.element_groups.items()})

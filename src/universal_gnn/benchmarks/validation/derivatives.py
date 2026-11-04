"""Independent finite differences and geometry checks; no training or metadata patches."""
import math

import torch

from universal_gnn.adapters.features import scalar_features
from universal_gnn.contracts import StructureBatch
from universal_gnn.data.geometry import scatter_mean, strain_batch
from universal_gnn.engine.optimization import components
from .finite_difference import STEPS, converged_difference


def validate_derivatives(model, structures, config):
    """Check the actual model on two records; return observations and strict required checks."""
    if len(structures) < 2:
        raise ValueError('Derivative acceptance requires two structures')
    if config['task']['kind'] not in {'forcefield', 'supervised'}:
        raise ValueError('Derivative acceptance supports force fields and response tensors')
    field = config['task']['kind'] == 'forcefield'
    if not field and model.spec.construction != 'derivative':
        raise ValueError('Supervised derivative acceptance requires a response readout')
    if not field and (tuple(model.spec.shape) != (3, 3) or model.spec.scope != 'graph'):
        raise ValueError('Response geometry acceptance currently requires graph-level rank2 Cartesian output')
    parameter = next(model.parameters())
    selected = StructureBatch.from_structures([structures[0], structures[1]]).to(parameter.device, parameter.dtype)
    batch = StructureBatch.from_structures([structures[0]]).to(parameter.device, parameter.dtype)
    offset = .017 * torch.sin(torch.arange(batch.positions.numel(), device=parameter.device,
                                          dtype=parameter.dtype).reshape_as(batch.positions) * .73 + .31)
    batch = batch.with_geometry(batch.positions + offset, batch.cell)
    model.eval()
    result = {'dtype': str(parameter.dtype), 'device': str(parameter.device),
              'structure_ids': list(selected.identifiers), 'checks': {},
              'finite_difference': {'steps': list(STEPS), 'rtol': .02, 'atol': .002,
                                    'criterion': 'adjacent steps must match analytic derivative and each other'},
              'geometry_tolerance': {'rtol': .001, 'atol': .0002}}

    def compare(name, actual, expected, *, rtol=.001, atol=.0002, required=True):
        actual, expected = actual.detach(), expected.detach()
        finite = bool(torch.isfinite(actual).all() and torch.isfinite(expected).all())
        passed = finite and bool(torch.isclose(actual, expected, rtol=rtol, atol=atol).all())
        result['checks'][name] = {'passed': passed, 'required': required,
                                  'max_abs_error': float((actual - expected).abs().max()),
                                  'rtol': rtol, 'atol': atol}

    model.zero_grad(set_to_none=True)
    value = model(batch, create_graph=True)
    loss = value['forces'].square().sum() + value['stress'].square().sum() if field else value.square().sum()
    loss.backward()
    gradients = {}
    for name, module in components(model).items():
        active = [p.grad for p in module.parameters() if p.grad is not None]
        if any(not bool(torch.isfinite(g).all()) for g in active):
            raise FloatingPointError('Nonfinite mixed derivative in '+name)
        gradients[name] = math.sqrt(sum(float(g.detach().double().square().sum()) for g in active))
        trainable = model._component_policy['train_'+name]
        if (trainable and gradients[name] <= 1e-10) or (not trainable and active):
            raise AssertionError('Mixed derivative violates component policy: '+name)
    result['mixed_parameter_gradient_norms'] = gradients
    value = {key:item.detach() for key,item in value.items()} if field else value.detach()
    model.zero_grad(set_to_none=True)
    if field:
        force_indices = [(atom, axis) for atom in range(min(2, len(batch.numbers))) for axis in range(3)]
        stress_indices = [(0, 0), (1, 1), (0, 1)]
        force_a = torch.stack([value['forces'][atom, axis] for atom, axis in force_indices])
        stress_a = torch.stack([value['stress'][0, i, j] for i, j in stress_indices])

        def force_estimate(step):
            estimates = []
            for atom, axis in force_indices:
                change = torch.zeros_like(batch.positions)
                change[atom, axis] = step
                plus = model.energy_model(batch.with_geometry(batch.positions + change, batch.cell)).detach()
                minus = model.energy_model(batch.with_geometry(batch.positions - change, batch.cell)).detach()
                estimates.append((-(plus - minus) / (2 * step)).reshape(()))
            return torch.stack(estimates).tolist()

        def stress_estimate(step):
            estimates = []
            for i, j in stress_indices:
                strain = torch.zeros_like(batch.cell)
                strain[0, i, j] = step
                plus = model.energy_model(strain_batch(batch, strain)).detach()
                minus = model.energy_model(strain_batch(batch, -strain)).detach()
                estimates.append(((plus - minus) / (2 * step * torch.linalg.det(batch.cell[0]).abs()) * 160.21766208).reshape(()))
            return torch.stack(estimates).tolist()

        for name, analytic, estimate in [('forces', force_a, force_estimate), ('stress', stress_a, stress_estimate)]:
            convergence = converged_difference(analytic.tolist(), estimate)
            numeric = analytic.new_tensor(convergence['numeric'])
            key = name+'_finite_difference'
            compare(key, analytic, numeric, rtol=.02, atol=.002)
            result['checks'][key]['passed'] &= convergence['passed']
            result['checks'][key]['selected_steps'] = convergence['selected_steps']
            result['finite_difference'][name+'_analytic'] = analytic.tolist()
            result['finite_difference'][name+'_numeric'] = convergence['numeric']
            result['finite_difference'][name+'_convergence'] = convergence
        compare('net_force', value['forces'].sum(0), torch.zeros_like(value['forces'][0]), rtol=0, atol=2e-5)
    else:
        features = model.backbone.encode(batch)
        if model.adapter is not None:
            features = model.adapter(features)
        if model.readout.processing is not None:
            features = model.readout.processing(features)
        core = model.readout.core
        nodes = scatter_mean(features.nodes, features.batch, batch.num_graphs)
        def response(q):
            if core.kind == 'equivariant':
                return core.response.to_cartesian(core.coupling(nodes, core.auxiliary.from_cartesian(q))).reshape(1, core.response_size)
            coefficients = core.coefficients(scalar_features(nodes, core.irreps)).reshape(1, core.response_size, core.auxiliary_size)
            return torch.einsum('brq,bq->br', coefficients, q.flatten(1))
        columns = []
        for index in range(core.auxiliary_size):
            q = nodes.new_zeros((1, *([3] * len(core.spec.auxiliary_indices))))
            q.reshape(-1)[index] = .1
            columns.append((response(q) - response(-q)) / .2)
        numeric = torch.stack(columns, dim=-1).reshape_as(value)
        compare('response_auxiliary_finite_difference', value, numeric, rtol=2e-4, atol=2e-5)
        result['response'] = {'guarantee': model.readout.descriptor['transformation_guarantee'],
                              'analytic': value.tolist(), 'numeric': numeric.detach().tolist(),
                              'no_symmetry_projection': True}

    axis = batch.positions.new_tensor([1., 2., 3.])
    axis = axis / axis.norm()
    cross = torch.stack([torch.stack([axis[0]*0, -axis[2], axis[1]]),
                         torch.stack([axis[2], axis[0]*0, -axis[0]]),
                         torch.stack([-axis[1], axis[0], axis[0]*0])])
    rotation = torch.eye(3, device=parameter.device, dtype=parameter.dtype) + math.sin(.531)*cross + (1-math.cos(.531))*(cross@cross)
    translated = batch.with_geometry(batch.positions + batch.positions.new_tensor([.31, -.27, .19]), batch.cell)
    transformed = batch.with_geometry(batch.positions @ rotation.T, batch.cell @ rotation.T)
    move = model(translated, create_graph=False)
    turn = model(transformed, create_graph=False)
    if field:
        for key in value:
            compare('translation_'+key, move[key], value[key])
        compare('rotation_energy', turn['total_energy'], value['total_energy'])
        compare('rotation_forces', turn['forces'], value['forces'] @ rotation.T)
        compare('rotation_stress', turn['stress'], rotation @ value['stress'] @ rotation.T)
    else:
        compare('translation_response', move, value)
        guarantee = result['response']['guarantee']
        compare('rotation_response_covariance', turn, rotation @ value @ rotation.T,
                required=guarantee in {'O3_cartesian','SO3_cartesian'})
        if guarantee == 'fixed_frame_components':
            compare('rotation_fixed_frame_invariance', turn, value)
        if guarantee == 'O3_cartesian':
            inverted = model(batch.with_geometry(-batch.positions, -batch.cell), create_graph=False)
            compare('inversion_rank2_response', inverted, value)

    for train_mode in ([False, True] if field else [False]):
        state = {key:item.detach().clone() for key,item in model.state_dict().items()}
        model.train(train_mode)
        combined = model(selected, create_graph=False)
        separate = [model(StructureBatch.from_structures([s]).to(parameter.device, parameter.dtype),
                          create_graph=False) for s in [structures[0],structures[1]]]
        if field:
            for key in combined:
                compare(('train' if train_mode else 'eval')+'_batch_'+key, combined[key],
                        torch.cat([item[key] for item in separate]), rtol=2e-4, atol=2e-5)
        else:
            compare('eval_batch_response', combined, torch.cat(separate), rtol=2e-4, atol=2e-5)
        model.load_state_dict(state, strict=True)
    model.eval()
    result['passed'] = all(item['passed'] for item in result['checks'].values() if item['required'])
    return result

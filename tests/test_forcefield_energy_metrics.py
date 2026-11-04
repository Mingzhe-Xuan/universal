"""Numerical held-out coverage: execute through Slurm."""
import json

import pytest
import torch

from universal_gnn.contracts import Structure
from universal_gnn.engine.evaluation.heldout import score_partition


@pytest.mark.parametrize('batch_size', [1, 2])
@pytest.mark.parametrize('include_energy', [False, True])
def test_energy_per_atom_uses_each_structure_size_without_changing_loss(tmp_path, batch_size, include_energy):
    class AnalyticModel(torch.nn.Module):
        def forward(self, batch, *, create_graph=False):
            return {'total_energy': batch.natoms[:, None].float().square() / 2,
                    'forces': torch.zeros_like(batch.positions),
                    'stress': torch.zeros_like(batch.cell)}

    structures = [Structure(torch.ones(n, dtype=torch.long),
                            torch.arange(n * 3, dtype=torch.float32).reshape(n, 3) * .1,
                            torch.eye(3) * 10, torch.zeros(3, dtype=torch.bool), str(n),
                            targets={'total_energy': 0. if n == 2 else 4., 'forces': [[0.] * 3] * n})
                  for n in [2, 4]]
    outputs = ['total_energy', 'forces'] if include_energy else ['forces']
    config = {'batch_size': batch_size, 'dtype': 'float32', 'device': 'cpu',
              'task': {'kind': 'forcefield', 'supervised_outputs': outputs}}
    result = score_partition(AnalyticModel(), structures, config, {name: 1. for name in outputs},
                             tmp_path / 'scoring')
    assert result['metrics']['forces']['mae'] == 0
    assert result['metrics']['forces']['finite_elements'] == 18
    records = [json.loads(row) for row in open(result['predictions'])]
    assert [row['natoms'] for row in records] == [2, 4]
    if include_energy:
        assert result['normalized_loss'] == 10.
        assert result['metrics']['total_energy']['mae'] == 3.
        assert result['metrics']['energy_per_atom']['mae'] == 1.
        assert result['metrics']['energy_per_atom']['rmse'] == 1.
        assert result['metrics']['energy_per_atom']['unit'] == 'eV/atom'
        assert result['metrics']['energy_per_atom']['structures'] == 2
    else:
        assert 'energy_per_atom' not in result['metrics']
        assert 'total_energy' not in result['metrics']
        assert result['normalized_loss'] == 0.

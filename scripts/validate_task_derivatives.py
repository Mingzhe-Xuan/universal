"""Check a configured force-field or response model through Slurm."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        parser.error('Derivative validation must run through Slurm')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output must be fresh')
    import torch
    from universal_gnn.benchmarks.validation.derivatives import validate_derivatives
    from universal_gnn.engine.batching import model_dtype
    from universal_gnn.engine.configuration import load_config
    from universal_gnn.engine.initialization.neighbors import prepare_native_neighbors
    from universal_gnn.engine.training import build_model, dataset

    config = prepare_native_neighbors(load_config(args.config))
    torch.manual_seed(config.get('seed', 123))
    model = build_model(config).to(device=config.get('device', 'cpu'), dtype=model_dtype(config))
    result = validate_derivatives(model, dataset(config), config)
    result.update(config=config, slurm_job_id=os.environ['SLURM_JOB_ID'],
                  git_commit=subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps({'passed': result['passed'], 'output': str(args.output)}))
    if not result['passed']:
        raise RuntimeError('Derivative acceptance failed; inspect retained receipt')


if __name__ == '__main__':
    main()

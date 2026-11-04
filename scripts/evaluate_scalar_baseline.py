"""Fit a train-only scalar baseline and evaluate complete frozen held-out partitions."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Complete baseline evaluation must run through Slurm')
    from universal_gnn.benchmarks.baselines import evaluate_scalar_mean

    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    result = evaluate_scalar_mean(json.loads(args.config.read_text(encoding='utf8')),args.output)
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() != commit:
        (args.output/'report.json').unlink()
        raise RuntimeError('Source checkout changed during baseline evaluation')
    result['execution'] = dict(git_commit=commit,slurm_job_id=os.environ['SLURM_JOB_ID'],device='cpu',
                              source_file=str(Path(__file__).resolve()))
    (args.output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps(result,allow_nan=False))


if __name__ == '__main__':
    main()

"""Prepare real diagnostic subsets under Slurm; never start training."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):parser.error('Diagnostic dataset preparation must run through Slurm')
    from universal_gnn.benchmarks.experiments.pilots import prepare_pilots
    result=prepare_pilots(json.loads(args.matrix.read_text()),args.output)
    print(json.dumps(dict(status=result['status'],pilot_cases=len(result['cases']),datasets=result['datasets'],
                          formal_training_runs=0,slurm_job_id=os.environ['SLURM_JOB_ID'])))


if __name__=='__main__':main()

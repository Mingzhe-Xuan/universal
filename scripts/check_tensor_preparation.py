"""Independently check both full supplemental tensor modes; never submit training."""
import argparse
import os
from pathlib import Path
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--definitions',type=Path,default=Path('runs/tensor-definition-control-1231/definitions/definitions.json'))
    parser.add_argument('--primary-matrix',type=Path,default=Path('runs/arxiv-v1/definition-947/matrix.json'))
    parser.add_argument('--pair',required=True)
    parser.add_argument('--preparation',type=Path,required=True)
    parser.add_argument('--receipt',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        parser.error('Independent full tensor preparation checks must run through Slurm')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output must be fresh')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
    from universal_gnn.benchmarks.execution.gates import compatible_sources,read_json,file_sha
    from universal_gnn.benchmarks.preflight import write_json
    from universal_gnn.benchmarks.submission.planning import finite_budget,measured_train_estimate,partition_maximum
    from universal_gnn.benchmarks.supplemental_tensors.gate import DEFINITION_SHA,tensor_case_spec,check_tensor_preparation
    commit=compatible_sources([])
    args.output.mkdir(parents=True,exist_ok=False)
    report=dict(status='running',stage='closed_tensor_definitions',kind='independent_supplemental_pair_preparation',
                pair_id=args.pair,git_commit=commit,slurm_job_id=os.environ['SLURM_JOB_ID'],
                formal_training_runs=0,new_training_jobs=0)
    def record(**fields):
        report.update(fields,updated_at=time.time());write_json(args.output/'report.json',report)
    try:
        record()
        if file_sha(args.definitions)!=DEFINITION_SHA:
            raise ValueError('Original accepted tensor definition bytes differ')
        primary,definitions=read_json(args.primary_matrix),read_json(args.definitions)
        cases=[c for c in definitions['cases'] if c['pair_id']==args.pair]
        if len(cases)!=2 or {c['initialization'] for c in cases}!={'pretrained','scratch'}:
            raise ValueError('Select one complete registered supplemental initialization pair')
        spec=tensor_case_spec(primary,definitions,cases[0]['id'])
        estimate=measured_train_estimate(args.preparation,spec)
        budget=finite_budget(estimate,partition_maximum())
        record(stage='independent_complete_source_graph_capacity_and_physics',definition_sha256=DEFINITION_SHA,
               budget_seconds=budget,probed_train_only_seconds=estimate,gates={})
        for case in cases:
            gate=check_tensor_preparation(args.definitions,case['id'],args.preparation,budget_seconds=budget,
                                          primary_path=args.primary_matrix,receipt_path=args.receipt)
            write_json(args.output/('gate-'+case['initialization']+'.json'),gate)
            report['gates'][case['initialization']]=dict(case_id=case['id'],status=gate['status'],
                sha256=file_sha(args.output/('gate-'+case['initialization']+'.json')))
            record(gates=report['gates'])
        record(status='passed',stage='complete',seed=123,model=cases[0]['model'],task=cases[0]['task'],
               common_batch_size=gate['common_batch_size'],counts=gate['counts'],
               interpretation='Independent complete two-mode supplemental preparation only; no training/post prediction or scientific accuracy claim')
    except Exception as error:
        record(status='failed',error_type=type(error).__name__,error=str(error));raise


if __name__=='__main__':main()

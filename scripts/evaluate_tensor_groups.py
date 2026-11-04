"""Independently assess saved test tensors by zero/nonzero target groups."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--shape',required=True,type=int,nargs='+')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Complete tensor assessment must run through Slurm')
    from universal_gnn.benchmarks.assessment import evaluate_tensor_groups

    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    result=evaluate_tensor_groups(args.report,args.output,shape=args.shape)
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=commit:
        (args.output/'report.json').unlink()
        raise RuntimeError('Source checkout changed during tensor assessment')
    paths=['src/universal_gnn/benchmarks/assessment/grouped.py',
           'src/universal_gnn/benchmarks/assessment/heldout.py',
           'src/universal_gnn/engine/evaluation/metrics.py',str(Path(__file__).relative_to(Path.cwd()))]
    result['execution']=dict(git_commit=commit,slurm_job_id=os.environ['SLURM_JOB_ID'],device='cpu',
                            source_sha256={path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths})
    (args.output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps(dict(status=result['status'],structures=result['structures'],output=str(args.output))))


if __name__=='__main__':main()

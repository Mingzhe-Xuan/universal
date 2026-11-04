"""Audit complete frozen material IDs against a published checkpoint's ID splits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--reference',required=True,type=Path)
    parser.add_argument('--reference-sha256',required=True)
    parser.add_argument('--id-prefix',required=True)
    parser.add_argument('--reference-target',required=True)
    parser.add_argument('--relation',required=True,choices=('same_target','derived_target','different_target','unknown'))
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Complete pretraining ID audit must run through Slurm')
    from universal_gnn.benchmarks.audits import audit_id_overlap

    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    result=audit_id_overlap(json.loads(args.config.read_text(encoding='utf8')),args.output,
        reference_archive=args.reference,reference_sha256=args.reference_sha256,id_prefix=args.id_prefix,
        reference_label_field=args.reference_target,target_relation=args.relation)
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=commit:
        (args.output/'report.json').unlink();raise RuntimeError('Source checkout changed during ID audit')
    paths=['src/universal_gnn/benchmarks/audits/overlap.py','src/universal_gnn/data/splits/manifest.py',
           str(Path(__file__).relative_to(Path.cwd()))]
    result['execution']=dict(git_commit=commit,slurm_job_id=os.environ['SLURM_JOB_ID'],device='cpu',
        source_sha256={path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths})
    (args.output/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf8')
    print(json.dumps(dict(status=result['status'],source_structures=result['source_structures'],counts=result['counts'])))


if __name__=='__main__':main()

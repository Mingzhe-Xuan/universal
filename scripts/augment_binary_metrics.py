"""Add balanced accuracy from original report counts without changing predictions or training."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, nargs='+', required=True)
    parser.add_argument('--property', default='classification')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        parser.error('Metric augmentation must run through Slurm')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output must be fresh; original reports remain immutable')
    if len({path.resolve() for path in args.reports}) != len(args.reports):
        parser.error('Duplicate source report')
    from universal_gnn.engine.evaluation.metrics import balanced_accuracy

    records = []
    for path in args.reports:
        raw = path.read_bytes()
        report = json.loads(raw)
        heldout = report['heldout']
        metric = heldout['metrics'][args.property]
        matrix = metric['confusion_matrix_true_by_predicted']
        score = balanced_accuracy(matrix)
        if (sum(sum(row) for row in matrix) != heldout['structures'] or
                metric['structures'] != heldout['structures']):
            raise ValueError('Original confusion counts differ from test coverage')
        records.append(dict(source_report=str(path), source_report_sha256=hashlib.sha256(raw).hexdigest(),
                            model=report['config']['backbone']['name'],
                            initialization=report['config']['backbone'].get('initialization','pretrained'),
                            property=args.property, metrics={**metric,'balanced_accuracy':score,
                            'balanced_accuracy_policy':'mean of both true-class recalls; single-class null'}))
    value = dict(version=1, kind='binary_metric_augmentation', records=records,
                 git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                 slurm_job_id=os.environ['SLURM_JOB_ID'],
                 interpretation='derived from original test confusion counts; no new training or predictions')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status='complete', reports=len(records), output=str(args.output))))


if __name__ == '__main__':
    main()

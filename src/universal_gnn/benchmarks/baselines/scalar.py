"""Streaming scalar mean baseline; no graph construction or model imports."""
import hashlib
import json
import math
from pathlib import Path

from universal_gnn.data.splits.manifest import validate_manifest
from universal_gnn.engine.evaluation.metrics import RegressionMetrics
from universal_gnn.benchmarks.experiments.registry import canonical_digest


def evaluate_scalar_mean(config, output):
    if (config.get('structures') != 'all' or config.get('max_atoms') is not None or
            config.get('task', {}).get('kind') != 'supervised'):
        raise ValueError('Scalar baseline requires a complete supervised dataset without atom cropping')
    settings = config['dataset']
    if settings.get('partition') != 'train':
        raise ValueError('The mean must be fitted on the training partition')
    property_name = config['task']['property']
    binding = settings['bindings'][property_name]
    if set(binding) != {'key', 'unit'} or not all(isinstance(v, str) and v for v in binding.values()):
        raise ValueError('Scalar baseline requires an explicit raw-label key and unit')
    source = Path(settings['path'])
    manifest = json.loads(Path(settings['split_manifest']).read_text(encoding='utf8'))
    validate_manifest(manifest, source_sha256=settings['sha256'], source_count=manifest['source_count'])
    manifest_sha = canonical_digest(manifest)
    if manifest_sha != settings['split_manifest_sha256']:
        raise ValueError('Scalar baseline manifest fingerprint changed')
    roles = [None] * manifest['source_count']
    for role, indices in manifest['partitions'].items():
        for index in indices:
            roles[index] = role

    def rows():
        digest = hashlib.sha256()
        count = 0
        with source.open('rb') as stream:
            for raw in stream:
                digest.update(raw)
                if not raw.strip():
                    continue
                row = json.loads(raw)
                if count >= len(roles) or row.get('id') != manifest['records'][count]['id']:
                    raise ValueError('Scalar baseline source IDs/order changed')
                value = row['targets'][binding['key']]
                while isinstance(value, (list, tuple)) and len(value) == 1:
                    value = value[0]
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValueError('Scalar baseline requires one finite label per structure')
                yield row['id'], roles[count], float(value)
                count += 1
        if count != len(roles) or digest.hexdigest() != settings['sha256']:
            raise ValueError('Scalar baseline source fingerprint/count changed')

    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refusing to overwrite an existing baseline output')
    n, mean = 0, 0.
    for identifier, role, value in rows():
        if role == 'train':
            n += 1
            mean += (value - mean) / n
    if n != manifest['counts']['train'] or not math.isfinite(mean):
        raise ValueError('Training mean/count is invalid')
    output.mkdir(parents=True)
    accumulators = {role: RegressionMetrics() for role in ['validation', 'test']}
    prediction_path = output / 'predictions.jsonl'
    partial = output / 'predictions.jsonl.partial'
    with partial.open('x', encoding='utf8') as stream:
        for identifier, role, value in rows():
            if role in accumulators:
                accumulators[role].update(mean, value)
                stream.write(json.dumps(dict(id=identifier, partition=role, prediction=mean,
                                             target=value, unit=binding['unit']), allow_nan=False)+'\n')
    partitions = {}
    for role, accumulator in accumulators.items():
        metrics = accumulator.result()
        if metrics['structures'] != manifest['counts'][role]:
            raise ValueError('Scalar baseline held-out count differs from manifest')
        partitions[role] = dict(structures=metrics['structures'], mae=metrics['mae'], rmse=metrics['rmse'],
                                unit=binding['unit'])
    partial.replace(prediction_path)
    result = dict(status='passed',kind='scalar_training_mean_baseline',property=property_name,
                  source_sha256=settings['sha256'],split_manifest_sha256=manifest_sha,
                  source_structures=manifest['source_count'],training_structures=n,training_mean=mean,
                  unit=binding['unit'],partitions=partitions,predictions=str(prediction_path),
                  config_sha256=canonical_digest(config),formal_training_runs=0,
                  evaluation_arithmetic='Python float64 on raw stored labels',
                  interpretation='One mean fitted only on train; all validation/test labels independently scored')
    (output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf8')
    return result

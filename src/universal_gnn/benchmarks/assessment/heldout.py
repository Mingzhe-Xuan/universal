"""Rescore complete saved test predictions against their exact source labels."""
import hashlib
import json
import math
from pathlib import Path
import struct

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.data.splits.manifest import validate_manifest
from .grouped import GroupedRegressionMetrics, tensor_values


def evaluate_tensor_groups(training_report, output, *, shape):
    """No model imports or inference; only explicit graph-level identity-bound labels."""
    report_path, output = Path(training_report), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refusing to overwrite an existing assessment output')
    raw_report = report_path.read_bytes()
    trained = json.loads(raw_report)
    config, heldout = trained['config'], trained['heldout']
    if (not trained.get('passed') or config.get('structures') != 'all' or config.get('max_atoms') is not None or
            config.get('task', {}).get('kind') != 'supervised' or config['dataset'].get('partition') != 'train' or
            heldout.get('partition') != 'test' or heldout.get('checkpoint_role') != 'validation_best'):
        raise ValueError('Assessment requires a passed complete supervised validation-best test report')
    name, settings = config['task']['property'], config['dataset']
    binding = settings['bindings'][name]
    if (not isinstance(binding, dict) or set(binding) != {'key', 'unit'} or
            not all(isinstance(value, str) and value for value in binding.values())):
        raise ValueError('Assessment supports explicit raw-label key/unit bindings without transforms')
    dtype = config.get('dtype')
    if dtype not in {'float32', 'float64'}:
        raise ValueError('Assessment requires an explicit supported prediction dtype')
    manifest = json.loads(Path(settings['split_manifest']).read_text(encoding='utf8'))
    validate_manifest(manifest, source_sha256=settings['sha256'], source_count=manifest['source_count'])
    manifest_sha = canonical_digest(manifest)
    if manifest_sha != settings['split_manifest_sha256'] or heldout['source_sha256'] != settings['sha256']:
        raise ValueError('Assessment source/manifest fingerprint changed')
    if (trained['selected_structures'] != manifest['counts']['train'] or
            heldout['declared_train_structures'] != manifest['counts']['train'] or
            heldout['validation_structures'] != manifest['counts']['validation'] or
            heldout['source_structures'] != manifest['source_count']):
        raise ValueError('Original report does not describe the complete frozen partition counts')
    expected = {manifest['records'][index]['id'] for index in manifest['partitions']['test']}
    if heldout['structures'] != len(expected) or heldout['test_structures'] != len(expected):
        raise ValueError('Held-out report does not describe the complete declared test partition')
    metrics = GroupedRegressionMetrics(shape)
    labels, source_hash, source_count = {}, hashlib.sha256(), 0
    with Path(settings['path']).open('rb') as stream:
        for raw in stream:
            source_hash.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw)
            if source_count >= manifest['source_count'] or row.get('id') != manifest['records'][source_count]['id']:
                raise ValueError('Assessment source IDs/order changed')
            if row['id'] in expected:
                values = tensor_values(row['targets'][binding['key']], metrics.shape, missing=True)
                labels[row['id']] = [struct.unpack('f', struct.pack('f', value))[0]
                                     if dtype == 'float32' else value for value in values]
            source_count += 1
    if source_count != manifest['source_count'] or source_hash.hexdigest() != settings['sha256']:
        raise ValueError('Assessment source fingerprint/count changed')
    output.mkdir(parents=True)
    predictions = Path(heldout['predictions'])
    prediction_hash, seen = hashlib.sha256(), set()
    partial = output / 'groups.jsonl.partial'
    with partial.open('x', encoding='utf8') as grouped, predictions.open('rb') as stream:
        for raw in stream:
            prediction_hash.update(raw)
            row = json.loads(raw)
            identifier = row['id']
            if identifier not in expected or identifier in seen:
                raise ValueError('Prediction ID is duplicated or outside the declared test partition')
            target, prediction = row['targets'][name], row['predictions'][name]
            if not isinstance(target, list) or len(target) != 1 or not isinstance(prediction, list) or len(prediction) != 1:
                raise ValueError('Saved graph-level tensor requires one leading structure dimension')
            observed = tensor_values(target[0], metrics.shape, missing=True)
            if any((actual != original) if math.isfinite(actual) and math.isfinite(original)
                   else math.isfinite(actual) != math.isfinite(original)
                   for actual, original in zip(observed, labels[identifier])):
                raise ValueError('Saved target differs from the original dtype-bound source label')
            group = metrics.update(prediction[0], target[0])
            grouped.write(json.dumps(dict(id=identifier, group=group), allow_nan=False) + '\n')
            seen.add(identifier)
    if seen != expected:
        raise ValueError('Saved predictions omit declared test structures')
    result = metrics.result()
    reference, actual = heldout['metrics'][name], result['overall']['metrics']
    if actual is None:
        raise ValueError('No finite assessment labels')
    for field in ('structures', 'finite_elements', 'masked_target_elements', 'zero_norm_target_structures'):
        if actual[field] != reference[field]:
            raise ValueError('Recomputed overall metric population differs from the original report')
    for field in ('mae', 'rmse', 'mean_structure_frobenius_error'):
        if not math.isclose(actual[field], reference[field], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError('Recomputed overall errors differ from the original report')
    partial.replace(output / 'groups.jsonl')
    result.update(status='passed', kind='heldout_tensor_zero_nonzero_assessment', property=name, unit=binding['unit'],
                  source_structures=source_count, source_sha256=source_hash.hexdigest(),
                  split_manifest_sha256=manifest_sha, prediction_sha256=prediction_hash.hexdigest(),
                  training_report_sha256=hashlib.sha256(raw_report).hexdigest(),
                  config_sha256=canonical_digest(config), dtype=dtype,
                  best_checkpoint_sha256=heldout['selection']['best_sha256'], checkpoint_role='validation_best',
                  formal_training_runs=0,
                  interpretation='Saved test predictions independently rescored; no symmetry projection or new inference')
    (output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf8')
    return result

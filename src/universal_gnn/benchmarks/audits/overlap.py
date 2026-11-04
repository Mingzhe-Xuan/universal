"""Audit published material-ID exposure without claiming geometric disjointness."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.data.splits.manifest import validate_manifest

ROLES = ('train', 'validation', 'test')
REFERENCE_KEYS = dict(train='id_train', validation='id_val', test='id_test')
RELATIONS = ('same_target', 'derived_target', 'different_target', 'unknown')


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_reference_splits(archive, expected_sha256, *, policy='strict'):
    if policy not in {'strict', 'report_ambiguity'}:
        raise ValueError('Unknown published-reference integrity policy')
    if (not isinstance(expected_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_sha256) or
            file_digest(archive) != expected_sha256):
        raise ValueError('Published reference archive fingerprint changed')
    with zipfile.ZipFile(archive) as zipped:
        def read(name):
            members = [member for member in zipped.namelist() if member == name or member.endswith('/' + name)]
            if len(members) != 1:
                raise ValueError('Published reference requires one unambiguous ' + name)
            return zipped.read(members[0])
        raw_ids, raw_config = read('ids_train_val_test.json'), read('config.json')
    ids, config = json.loads(raw_ids), json.loads(raw_config)
    if not isinstance(ids, dict) or set(ids) != set(REFERENCE_KEYS.values()):
        raise ValueError('Published reference must explicitly identify all three partitions')
    seen, splits, ambiguous = set(), {}, set()
    for role, key in REFERENCE_KEYS.items():
        values = ids[key]
        if (not isinstance(values, list) or not values or
                any(not isinstance(value, str) or not value for value in values) or
                len(set(values)) != len(values)):
            raise ValueError('Published reference IDs must be unique within each partition')
        overlap = seen.intersection(values)
        if overlap and policy == 'strict':
            raise ValueError('Published reference IDs must be disjoint across partitions')
        ambiguous.update(overlap)
        declared = config.get({'train': 'n_train', 'validation': 'n_val', 'test': 'n_test'}[role])
        if type(declared) is not int or declared != len(values):
            raise ValueError('Published reference config/ID partition counts disagree')
        seen.update(values);splits[role] = values
    return dict(splits=splits, archive_sha256=expected_sha256,
                ids_sha256=hashlib.sha256(raw_ids).hexdigest(),
                config_sha256=hashlib.sha256(raw_config).hexdigest(),
                counts={role: len(values) for role, values in splits.items()},
                integrity_policy=policy, mutually_disjoint=not ambiguous,
                cross_partition_ids=sorted(ambiguous), unique_reference_ids=len(seen))


def audit_id_overlap(config, output, *, reference_archive, reference_sha256,
                     id_prefix, reference_label_field, target_relation, reference_policy='strict'):
    """Inspect every frozen source ID; missing ID membership is not a no-leakage claim."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('Refusing to overwrite an existing overlap audit')
    if (config.get('structures') != 'all' or config.get('max_atoms') is not None or
            config['dataset'].get('partition') != 'train'):
        raise ValueError('Overlap audit requires the complete frozen training-source configuration')
    if (target_relation not in RELATIONS or not isinstance(id_prefix, str) or not id_prefix or
            not isinstance(reference_label_field, str) or not reference_label_field):
        raise ValueError('Declare a reference label field, ID namespace prefix and target relation')
    reference = read_reference_splits(reference_archive, reference_sha256, policy=reference_policy)
    lookup = {}
    for role, values in reference['splits'].items():
        for identifier in values:
            lookup.setdefault(identifier, []).append(role)
    if any(not identifier.startswith(id_prefix) for identifier in lookup):
        raise ValueError('Published IDs do not share the declared namespace')
    settings = config['dataset']
    manifest = json.loads(Path(settings['split_manifest']).read_text(encoding='utf8'))
    validate_manifest(manifest, source_sha256=settings['sha256'], source_count=manifest['source_count'])
    manifest_sha = canonical_digest(manifest)
    if manifest_sha != settings['split_manifest_sha256']:
        raise ValueError('Current source manifest fingerprint changed')
    roles = [None] * manifest['source_count']
    for role, indices in manifest['partitions'].items():
        for index in indices:
            roles[index] = role
    categories = (*ROLES, 'not_listed', 'multiple_roles') if reference_policy == 'report_ambiguity' else (*ROLES, 'not_listed')
    bins = {role: {key: 0 for key in categories} for role in ROLES}
    training_exposure = {role: 0 for role in ROLES}
    selection_exposure = {role: 0 for role in ROLES}
    output.mkdir(parents=True)
    partial = output / 'id-overlap.jsonl.partial'
    digest, count = hashlib.sha256(), 0
    with Path(settings['path']).open('rb') as stream, partial.open('x', encoding='utf8') as results:
        for raw in stream:
            digest.update(raw)
            if not raw.strip():
                continue
            row = json.loads(raw);identifier = row.get('id')
            if count >= len(roles) or identifier != manifest['records'][count]['id']:
                raise ValueError('Current source IDs/order changed')
            if not identifier.startswith(id_prefix):
                raise ValueError('Current and published IDs have incompatible namespaces')
            field = row.get('metadata', {}).get('label_field')
            if target_relation != 'unknown':
                if not isinstance(field, str) or not field:
                    raise ValueError('Current raw target field is not auditable')
                same = field == reference_label_field
                if same != (target_relation in {'same_target', 'derived_target'}):
                    raise ValueError('Declared target relation disagrees with the current raw label field')
            memberships = lookup.get(identifier, [])
            published = ('multiple_roles' if len(memberships) > 1 else memberships[0]) if memberships else 'not_listed'
            role = roles[count]
            bins[role][published] += 1
            training_exposure[role] += 'train' in memberships
            selection_exposure[role] += 'validation' in memberships
            results.write(json.dumps(dict(id=identifier, partition=role, reference_partition=published,
                                          reference_memberships=memberships)) + '\n')
            count += 1
    if count != manifest['source_count'] or digest.hexdigest() != settings['sha256']:
        raise ValueError('Current source fingerprint/count changed')
    if any(sum(bins[role].values()) != manifest['counts'][role] for role in ROLES):
        raise ValueError('Overlap audit omitted current partition records')
    partial.replace(output / 'id-overlap.jsonl')
    result = dict(status='passed', kind='published_material_id_overlap', source_structures=count,
                  source_sha256=digest.hexdigest(), split_manifest_sha256=manifest_sha,
                  config_sha256=canonical_digest(config), reference={key: value for key, value in reference.items() if key != 'splits'},
                  id_prefix=id_prefix, reference_label_field=reference_label_field, target_relation=target_relation,
                  counts=bins, current_partition_counts=manifest['counts'], formal_training_runs=0,
                  parameter_training_id_matches=training_exposure, model_selection_id_matches=selection_exposure,
                  label_disjointness='not established by ID membership alone',
                  reference_validation_policy='selection exposure recorded separately from parameter-training exposure',
                  not_listed_policy='absent from this published ID roster; not proof of unseen geometry or labels',
                  limitations='Exact label values and geometry at pretraining time are not reconstructed; no cross-ID crystal equivalence matching')
    (output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf8')
    return result

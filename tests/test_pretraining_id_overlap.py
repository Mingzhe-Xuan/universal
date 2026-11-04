import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from universal_gnn.benchmarks.audits import audit_id_overlap, read_reference_splits
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.data.splits.manifest import create_manifest


def fixture(root):
    ids = {'id_train': ['JVASP-1', 'JVASP-5', 'JVASP-9'],
           'id_val': ['JVASP-2', 'JVASP-6'], 'id_test': ['JVASP-3', 'JVASP-7']}
    archive = root / 'reference.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('config.json', json.dumps(dict(n_train=3, n_val=2, n_test=2)))
        zipped.writestr('ids_train_val_test.json', json.dumps(ids))
    rows = [dict(id='JVASP-' + str(i), metadata=dict(label_field='gap')) for i in range(1, 10)]
    source = root / 'source.jsonl'
    source.write_bytes(b''.join((json.dumps(row) + '\n').encode() for row in rows))
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    records = [dict(id=row['id'], group=row['id']) for row in rows]
    roles = {row['id']: 'train' if i < 3 else 'validation' if i < 6 else 'test' for i, row in enumerate(rows)}
    manifest = create_manifest(records, source_sha256=sha, official=roles)
    split = root / 'split.json';split.write_text(json.dumps(manifest))
    config = dict(structures='all', dataset=dict(path=str(source), sha256=sha, partition='train',
                  split_manifest=str(split), split_manifest_sha256=canonical_digest(manifest)))
    options = dict(reference_archive=archive, reference_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                   id_prefix='JVASP-', reference_label_field='gap', target_relation='same_target')
    return config, options, ids


class PretrainingIDOverlapTests(unittest.TestCase):
    def test_all_source_partitions_and_published_exposure_categories(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config,options,_=fixture(root);before=copy.deepcopy(config)
            report=audit_id_overlap(config,root/'out',**options)
            self.assertEqual(config,before)
            self.assertEqual(report['source_structures'],9)
            self.assertEqual(report['counts'],dict(train=dict(train=1,validation=1,test=1,not_listed=0),
             validation=dict(train=1,validation=1,test=0,not_listed=1),test=dict(train=1,validation=0,test=1,not_listed=1)))
            self.assertEqual(report['reference']['counts'],dict(train=3,validation=2,test=2))
            self.assertEqual(report['label_disjointness'],'not established by ID membership alone')
            self.assertEqual(report['formal_training_runs'],0)
            rows=[json.loads(line) for line in (root/'out/id-overlap.jsonl').read_text().splitlines()]
            self.assertEqual([row['id'] for row in rows],['JVASP-'+str(i) for i in range(1,10)])
            self.assertEqual(rows[7]['reference_partition'],'not_listed')

    def test_target_relations_and_unknown_do_not_claim_no_leakage(self):
        for relation in ['same_target','derived_target','different_target','unknown']:
            with self.subTest(relation=relation),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config,options,_=fixture(root);options['target_relation']=relation
                if relation=='different_target':options['reference_label_field']='another_label'
                report=audit_id_overlap(config,root/'out',**options)
                self.assertEqual(report['target_relation'],relation)
                self.assertIn('not proof',report['not_listed_policy'])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config,options,_=fixture(root);options['target_relation']='different_target'
            with self.assertRaisesRegex(ValueError,'relation'):audit_id_overlap(config,root/'out',**options)
            self.assertFalse((root/'out/report.json').exists())

    def test_reference_archive_hash_counts_duplicates_and_role_leakage(self):
        for change in ['hash','counts','duplicate','cross_role','missing_role']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);_,options,ids=fixture(root)
                if change=='hash':options['reference_sha256']='0'*64
                else:
                    if change=='duplicate':ids['id_train'][1]=ids['id_train'][0]
                    if change=='cross_role':ids['id_val'][0]=ids['id_train'][0]
                    if change=='missing_role':del ids['id_test']
                    with zipfile.ZipFile(options['reference_archive'],'w') as zipped:
                        zipped.writestr('config.json',json.dumps(dict(n_train=4 if change=='counts' else 3,n_val=2,n_test=2)))
                        zipped.writestr('ids_train_val_test.json',json.dumps(ids))
                    options['reference_sha256']=hashlib.sha256(options['reference_archive'].read_bytes()).hexdigest()
                with self.assertRaises(ValueError):read_reference_splits(options['reference_archive'],options['reference_sha256'])
                if change!='cross_role':
                    with self.assertRaises(ValueError):
                        read_reference_splits(options['reference_archive'],options['reference_sha256'],policy='report_ambiguity')

    def test_current_source_fingerprint_order_and_manifest(self):
        for change in ['bytes','manifest','order','truncation']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config,options,_=fixture(root)
                if change=='bytes':
                    with Path(config['dataset']['path']).open('ab') as stream:stream.write(b' \n')
                elif change=='truncation':
                    source=Path(config['dataset']['path']);source.write_bytes(b''.join(source.read_bytes().splitlines(keepends=True)[:-1]))
                else:
                    manifest=json.loads((root/'split.json').read_text());manifest['records'][0]['id']='JVASP-999'
                    (root/'split.json').write_text(json.dumps(manifest))
                    if change=='order':config['dataset']['split_manifest_sha256']=canonical_digest(manifest)
                with self.assertRaisesRegex(ValueError,'fingerprint|IDs/order'):
                    audit_id_overlap(config,root/'out',**options)
                self.assertFalse((root/'out/report.json').exists())

    def test_namespace_debug_selection_invalid_relation_and_output_refused(self):
        for change in ['namespace','subset','partition','relation']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config,options,_=fixture(root)
                if change=='namespace':options['id_prefix']='mp-'
                elif change=='subset':config['structures']=2
                elif change=='partition':config['dataset']['partition']='test'
                else:options['target_relation']='no_leakage'
                with self.assertRaises(ValueError):audit_id_overlap(config,root/'out',**options)
                self.assertFalse((root/'out/report.json').exists())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config,options,_=fixture(root);(root/'out').mkdir();(root/'out/keep').write_text('keep')
            with self.assertRaises(FileExistsError):audit_id_overlap(config,root/'out',**options)
            self.assertEqual((root/'out/keep').read_text(),'keep')

    def test_source_namespace_is_verified_even_with_valid_fingerprints(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config,options,_=fixture(root)
            source=Path(config['dataset']['path']);rows=[json.loads(line) for line in source.read_text().splitlines()]
            rows[0]['id']='mp-1';source.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            manifest=json.loads((root/'split.json').read_text());manifest['records'][0]['id']='mp-1'
            sha=hashlib.sha256(source.read_bytes()).hexdigest();manifest['source_sha256']=sha
            (root/'split.json').write_text(json.dumps(manifest))
            config['dataset'].update(sha256=sha,split_manifest_sha256=canonical_digest(manifest))
            with self.assertRaisesRegex(ValueError,'namespaces'):audit_id_overlap(config,root/'out',**options)
            self.assertFalse((root/'out/report.json').exists())

    def test_explicit_ambiguity_reporting_preserves_all_roles_and_training_exposure(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config,options,ids=fixture(root)
            ids['id_val'][0]='JVASP-1';ids['id_test'][0]='JVASP-5'
            with zipfile.ZipFile(options['reference_archive'],'w') as zipped:
                zipped.writestr('config.json',json.dumps(dict(n_train=3,n_val=2,n_test=2)))
                zipped.writestr('ids_train_val_test.json',json.dumps(ids))
            options['reference_sha256']=hashlib.sha256(options['reference_archive'].read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'disjoint'):
                audit_id_overlap(config,root/'strict',**options)
            self.assertFalse((root/'strict/report.json').exists())
            result=audit_id_overlap(config,root/'report',reference_policy='report_ambiguity',**options)
            self.assertFalse(result['reference']['mutually_disjoint'])
            self.assertEqual(result['reference']['cross_partition_ids'],['JVASP-1','JVASP-5'])
            self.assertEqual(result['counts']['train'],dict(train=0,validation=0,test=0,not_listed=2,multiple_roles=1))
            self.assertEqual(result['parameter_training_id_matches'],dict(train=1,validation=1,test=1))
            self.assertEqual(result['model_selection_id_matches'],dict(train=1,validation=1,test=0))
            rows=[json.loads(line) for line in (root/'report/id-overlap.jsonl').read_text().splitlines()]
            self.assertEqual(rows[0]['reference_memberships'],['train','validation'])
            self.assertEqual(rows[4]['reference_memberships'],['train','test'])
            self.assertEqual(rows[4]['reference_partition'],'multiple_roles')
            self.assertEqual(result['label_disjointness'],'not established by ID membership alone')


if __name__=='__main__':unittest.main()

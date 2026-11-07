"""Small metadata/archive fixtures; they are not actual full-source evidence."""

from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch

from test_arxiv_experiment_definitions import registry_fixture
from universal_gnn.benchmarks.experiments import bundle
from universal_gnn.benchmarks.experiments.recipes import build_matrix


@contextmanager
def fixture():
    matrix = build_matrix(registry_fixture())
    digest = bundle.canonical_digest(matrix)
    active = [row['id'] for row in matrix['cases'] if row['seed'] == 123]
    excluded = [row['id'] for row in matrix['cases'] if row['seed'] != 123]
    scope = dict(base_matrix_sha256=digest, active_case_ids=active, excluded_case_ids=excluded,
        training_seeds=[123], expected_training_runs=48)
    raw = json.dumps(matrix).encode()
    scope_raw = json.dumps(scope).encode()
    with patch.object(bundle,'MATRIX_SHA',digest),patch.object(bundle,'SCOPE_SHA',bundle.sha(scope_raw)):
        yield matrix, scope, raw, scope_raw


def payloads(matrix, scope, raw, scope_raw):
    result = {'matrix.json':raw,'scope.json':scope_raw,'registry.json':json.dumps(matrix['registry']).encode(),
        'README.md':b'Metadata unit fixture only; not actual input-data acceptance.\n',
        'models/official/cgcnn/atom_init.json':b'{}',
        'models/official/nequip/NequIP-OAM-S_pretrain_config.yaml':b'fixture: true\n'}
    for row in matrix['cases']:
        if row['id'] in scope['active_case_ids']:
            result[row['config_path']] = json.dumps(row['config']).encode()
    for name in bundle.DATASETS:
        for filename in ['split.json','audit.json','exclusions.jsonl']:
            result['data/arxiv-v1/'+name+'/'+filename] = b'{}' if filename.endswith('.json') else b''
    manifest = dict(kind='arxiv_v1_frozen_inputs_only',active_case_ids=scope['active_case_ids'],definition_configs=48,
        dataset_count=5,scientific_acceptance=False,preflight_still_required=True,structures_and_learned_weights_included=False,
        members={name:dict(bytes=len(body),sha256=bundle.sha(body)) for name,body in result.items()})
    result['manifest.json'] = json.dumps(manifest).encode()
    return result


class InputBundleTests(unittest.TestCase):
    def test_original144_and_only48_active_definition_configs_are_preserved(self):
        with fixture() as (matrix,scope,raw,scope_raw):
            checked, selected, active = bundle.checked_definitions(raw,scope_raw)
            self.assertEqual(checked,matrix)
            self.assertEqual(selected,scope)
            self.assertEqual(len(active),48)
            self.assertEqual({row['seed'] for row in active},{123})
            self.assertEqual(len(matrix['cases']),144)

    def test_raw_scope_and_canonical_matrix_identity_are_distinct(self):
        with fixture() as (matrix,scope,raw,scope_raw):
            self.assertEqual(len(bundle.checked_definitions(json.dumps(matrix,indent=2).encode(),scope_raw)[2]),48)
            with self.assertRaises(ValueError):bundle.checked_definitions(raw,scope_raw+b'\n')
            matrix['status'] = 'tampered'
            with self.assertRaises(ValueError):bundle.checked_definitions(json.dumps(matrix).encode(),scope_raw)

    def test_missing_duplicate_or_excluded_active_ids_refuse_even_with_self_consistent_scope_hash(self):
        for change in ['missing','duplicate','excluded','seed']:
            with self.subTest(change=change),fixture() as (_,scope,raw,__):
                if change=='missing':scope['active_case_ids'].pop()
                elif change=='duplicate':scope['active_case_ids'][0]=scope['active_case_ids'][1]
                elif change=='excluded':scope['active_case_ids'][0]=scope['excluded_case_ids'][0]
                else:scope['training_seeds']=[456]
                encoded=json.dumps(scope).encode()
                with patch.object(bundle,'SCOPE_SHA',bundle.sha(encoded)),self.assertRaises(ValueError):
                    bundle.checked_definitions(raw,encoded)

    def test_bad_registry_or_config_digest_refuses_after_outer_digest_is_consistent(self):
        for change in ['registry','config']:
            with self.subTest(change=change),fixture() as (matrix,scope,_,__):
                if change=='registry':matrix['registry']['datasets']['jarvis-gap']['structures']=10
                else:matrix['cases'][0]['config']['batch_size']=1
                digest=bundle.canonical_digest(matrix)
                scope['base_matrix_sha256']=digest
                raw,scope_raw=json.dumps(matrix).encode(),json.dumps(scope).encode()
                with patch.object(bundle,'MATRIX_SHA',digest),patch.object(bundle,'SCOPE_SHA',bundle.sha(scope_raw)),self.assertRaises(ValueError):
                    bundle.checked_definitions(raw,scope_raw)

    def test_unsafe_relative_names_include_windows_streams_and_traversal(self):
        for name in ['', '../x', '/x', 'C:/x', 'a\\b', 'a//b', 'a/../b', '.git/config', 'a/b:stream', 'a\nb', 'a\tb', 'directory/']:
            with self.subTest(name=name),self.assertRaises(ValueError):bundle.safe_name(name)

    def test_deterministic_zip_metadata_preserve_exact_bytes_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            first,second=Path(directory)/'a.zip',Path(directory)/'b.zip'
            bodies={'z.txt':b'line\r\n','a.txt':'元素'.encode('utf8')}
            bundle.write_payload_archive(first,bodies)
            bundle.write_payload_archive(second,dict(reversed(list(bodies.items()))))
            self.assertEqual(first.read_bytes(),second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(archive.namelist(),['a.txt','z.txt'])
                self.assertEqual(archive.read('z.txt'),b'line\r\n')
                self.assertTrue(all(row.date_time==(1980,1,1,0,0,0) for row in archive.infolist()))

    def test_existing_output_empty_or_nonbyte_payload_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'archive.zip'
            for values in [{},{'file.txt':'not bytes'},{'../escape':b'bytes'}]:
                with self.assertRaises((ValueError,TypeError)):bundle.write_payload_archive(path,values)
                self.assertFalse(path.exists())
            bundle.write_payload_archive(path,{'file.txt':b'bytes'})
            with self.assertRaises(FileExistsError):bundle.write_payload_archive(path,{'file.txt':b'new'})

    def test_archive_readback_checks_all_members_and_definition_configs(self):
        with fixture() as values,tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'archive.zip'
            bodies=payloads(*values)
            bundle.write_payload_archive(path,bodies)
            manifest=bundle.verify_archive(path)
            self.assertEqual(manifest['definition_configs'],48)
            self.assertEqual(len(manifest['members'])+1,len(bodies))
            self.assertFalse(manifest['scientific_acceptance'])
            self.assertTrue(manifest['preflight_still_required'])

    def test_tampered_member_missing_member_and_invented_readiness_refuse(self):
        for change in ['bytes','missing','claim','registry','extra_weight']:
            with self.subTest(change=change),fixture() as values,tempfile.TemporaryDirectory() as directory:
                bodies=payloads(*values)
                if change=='bytes':bodies['README.md']=b'changed'
                elif change=='missing':del bodies['models/official/cgcnn/atom_init.json']
                elif change=='claim':
                    manifest=json.loads(bodies['manifest.json']);manifest['scientific_acceptance']=True
                    bodies['manifest.json']=json.dumps(manifest).encode()
                elif change=='registry':bodies['registry.json']=b'{}'
                else:
                    bodies['weight.pt']=b'not an allowed metadata member'
                    manifest=json.loads(bodies['manifest.json'])
                    manifest['members']['weight.pt']=dict(bytes=len(bodies['weight.pt']),sha256=bundle.sha(bodies['weight.pt']))
                    bodies['manifest.json']=json.dumps(manifest).encode()
                path=Path(directory)/'archive.zip';bundle.write_payload_archive(path,bodies)
                with self.assertRaises(ValueError):bundle.verify_archive(path)

    def test_duplicate_or_symlink_zip_members_refuse_without_extraction(self):
        for change in ['duplicate','symlink']:
            with self.subTest(change=change),fixture() as values,tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'archive.zip';bundle.write_payload_archive(path,payloads(*values))
                with warnings.catch_warnings(),zipfile.ZipFile(path,'a') as archive:
                    warnings.simplefilter('ignore',UserWarning)
                    if change=='duplicate':archive.writestr('README.md',b'duplicate')
                    else:
                        entry=zipfile.ZipInfo('link');entry.create_system=3;entry.external_attr=0o120777<<16
                        archive.writestr(entry,b'/outside')
                with self.assertRaises(ValueError):bundle.verify_archive(path)

    def test_full_export_refuses_missing_slurm_before_reading_any_inputs(self):
        with patch.dict(os.environ,{},clear=True),self.assertRaises(RuntimeError):
            bundle.export_inputs('absent','absent','absent','absent')

    def test_public_cli_refuses_missing_slurm(self):
        repository=Path(__file__).resolve().parents[1]
        env=dict(os.environ,PYTHONPATH=str(repository/'src'));env.pop('SLURM_JOB_ID',None)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'never-created'
            result=subprocess.run([sys.executable,'-S',str(repository/'scripts/export_arxiv_inputs.py'),
                '--repository','absent','--matrix','absent','--output',str(output)],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('CPU Slurm',result.stderr)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()

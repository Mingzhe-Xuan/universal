"""Pure full-definition and source-reader controls; no model imports."""
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.supplemental_tensors import experiments as module
from universal_gnn.data.splits import create_manifest

registry_fixture=runpy.run_path(str(Path(__file__).with_name("test_arxiv_experiment_definitions.py")))["registry_fixture"]


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(json.dumps(value,allow_nan=False).encode())


def nested(rank, value):
    return value if rank==0 else [nested(rank-1,value) for _ in range(3)]


@contextmanager
def sources():
    with tempfile.TemporaryDirectory() as folder:
        before=Path.cwd();os.chdir(folder)
        try:
            root=Path(module.DATA_ROOT);root.mkdir(parents=True)
            write(root/'report.json',dict(status='passed',source='fixture'))
            verified=Path('runs/supplemental-tensor-verification-1075/report.json');write(verified,dict(status='passed',source='fixture'))
            datasets={}
            for task,rank in [('piezoelectric',3),('elastic',4)]:
                rows=[dict(id=task+str(i),group=task+str(i),targets={task:nested(rank,0. if i==0 else 10**i)}) for i in range(3)]
                path=root/task/'structures.jsonl';path.parent.mkdir();path.write_bytes(b''.join((json.dumps(row)+'\n').encode() for row in rows))
                sha=hashlib.sha256(path.read_bytes()).hexdigest()
                manifest=create_manifest(rows,source_sha256=sha,official={rows[i]['id']:role for i,role in enumerate(['train','validation','test'])})
                write(root/task/'split.json',manifest)
                datasets[task]=dict(sha256=sha,split_manifest_sha256=canonical_digest(manifest),counts=manifest['counts'],structures=3)
            with patch.object(module,'DATASETS',datasets),patch.object(module,'PREPARATION_SHA',module.file_sha(root/'report.json')),patch.object(module,'VERIFICATION_SHA',module.file_sha(verified)):
                yield root,datasets
        finally:os.chdir(before)


class TensorExperimentDefinitions(unittest.TestCase):
    def setUp(self):
        self.primary=build_matrix(registry_fixture())
        self.guard=patch.object(module,'PRIMARY_SHA',canonical_digest(self.primary));self.guard.start();self.addCleanup(self.guard.stop)

    def test_complete_separate16_seed123_and_original_templates_unchanged(self):
        before=copy.deepcopy(self.primary);result=module.build_tensor_definitions(self.primary)
        self.assertEqual(self.primary,before)
        self.assertEqual(result['training_seeds'],[123]);self.assertEqual(result['defined_training_runs'],16)
        self.assertEqual(result['formal_training_runs'],0);self.assertEqual(len(result['pairs']),8)
        self.assertEqual(len({c['id'] for c in result['cases']}),16)
        for case in result['cases']:
            template=next(c for c in self.primary['cases'] if c['id']=='seed-123--dielectric--'+case['model']+'--'+case['initialization'])
            expected=copy.deepcopy(template['config']);expected.pop('task');expected.pop('dataset')
            actual=copy.deepcopy(case['config']);actual.pop('task');actual.pop('dataset')
            self.assertEqual(actual,expected)
            self.assertEqual(case['config']['seed'],123);self.assertEqual(case['config_sha256'],canonical_digest(case['config']))
            self.assertEqual(case['tensor_shape'],[3]*(3 if case['task']=='piezoelectric' else 4))
            self.assertTrue(case['run_directory'].startswith('runs/arxiv-v1/supplemental-cases/'))
            self.assertEqual(case['status'],'defined_not_preflighted')

    def test_primary_digest_and_original_template_mutation_are_rejected(self):
        changed=copy.deepcopy(self.primary);changed['cases'][0]['seed']=456
        with self.assertRaisesRegex(ValueError,'original frozen'):module.build_tensor_definitions(changed)
        changed=copy.deepcopy(self.primary)
        target=next(c for c in changed['cases'] if c['id']=='seed-123--dielectric--mace--pretrained')
        target['config']['optimization']['train_backbone']=False;target['config_sha256']=canonical_digest(target['config'])
        with patch.object(module,'PRIMARY_SHA',canonical_digest(changed)),self.assertRaises(ValueError):module.build_tensor_definitions(changed)

    def test_full_source_reader_retains_zeros_and_all_cartesian_components(self):
        with sources():
            result=module.inspect_tensor_inputs()
            for task,rank in [('piezoelectric',3),('elastic',4)]:
                self.assertEqual(result[task]['structures'],3)
                self.assertEqual(result[task]['finite_cartesian_components'],3*3**rank)
                self.assertEqual(result[task]['whole_zero_labels'],1)

    def test_source_order_and_label_shape_fail_before_definition_output(self):
        with sources() as (root,datasets):
            p=root/'piezoelectric/structures.jsonl';rows=p.read_bytes().splitlines();p.write_bytes(b'\n'.join(reversed(rows))+b'\n')
            with self.assertRaisesRegex(ValueError,'ordered'):module.inspect_tensor_inputs()
        with sources() as (root,datasets):
            p=root/'piezoelectric/structures.jsonl';rows=[json.loads(x) for x in p.read_bytes().splitlines()];rows[0]['targets']['piezoelectric']=[0.]
            p.write_bytes(b''.join((json.dumps(row)+'\n').encode() for row in rows))
            with self.assertRaisesRegex(ValueError,'shape'):module.inspect_tensor_inputs()

    def test_parent_conversion_and_independent_proof_mutations_fail(self):
        for path in [module.DATA_ROOT+'/report.json','runs/supplemental-tensor-verification-1075/report.json']:
            with self.subTest(path=path),sources():
                write(path,dict(status='changed'))
                with self.assertRaisesRegex(ValueError,'proof changed'):module.inspect_tensor_inputs()

    def test_valid_shape_byte_mutation_and_canonical_split_mutation_fail(self):
        with sources() as (root,datasets):
            p=root/'elastic/structures.jsonl';p.write_bytes(p.read_bytes().replace(b'100',b'101'))
            with self.assertRaisesRegex(ValueError,'bytes/count'):module.inspect_tensor_inputs()
        with sources() as (root,datasets):
            p=root/'elastic/split.json';value=json.loads(p.read_bytes());value['protocol']['note']='changed';write(p,value)
            with self.assertRaisesRegex(ValueError,'split changed'):module.inspect_tensor_inputs()

    def test_configs_written_only_to_fresh_directory_and_unchanged_primary(self):
        with sources():
            # Input-reader and definition construction have separate fixtures.
            with patch.object(module,'inspect_tensor_inputs',return_value={'fixture':'full metadata reader separately tested'}):
                result=module.write_tensor_definitions(self.primary,'out')
                self.assertEqual(len(list(Path('out/configs').glob('*.json'))),16)
                for case in result['cases']:self.assertEqual(json.loads((Path('out')/case['config_path']).read_bytes()),case['config'])
                with self.assertRaises(FileExistsError):module.write_tensor_definitions(self.primary,'out')

    def test_public_cli_refuses_login_node(self):
        source=Path(__file__).resolve().parents[1]/'scripts/prepare_tensor_experiment_definitions.py'
        with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',[str(source),'--output','unused']),self.assertRaises(SystemExit) as raised:
            runpy.run_path(str(source),run_name='__main__')
        self.assertEqual(raised.exception.code,2)


if __name__=='__main__':unittest.main()

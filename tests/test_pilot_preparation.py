"""Diagnostic subset controls use small stdlib JSON fixtures; no numerical models."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from universal_gnn.benchmarks.experiments.pilots import pilot_config, select_pilot_indices, write_pilot_dataset
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.pairing.capacity import validate_pair
from universal_gnn.data.splits.manifest import create_manifest, validate_manifest


def fixture(root):
    records=[dict(schema_version=1,id=f'r-{i}',numbers=[1]*(i+1),positions=[[0.,0.,float(j)] for j in range(i+1)],
                  cell=[[30.,0.,0.],[0.,30.,0.],[0.,0.,30.]],pbc=[False]*3,
                  targets=dict(bandgap=float(i),classification=i%2)) for i in range(18)]
    path=root/'parent.jsonl';path.write_text(''.join(json.dumps(row)+'\n' for row in records))
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    roles={row['id']:('train' if i<10 else 'validation' if i<14 else 'test') for i,row in enumerate(records)}
    manifest=create_manifest([dict(id=row['id'],group=row['id']) for row in records],source_sha256=sha,official=roles)
    split=root/'parent-split.json';split.write_text(json.dumps(manifest))
    entry=dict(path=str(path),sha256=sha,split_manifest=str(split),split_manifest_sha256=canonical_digest(manifest))
    return records,manifest,entry


class PilotPreparationTests(unittest.TestCase):
    def test_selection_stays_inside_roles_is_deterministic_and_independent_of_atom_sizes(self):
        with tempfile.TemporaryDirectory() as folder:
            records,manifest,_=fixture(Path(folder));counts=dict(train=4,validation=2,test=2)
            selected=select_pilot_indices(manifest,counts=counts)
            self.assertEqual(selected,select_pilot_indices(manifest,counts=counts))
            self.assertNotEqual(selected,select_pilot_indices(manifest,counts=counts,seed=456))
            for role,indices in selected.items():
                self.assertEqual(len(indices),counts[role]);self.assertEqual(indices,sorted(indices))
                self.assertLessEqual(set(indices),set(manifest['partitions'][role]))
            self.assertTrue(any(i>3 for i in selected['train']))
            for row in records:row['numbers']=[];row['targets']={'changed':True}
            self.assertEqual(selected,select_pilot_indices(manifest,counts=counts))

    def test_parent_roles_labels_source_order_and_digest_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);records,parent,entry=fixture(root)
            result=write_pilot_dataset(entry,root/'pilot',counts=dict(train=4,validation=2,test=2))
            selected=[json.loads(line) for line in Path(result['path']).read_text().splitlines()]
            manifest=json.loads(Path(result['split_manifest']).read_text());lookup={row['id']:i for i,row in enumerate(records)}
            self.assertEqual([lookup[row['id']] for row in selected],sorted(lookup[row['id']] for row in selected))
            self.assertEqual(selected,[records[lookup[row['id']]] for row in selected])
            self.assertEqual(hashlib.sha256(Path(result['path']).read_bytes()).hexdigest(),result['sha256'])
            self.assertEqual(canonical_digest(manifest),result['split_manifest_sha256'])
            validate_manifest(manifest,source_sha256=result['sha256'],source_count=8)
            for role,indices in manifest['partitions'].items():
                self.assertTrue(all(lookup[selected[i]['id']] in parent['partitions'][role] for i in indices))
            audit=json.loads((root/'pilot/audit.json').read_text())
            self.assertEqual(audit['formal_training_runs'],0);self.assertEqual(audit['all_parent_records_verified'],18)
            with self.assertRaises(FileExistsError):write_pilot_dataset(entry,root/'pilot',counts=dict(train=4,validation=2,test=2))

    def test_mutated_labels_ids_or_split_never_publish_a_subset(self):
        for mode in ('labels','ids','split'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);records,manifest,entry=fixture(root)
                if mode=='split':
                    manifest['protocol']['changed']=True;Path(entry['split_manifest']).write_text(json.dumps(manifest))
                else:
                    if mode=='labels':records[-1]['targets']['bandgap']=999.
                    else:records[-1]['id']='different'
                    Path(entry['path']).write_text(''.join(json.dumps(row)+'\n' for row in records))
                with self.assertRaises(ValueError):write_pilot_dataset(entry,root/'pilot',counts=dict(train=4,validation=2,test=2))
                self.assertFalse((root/'pilot/split.json').exists())
                self.assertFalse((root/'pilot/structures.jsonl').exists())

    def test_invalid_or_unavailable_counts_are_not_silently_reduced(self):
        with tempfile.TemporaryDirectory() as folder:
            _,manifest,_=fixture(Path(folder))
            for counts in [dict(train=11,validation=2,test=2),dict(train=True,validation=2,test=2),
                           dict(train=4,validation=0,test=2),dict(train=4,test=2)]:
                with self.subTest(counts=counts),self.assertRaises(ValueError):select_pilot_indices(manifest,counts=counts)

    def test_pair_keeps_original_architecture_and_task_and_rebinds_only_pilot_budget(self):
        source=dict(seed=123,structures='all',dtype='float32',device='cuda',epochs=300,batch_size=32,max_atoms=None,
                    backbone=dict(name='cgcnn',implementation='official',initialization='pretrained'),
                    dataset=dict(path='parent.jsonl',partition='train',bindings={'bandgap':{'key':'bandgap','unit':'eV'}}),
                    task=dict(kind='supervised',property='bandgap'),optimization=dict(train_backbone=True,train_readout=True),
                    prediction=dict(head_mode='reset'),evaluation=dict(patience=30))
        before=copy.deepcopy(source);data=dict(path='pilot.jsonl',sha256='a'*64,split_manifest='pilot-split.json',split_manifest_sha256='b'*64)
        first=pilot_config(source,data);other=copy.deepcopy(source);other['backbone']['initialization']='scratch';second=pilot_config(other,data)
        validate_pair(dict(pretrained=first,scratch=second))
        self.assertEqual(source,before);self.assertEqual(first['backbone'],source['backbone'])
        self.assertEqual(first['dataset']['bindings'],source['dataset']['bindings'])
        self.assertEqual((first['epochs'],first['batch_size'],first['evaluation']['patience']),(3,2,None))
        self.assertEqual(first['structures'],'all');self.assertEqual(first['dataset']['path'],'pilot.jsonl')
        self.assertEqual(first['prediction'],source['prediction']);self.assertEqual(first['optimization'],source['optimization'])

    def test_cropped_or_fitted_parent_definitions_are_rejected(self):
        base=dict(structures='all',max_atoms=None,backbone=dict(name='mace',implementation='official',initialization='scratch'),
                  dataset=dict(partition='train'))
        data=dict(path='pilot.jsonl',sha256='a'*64,split_manifest='split.json',split_manifest_sha256='b'*64)
        variants=[{**base,'structures':10},{**base,'max_atoms':10},{**base,'generation_prior':{'fitted':True}},
                  {**base,'backbone':{**base['backbone'],'neighbor_statistics':{'fitted':True}}}]
        for config in variants:
            with self.assertRaises(ValueError):pilot_config(config,data)
        with self.assertRaises(ValueError):pilot_config(base,data,batch_size=True)

    def test_cli_slurm_gate_precedes_source_access_or_torch_import(self):
        environment=dict(os.environ,PYTHONPATH=str(Path('src').resolve()));environment.pop('SLURM_JOB_ID',None)
        script="import sys,runpy;sys.argv=['pilot','--matrix','missing.json','--output','unused'];\ntry:runpy.run_path('scripts/prepare_arxiv_pilot.py',run_name='__main__')\nexcept SystemExit as e:assert e.code==2\nassert 'torch' not in sys.modules"
        result=subprocess.run([sys.executable,'-S','-c',script],env=environment,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('Slurm',result.stderr)


if __name__=='__main__':unittest.main()

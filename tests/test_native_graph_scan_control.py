"""Stdlib-only scan policy, graph-size arithmetic and complete-stream controls."""

import copy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.probes.native_scan import (
    canonical_sha, edge_statistics, reference_config, write_training_rows,
)
from universal_gnn.benchmarks.probes.selection import select_probe


def configuration():
    return dict(structures="all", device="cuda", dtype="float32", max_atoms=None,
                backbone=dict(name="cgcnn", implementation="official", initialization="scratch"),
                dataset=dict(path="structures.jsonl", split_manifest="split.json", partition="train"),
                prediction=dict(head_mode="reset"))


@dataclass
class Record:
    identifier: str


class NativeGraphScanControlTests(unittest.TestCase):
    def test_gate_precedes_torch_import_and_cli_configuration_access(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, "Slurm"):
            reference_config({})
        env = dict(os.environ, PYTHONPATH=str(Path('src').resolve()))
        env.pop('SLURM_JOB_ID', None)
        script = "import sys,runpy;sys.argv=['scan_training_graphs','--config','missing.json','--output','unused'];\ntry:runpy.run_path('scripts/scan_training_graphs.py',run_name='__main__')\nexcept SystemExit as e:assert e.code==2\nassert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, '-S', '-c', script], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Slurm', result.stderr)
        script=script.replace('scan_training_graphs','validate_graph_scan').replace("'--config','missing.json',",'')
        result=subprocess.run([sys.executable,'-S','-c',script],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Slurm',result.stderr)

    def test_reference_retains_graph_dtype_task_and_callers_initialization(self):
        config=configuration();config['backbone'].update(name='nequip',architecture='author.yaml',neighbor_statistics={'fitted':True})
        config['task']={'kind':'generation','sampling':{'steps':100}}
        before=copy.deepcopy(config)
        with patch.dict(os.environ,SLURM_JOB_ID='fixture'):
            reference=reference_config(config)
        self.assertEqual(config,before)
        self.assertEqual(reference['backbone'],dict(name='nequip',implementation='official'))
        for key in ('dtype','device','task','dataset','structures'):
            self.assertEqual(reference[key],config[key])

    def test_rejects_cropped_nontraining_replaced_or_native_task_paths(self):
        changes=[('structures',10),('max_atoms',100),('graph',{'cutoff':6}),('device','cpu'),('dtype','float16')]
        variants=[]
        for key,value in changes:
            config=configuration();config[key]=value;variants.append(config)
        for section,key,value in [('dataset','partition','test'),('dataset','split_manifest',None),
                                  ('backbone','implementation','builtin'),('backbone','name','plugin'),
                                  ('backbone','initialization','random_head'),('prediction','head_mode','native')]:
            config=configuration();config[section][key]=value;variants.append(config)
        with patch.dict(os.environ,SLURM_JOB_ID='fixture'):
            for config in variants:
                with self.subTest(config=config),self.assertRaises(ValueError):reference_config(config)

    def test_directed_degree_counts_both_axes_periodic_images_and_empty_graphs(self):
        self.assertEqual(edge_statistics(4,[0,0,0],[1,2,3]),(3,3))
        self.assertEqual(edge_statistics(4,[1,2,3],[0,0,0]),(3,3))
        self.assertEqual(edge_statistics(1,[0,0,0],[0,0,0]),(3,3))
        self.assertEqual(edge_statistics(2,[],[]),(0,0))
        for nodes,src,dst in [(0,[],[]),(2,[0],[]),(2,[2],[0]),(2,[False],[0]),(2,[0],[-1])]:
            with self.subTest(nodes=nodes,src=src,dst=dst),self.assertRaises(ValueError):edge_statistics(nodes,src,dst)

    def test_complete_stream_uses_every_identity_once_and_can_be_selected(self):
        expected=[dict(id=f'a-{i}',source_index=4+3*i) for i in range(20)]
        structures=[Record(row['id']) for row in expected];calls=[]
        def counter(record):
            calls.append(record.identifier)
            i=len(calls)
            return dict(atoms=i,native_edges=i*12,native_triplets=0,auxiliary_edges=i*4,maximum_degree=12)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'rows.jsonl';write_training_rows(structures,expected,counter,path)
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(calls,[r['id'] for r in expected])
            self.assertEqual([r['source_index'] for r in rows],[r['source_index'] for r in expected])
            binding=dict(source_sha256='a'*64,split_manifest_sha256='b'*64,graph_definition_sha256='c'*64,
                         dtype='float32',native_edge_kind='padded_neighbor_slots')
            result=select_probe(rows,expected,binding)
            self.assertEqual(result['coverage']['structures'],20)
            self.assertIn(19,result['worst_indices'])
            self.assertFalse(result['coverage']['verified_full_training_scan'])
            with self.assertRaises(FileExistsError):write_training_rows(structures,expected,counter,path)

    def test_midstream_builder_or_identity_failure_preserves_only_completed_prefix(self):
        expected=[dict(id=f'a-{i}',source_index=i) for i in range(3)]
        for identity_error in (False,True):
            structures=[Record(row['id']) for row in expected]
            if identity_error:structures[1].identifier='wrong'
            def counter(record):
                if record.identifier=='a-1':raise RuntimeError('original builder failed')
                return dict(atoms=1,native_edges=0,native_triplets=0,auxiliary_edges=0,maximum_degree=0)
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'rows.jsonl'
                with self.assertRaises((RuntimeError,ValueError)):write_training_rows(structures,expected,counter,path)
                self.assertEqual(len(path.read_text().splitlines()),1)
                self.assertFalse((Path(folder)/'probe.json').exists())
        with tempfile.TemporaryDirectory() as folder,self.assertRaisesRegex(ValueError,'length'):
            write_training_rows([],expected,lambda _: {},Path(folder)/'rows.jsonl')

    def test_canonical_binding_ignores_mapping_order_but_tracks_precision(self):
        self.assertEqual(canonical_sha({'b':2,'a':1}),canonical_sha({'a':1,'b':2}))
        self.assertNotEqual(canonical_sha({'dtype':'float32'}),canonical_sha({'dtype':'float64'}))
        with self.assertRaises(ValueError):canonical_sha({'invalid':float('nan')})


if __name__=='__main__':unittest.main()

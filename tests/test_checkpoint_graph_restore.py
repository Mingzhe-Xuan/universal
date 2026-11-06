"""Source compatibility decisions and input-domain guards without a model runtime."""

import ast
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest

from universal_gnn.backbones.official.checkpoint_graph import (
    LEGACY_NEQUIP_SOURCE, PERIODIC_NEQUIP_SOURCE, checkpoint_graph_restore,
    restored_graph_compatibility, install_periodic_restore_guard,
)


def provenance(source):
    return dict(artifact_sha256={'package':'a'*64,'blueprint':'b'*64},adapter_source_sha256=source,
        provider_version='0.14.0',ase_version='3.27.0',torch_version='2.7.1+cu128')


def migration():
    return restored_graph_compatibility(provenance(LEGACY_NEQUIP_SOURCE),provenance(PERIODIC_NEQUIP_SOURCE),provider='nequip')


class Flags:
    def __init__(self, values, *, shape=(1,3),dtype='torch.bool'):
        self.values=values;self.shape=shape;self.dtype=dtype
    def all(self):return all(self.values)


class Native:
    def __init__(self):self.calls=0
    def native_input(self,batch):self.calls+=1;return batch


class CheckpointGraphRestoreTests(unittest.TestCase):
    def test_only_known_checkpoint_restore_context_allows_compatibility(self):
        self.assertIsNone(migration())
        previous,current=provenance(LEGACY_NEQUIP_SOURCE),provenance(PERIODIC_NEQUIP_SOURCE)
        before=copy.deepcopy((previous,current))
        with checkpoint_graph_restore():
            result=restored_graph_compatibility(previous,current,provider='nequip')
            self.assertEqual(result['allowed_pbc'],'fully_periodic_only')
            self.assertFalse(result['statistics_recalibrated'])
            self.assertEqual(result['original_native_graph'],previous)
            self.assertEqual(result['runtime_native_graph'],current)
            result['original_native_graph']['artifact_sha256']['package']='changed'
        self.assertEqual((previous,current),before);self.assertIsNone(migration())

    def test_unknown_sources_artifacts_versions_and_fields_refuse(self):
        with checkpoint_graph_restore():
            for field in ['adapter_source_sha256','artifact_sha256','provider_version','ase_version','torch_version']:
                for which in ['previous','current']:
                    with self.subTest(field=field,which=which):
                        previous,current=provenance(LEGACY_NEQUIP_SOURCE),provenance(PERIODIC_NEQUIP_SOURCE)
                        (previous if which=='previous' else current)[field]='unknown'
                        self.assertIsNone(restored_graph_compatibility(previous,current,provider='nequip'))
            for provider in ['mace','alignn','cgcnn','custom']:
                self.assertIsNone(restored_graph_compatibility(provenance(LEGACY_NEQUIP_SOURCE),provenance(PERIODIC_NEQUIP_SOURCE),provider=provider))
            for old in [None,{},[],{**provenance(LEGACY_NEQUIP_SOURCE),'unknown':'value'}]:
                self.assertIsNone(restored_graph_compatibility(old,provenance(PERIODIC_NEQUIP_SOURCE),provider='nequip'))

    def test_exception_nested_and_thread_contexts_restore(self):
        with self.assertRaisesRegex(RuntimeError,'intentional'):
            with checkpoint_graph_restore():
                self.assertIsNotNone(migration())
                with checkpoint_graph_restore():self.assertIsNotNone(migration())
                with ThreadPoolExecutor(max_workers=1) as pool:self.assertIsNone(pool.submit(migration).result())
                self.assertIsNotNone(migration());raise RuntimeError('intentional')
        self.assertIsNone(migration())

    def test_all_periodic_guard_preserves_input_and_bound_clone(self):
        original=Native()
        with checkpoint_graph_restore():install_periodic_restore_guard(original,migration())
        batch=SimpleNamespace(num_graphs=1,pbc=Flags([True,True,True]))
        self.assertIs(original.native_input(batch),batch);self.assertEqual(original.calls,1)
        cloned=copy.deepcopy(original)
        self.assertIs(cloned.native_input(batch),batch)
        self.assertEqual(cloned.calls,2);self.assertEqual(original.calls,1)

    def test_guard_refuses_nonperiodic_partial_empty_and_invalid_flags_before_native_call(self):
        model=Native()
        with checkpoint_graph_restore():install_periodic_restore_guard(model,migration())
        cases=[SimpleNamespace(num_graphs=1,pbc=Flags([False,False,False])),
            SimpleNamespace(num_graphs=1,pbc=Flags([True,False,True])),
            SimpleNamespace(num_graphs=0,pbc=Flags([],shape=(0,3))),
            SimpleNamespace(num_graphs=1,pbc=Flags([True]*3,shape=(3,))),
            SimpleNamespace(num_graphs=1,pbc=Flags([True]*3,dtype='torch.float32'))]
        for batch in cases:
            with self.subTest(batch=batch),self.assertRaisesRegex(ValueError,'fully periodic'):model.native_input(batch)
        self.assertEqual(model.calls,0)

    def test_current_native_input_ast_preserves_the_known_periodic_implementation(self):
        source=Path('src/universal_gnn/backbones/official/nequip.py').read_bytes().replace(b'\r\n',b'\n')
        self.assertEqual(hashlib.sha256(source).hexdigest(),PERIODIC_NEQUIP_SOURCE)
        tree=ast.parse(source.decode());method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='native_input')
        class PeriodicIdentity(ast.NodeTransformer):
            def visit_Call(self,node):
                node=self.generic_visit(node)
                if isinstance(node.func,ast.Name) and node.func.id=='_respect_nonperiodic_axes':return node.args[0]
                return node
        normalized=PeriodicIdentity().visit(method)
        legacy=subprocess.check_output(['git','show','27e2339:src/universal_gnn/backbones/official/nequip.py'])
        self.assertEqual(hashlib.sha256(legacy).hexdigest(),LEGACY_NEQUIP_SOURCE)
        legacy_tree=ast.parse(legacy.decode())
        previous=next(n for n in ast.walk(legacy_tree) if isinstance(n,ast.FunctionDef) and n.name=='native_input')
        self.assertEqual(ast.dump(normalized,include_attributes=False),ast.dump(previous,include_attributes=False))

    def test_new_process_import_does_not_load_torch_or_numpy(self):
        code="import sys;sys.path.insert(0,'src');import universal_gnn.backbones.official.checkpoint_graph;assert not {'torch','numpy','ase'}&sys.modules.keys()"
        subprocess.run([sys.executable,'-S','-c',code],capture_output=True,check=True)


if __name__=='__main__':unittest.main()

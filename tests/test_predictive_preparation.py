"""Pure full-preparation orchestration controls, never numerical/model evidence."""

import copy
from contextlib import contextmanager, ExitStack, nullcontext
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.preparation import predictive_spec, prepare_predictive_pair
from universal_gnn.benchmarks.preparation.specification import full_manifest, physical_indices, reference_examples, runtime_context
from universal_gnn.data.splits import create_manifest

registry_fixture=runpy.run_path(str(Path(__file__).with_name('test_arxiv_experiment_definitions.py')))['registry_fixture']


@contextmanager
def preparation_fixture(task='forcefield',provider='alignn'):
    with tempfile.TemporaryDirectory() as temporary,ExitStack() as stack:
        root=Path(temporary);before=Path.cwd();os.chdir(root);stack.callback(os.chdir,before)
        matrix=build_matrix(registry_fixture());pair='seed-456--'+task+'--'+provider
        spec=predictive_spec(matrix,pair);operations=[]
        stack.enter_context(patch.dict(os.environ,{'SLURM_JOB_ID':'fixture'}))
        prefix='universal_gnn.benchmarks.preparation.predictive.'
        stack.enter_context(patch(prefix+'runtime_context',return_value=dict(git_commit='a'*40,slurm_job_id='fixture',source_checkout=str(root))))
        stack.enter_context(patch(prefix+'full_manifest',return_value=dict(partitions=dict(train=list(range(spec['counts']['train']))))))
        class Dataset:
            source=range(spec['source_structures'])
            indices=range(spec['counts']['train'])
            def __len__(self):return spec['counts']['train']
            def __getitem__(self,index):return SimpleNamespace(id='source-'+str(index))
        stack.enter_context(patch(prefix+'runtime.load_training',return_value=Dataset()))
        def parity(*args):operations.append('parity');return dict(structures=2)
        parity_mock=stack.enter_context(patch(prefix+'runtime.native_parity',side_effect=parity))
        probe=dict(coverage=dict(verified_full_training_scan=True,structures=spec['counts']['train']),worst_indices=[1,2])
        def scan(*args):operations.append('scan');return copy.deepcopy(probe)
        stack.enter_context(patch(prefix+'runtime.graph_scan',side_effect=scan))
        def capacity(configs,output,probe,timeout):
            operations.append('capacity');output.mkdir()
            for mode,config in configs.items():
                actual=copy.deepcopy(config);actual['batch_size']=4
                if mode=='scratch' and provider in {'mace','nequip'}:
                    actual['backbone']['neighbor_statistics']=dict(structures=spec['counts']['train'],declared_training_structures=spec['counts']['train'],
                        partition='train',source_sha256=config['dataset']['sha256'],manifest_sha256=config['dataset']['split_manifest_sha256'],dtype='float32')
                (output/('config.'+mode+'.resolved.json')).write_text(json.dumps(actual))
            return dict(passed=True,final_configs={mode:'config.'+mode+'.resolved.json' for mode in ['pretrained','scratch']})
        capacity_mock=stack.enter_context(patch(prefix+'runtime.paired_capacity',side_effect=capacity))
        evidence=dict(common_batch_size=4,successful_workers=[dict(elapsed_seconds=1.,measured_batches=100)]*4)
        stack.enter_context(patch(prefix+'verify_capacity_evidence',return_value=evidence))
        def derivatives(structures,config):
            operations.append('physics-'+config['backbone']['initialization'])
            names=['forces_finite_difference','stress_finite_difference'] if task=='forcefield' else ['response_auxiliary_finite_difference']
            return dict(passed=True,device='cuda:0',dtype='torch.float32',checks={key:dict(passed=True,required=True) for key in names})
        derivative_mock=stack.enter_context(patch(prefix+'runtime.derivatives',side_effect=derivatives))
        def gate(*args,**kwargs):operations.append('gate');return dict(status='passed',git_commit='a'*40,common_batch_size=4)
        gate_mock=stack.enter_context(patch(prefix+'check_preparation',side_effect=gate))
        stack.enter_context(patch(prefix+'shutil.disk_usage',return_value=SimpleNamespace(free=100*1024**3)))
        yield dict(root=root,matrix=matrix,pair=pair,spec=spec,output=root/'prepared',operations=operations,
                   parity=parity_mock,capacity=capacity_mock,derivatives=derivative_mock,gate=gate_mock)


class PredictivePreparationTests(unittest.TestCase):
    def test_all_sixty_predictive_pairs_preserve_frozen_tasks_seeds_and_modes(self):
        matrix=build_matrix(registry_fixture());before=copy.deepcopy(matrix);count=0
        for pair in matrix['pairs']:
            if '--generation--' in pair['id']:continue
            spec=predictive_spec(matrix,pair['id']);count+=1
            self.assertEqual({c['seed'] for c in spec['configs'].values()},{spec['seed']})
            self.assertEqual({c['epochs'] for c in spec['configs'].values()},{300})
            self.assertEqual(set(spec['configs']),{'pretrained','scratch'})
            self.assertEqual(sum(spec['counts'].values()),spec['source_structures'])
        self.assertEqual(count,60);self.assertEqual(matrix,before)
        with self.assertRaises(ValueError):predictive_spec(matrix,'seed-456--generation--mace')
        changed=copy.deepcopy(matrix);changed['cases'][0]['config']['seed']=789
        with self.assertRaises(ValueError):predictive_spec(changed,changed['cases'][0]['pair_id'])

    def test_all_twenty_provider_task_pipelines_use_current_seed_and_both_final_gates(self):
        for provider in ['cgcnn','alignn','mace','nequip']:
            for task in ['forcefield','dielectric','bandgap','classification','spectrum']:
                with self.subTest(provider=provider,task=task),preparation_fixture(task,provider) as f:
                    result=prepare_predictive_pair(f['matrix'],f['pair'],f['output'])
                    self.assertEqual((result['status'],result['seed'],result['formal_training_runs']),('passed',456,0))
                    self.assertFalse(result['final_gate_check_pending']);self.assertEqual(f['operations'][:3],['parity','scan','capacity'])
                    self.assertEqual(f['operations'][-2:],['gate','gate'])
                    self.assertEqual(f['derivatives'].call_count,2 if task in ['forcefield','dielectric'] else 0)
                    for call in f['derivatives'].call_args_list:self.assertEqual(call.args[1]['seed'],456)
                    self.assertEqual(f['spec']['configs']['pretrained']['batch_size'],4 if task in ['forcefield','dielectric'] else 32)

    def test_physics_and_capacity_failures_preserve_reports_and_never_pass_final_gate(self):
        for failure in ['capacity','physics','cpu_physics','optional_physics','final_gate','parity']:
            with self.subTest(failure=failure),preparation_fixture() as f:
                if failure=='capacity':f['capacity'].side_effect=lambda *a,**k:dict(passed=False)
                elif failure=='physics':f['derivatives'].side_effect=lambda *a:dict(passed=False)
                elif failure=='cpu_physics':f['derivatives'].side_effect=lambda *a:dict(passed=True,device='cpu',dtype='torch.float32')
                elif failure=='optional_physics':f['derivatives'].side_effect=lambda *a:dict(passed=True,device='cuda',dtype='torch.float32',checks={})
                elif failure=='final_gate':f['gate'].side_effect=ValueError('real full gate rejected')
                else:f['parity'].side_effect=lambda *a:dict(structures=1)
                with self.assertRaises((RuntimeError,ValueError)):prepare_predictive_pair(f['matrix'],f['pair'],f['output'])
                report=json.loads((f['output']/'report.json').read_text());self.assertEqual(report['status'],'failed')
                if failure!='final_gate':self.assertEqual(f['gate'].call_count,0)
                if failure=='parity':self.assertEqual(f['capacity'].call_count,0)

    def test_missing_slurm_existing_primary_fresh_output_and_disk_guards(self):
        original_disk_usage=shutil.disk_usage
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):prepare_predictive_pair({},'unused','unused')
        for failure in ['primary','output','disk','timeout']:
            with self.subTest(failure=failure),preparation_fixture() as f:
                if failure=='primary':Path(f['spec']['cases'][0]['run_directory']).mkdir(parents=True)
                elif failure=='output':f['output'].mkdir()
                low_disk=patch('universal_gnn.benchmarks.preparation.predictive.shutil.disk_usage',return_value=SimpleNamespace(free=1)) if failure=='disk' else nullcontext()
                with low_disk,self.assertRaises((RuntimeError,FileExistsError,ValueError)):
                    prepare_predictive_pair(f['matrix'],f['pair'],f['output'],timeout=0 if failure=='timeout' else 7200)
                self.assertEqual(f['capacity'].call_count,0)
        self.assertIs(shutil.disk_usage,original_disk_usage)

    def test_full_manifest_checks_exact_source_counts_and_partition_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'source.jsonl';data.write_bytes(b'complete fixture bytes')
            source=hashlib.sha256(data.read_bytes()).hexdigest()
            manifest=create_manifest([dict(id=str(i),group=str(i)) for i in range(9)],source_sha256=source)
            split=root/'split.json';split.write_text(json.dumps(manifest))
            config=dict(dataset=dict(path=str(data),sha256=source,split_manifest=str(split),split_manifest_sha256=canonical_digest(manifest)))
            spec=dict(configs=dict(pretrained=config),counts=manifest['counts'],source_structures=9)
            self.assertEqual(full_manifest(spec),manifest)
            data.write_bytes(b'changed')
            with self.assertRaises(ValueError):full_manifest(spec)

    def test_reference_csv_slots_never_modify_actual_targets_or_configs(self):
        @dataclass
        class Structure:
            targets:dict
        structures=[Structure(dict(forces=[[1.,2.,3.]])),Structure(dict(elastic='retained'))]
        config=dict(backbone=dict(name='cgcnn'),task=dict(kind='forcefield'))
        original=copy.deepcopy((structures,config));examples,reference=reference_examples(structures,config)
        self.assertEqual((structures,config),original)
        self.assertEqual(reference['task']['property'],'_unused_reference_csv_slot')
        self.assertEqual(examples[0].targets,{'_unused_reference_csv_slot':0.})

    def test_worst_inputs_are_real_unique_train_indices(self):
        self.assertEqual(physical_indices(dict(worst_indices=[4,4,3]),5),[4,3])
        self.assertEqual(physical_indices(dict(worst_indices=[4]),5),[4,0])
        for values in [[],[True],[-1],[5],None]:
            with self.subTest(values=values),self.assertRaises(ValueError):physical_indices(dict(worst_indices=values),5)

    def test_context_requires_original_environment_and_actual_running_gpu(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):runtime_context(dict(model='alignn'))
        with patch.dict(os.environ,{'SLURM_JOB_ID':'1'}),patch('sys.prefix','/fake/wrong'):
            with self.assertRaises(RuntimeError):runtime_context(dict(model='alignn'))


if __name__=='__main__':unittest.main()

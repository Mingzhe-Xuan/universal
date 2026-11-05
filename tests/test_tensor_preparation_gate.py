"""Synthetic protocol evidence only; these fixtures never certify real CUDA work."""
import copy
from contextlib import contextmanager, ExitStack
import getpass
import hashlib
import json
import os
from pathlib import Path
import runpy
import shlex
import sys
import tempfile
from unittest.mock import patch
import unittest

from universal_gnn.benchmarks.supplemental_tensors import gate as tensor
from universal_gnn.benchmarks.supplemental_tensors import experiments
from universal_gnn.benchmarks.experiments.recipes import build_matrix
from universal_gnn.benchmarks.execution import gates
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.probes.selection import select_probe
from universal_gnn.data.splits import create_manifest

registry_fixture=runpy.run_path(str(Path(__file__).with_name('test_arxiv_experiment_definitions.py')))['registry_fixture']


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(json.dumps(value,allow_nan=False).encode())


def physics(case, ids):
    rank=len(case['tensor_shape']);equivariant=case['model'] in {'mace','nequip'}
    names=dict(response_auxiliary_finite_difference=(2e-4,2e-5,True),translation_response=(.001,.0002,True),
        eval_batch_response=(2e-4,2e-5,True),rotation_response_covariance=(.001,.0002,equivariant))
    names['inversion_rank'+str(rank)+'_response' if equivariant else 'rotation_fixed_frame_invariance']=(.001,.0002,True)
    def value(n):return .125 if n==0 else [value(n-1) for _ in range(3)]
    return dict(passed=True,device='cuda:0',dtype='torch.float32',structure_ids=ids,
        geometry_tolerance=dict(rtol=.001,atol=.0002),mixed_parameter_gradient_norms=dict(backbone=.1,readout=.2),
        checks={k:dict(rtol=r,atol=a,required=req,passed=True,max_abs_error=0.) for k,(r,a,req) in names.items()},
        response=dict(guarantee='O3_cartesian' if equivariant else 'fixed_frame_components',rank=rank,
            shape=case['tensor_shape'],inversion_parity=(-1)**rank,no_symmetry_projection=True,
            analytic=[value(rank)],numeric=[value(rank)]))


def origin(case):
    errors=['max_feature_error','max_energy_error'] if case['model']=='mace' else (
        ['max_feature_error','max_energy_error','max_force_error'] if case['model']=='nequip' else
        ['max_feature_error','max_prediction_error'])
    return dict(cuda_acceptance=True,formal_training_runs=0,formal_training_launched=False,
        allocation=dict(gpus=1,node_list='node42',evidence='running_nodes_and_TresPerNode'),
        native_parity=dict(structures=2,reference='synthetic protocol fixture',**{k:0. for k in errors}))


@contextmanager
def shared_evidence(task='piezoelectric'):
    with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
        root=Path(folder);before=Path.cwd();os.chdir(root);stack.callback(os.chdir,before)
        stack.enter_context(patch.dict(os.environ,{'SLURM_JOB_ID':'fixture'}))
        source=root/'data.jsonl';source.write_bytes(b''.join((json.dumps(dict(id=str(i)))+'\n').encode() for i in range(5)))
        sha=gates.file_sha(source);manifest=create_manifest([dict(id=str(i),group=str(i)) for i in range(5)],source_sha256=sha,
            official={str(i):'train' if i<3 else 'validation' if i==3 else 'test' for i in range(5)})
        split=root/'split.json';write(split,manifest)
        configs={}
        for mode in ['pretrained','scratch']:
            configs[mode]=dict(seed=123,structures='all',max_atoms=None,device='cuda',dtype='float32',batch_size=4,epochs=300,
                dataset=dict(path=str(source),sha256=sha,split_manifest=str(split),split_manifest_sha256=canonical_digest(manifest),partition='train'),
                backbone=dict(name='alignn',implementation='official',initialization=mode),task=dict(kind='supervised',property=task),
                prediction=dict(version=1,head_mode='reset',readout=dict(name='response',pooling='mean')),
                optimization=dict(train_backbone=True,train_readout=True))
        artifact=Path('models/official/fixture.bin');artifact.parent.mkdir(parents=True);artifact.write_bytes(b'fixture artifact identity')
        artifact_sha=gates.file_sha(artifact)
        definition=dict(provider='alignn',dtype='float32',cutoff=5.,device='cuda:0',artifact_sha256=dict(checkpoint=artifact_sha))
        binding=dict(source_sha256=sha,split_manifest_sha256=canonical_digest(manifest),
            graph_definition_sha256=canonical_digest(definition),dtype='float32',native_edge_kind='directed_edges')
        rows=[dict(id=str(i),index=i,source_index=i,atoms=i+1,native_edges=2,native_triplets=0,auxiliary_edges=0,maximum_degree=1) for i in range(3)]
        records=[dict(id=str(i),source_index=i) for i in range(3)]
        probe=select_probe(rows,records,binding,warmup_batches=2,measure_batches=100)
        probe['coverage'].update(verified_full_training_scan=True,graph_definition=definition)
        prepared=root/'prepared';graph=prepared/'graph-scan';graph.mkdir(parents=True)
        write(graph/'report.json',dict(status='complete',structures=3,probe_sha256=canonical_digest(probe),graph_binding=binding,git_commit='a'*40))
        write(graph/'probe.json',probe);(graph/'graph-sizes.jsonl').write_bytes(b''.join((json.dumps(r)+'\n').encode() for r in rows))
        capacity=prepared/'capacity';capacity.mkdir()
        cap=dict(configs=configs,phase='train',input_config_sha256={k:canonical_digest(v) for k,v in configs.items()},
                 resolved_config_sha256={k:canonical_digest(v) for k,v in configs.items()})
        write(capacity/'report.json',cap)
        workers=[]
        for mode in ['pretrained','scratch']:
            write(capacity/('config.'+mode+'.resolved.json'),configs[mode])
            write(prepared/('derivatives-'+mode+'.json'),dict(passed=True,device='cuda:0',dtype='torch.float32',
                  checks=dict(response_auxiliary_finite_difference=dict(passed=True,required=True))))
            workers.append(dict(execution=dict(git_commit='a'*40,official=dict(initialization=mode,sha256=dict(checkpoint=artifact_sha),
                parameter_coverage=1. if mode=='pretrained' else 0.,buffer_coverage=0.,state_layout_verified=True)),
                selected_training_structures=3,measured_batches=100,measured_structures=400,batch_size=4,elapsed_seconds=1.,versions=dict(torch='fixture')))
        evidence=dict(common_batch_size=4,successful_workers=workers*2)
        stack.enter_context(patch.object(gates,'verify_capacity_evidence',return_value=evidence))
        stack.enter_context(patch.object(gates,'installed_versions',return_value=dict(torch='fixture')))
        stack.enter_context(patch.object(gates,'compatible_sources',return_value='a'*40))
        pair='fixture-tensor';case=dict(id=pair+'--pretrained',pair_id=pair,model='alignn',task=task,seed=123,initialization='pretrained')
        spec=dict(case=case,configs=configs,counts=manifest['counts'],source_structures=5,matrix_sha256='b'*64,
                  definition_kind='arxiv_v1_supplemental_tensor_definitions')
        report=dict(status='passed',stage='complete',kind='full_supplemental_tensor_pair_preparation',pair_id=pair,
                    model='alignn',task=task,seed=123,definition_sha256='b'*64,cuda_acceptance=True,git_commit='a'*40)
        write(prepared/'report.json',report)
        matrix=dict(registry=dict(artifacts=dict(alignn=dict(files={'fixture.bin':dict(sha256=artifact_sha)}))))
        yield dict(root=root,prepared=prepared,spec=spec,matrix=matrix,report=report,probe=probe,cap=cap,workers=workers)


@contextmanager
def receipt_fixture(case):
    with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
        before=Path.cwd();os.chdir(folder);stack.callback(os.chdir,before)
        preparation=Path('runs/arxiv-v1/full-rank34-preparation-1233-'+case['task']+'-'+case['model'])
        claim=Path('claim')/case['pair_id'];claim.mkdir(parents=True)
        request=claim/'request.sh';request.write_bytes(b'fixture request; never executed')
        source='/fixture/source/'+'a'*40
        argv=['sbatch','--no-requeue','--partition=compute','--nodelist=node42','--gres=gpu:1',
            '--cpus-per-task=2','--mem=64G','--time=16:00:00','--nice=1000','--chdir='+source,
            '--job-name=ugnn-rank34-prep-'+case['task']+'--'+case['model']]
        entry=dict(job='1233',state='submitted',formal_training_runs=0,pair=case['pair_id'],model=case['model'],task=case['task'],seed=123,
            definition_control_job='1231',definition_sha256=tensor.DEFINITION_SHA,output=preparation.as_posix(),
            request_path=request.as_posix(),request_sha256=gates.file_sha(request),source_checkout=source,git_commit='a'*40,sbatch_argv=argv)
        prepared=dict(request_sha256=entry['request_sha256'],slurm_job_id='1233',git_commit='a'*40)
        write(preparation/'report.json',prepared);write(claim/'job.json',entry)
        fields=dict(JobId='1233',UserId=getpass.getuser()+'(1000)',JobName=argv[-1].split('=',1)[1],WorkDir=source,
            JobState='COMPLETED',ExitCode='0:0',Requeue='0',NumCPUs='2',MinMemoryNode='64G',TimeLimit='16:00:00',Nice='1000')
        terminal=dict(entry=copy.deepcopy(entry),exit=0,request_sha256=entry['request_sha256'],report_sha256=gates.file_sha(preparation/'report.json'),
            fields=fields,raw=' '.join(k+'='+shlex.quote(v) for k,v in fields.items()))
        write(claim/'terminal.json',terminal)
        source_identity=stack.enter_context(patch.object(tensor.subprocess,'check_output',side_effect=lambda args,**kwargs:'a'*40+'\n' if 'rev-parse' in args else ''))
        yield dict(preparation=preparation,prepared=prepared,claim=claim,receipt=entry,terminal=terminal,source_identity=source_identity)


@contextmanager
def wrapper_fixture(primary,definitions,case):
    with tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
        before=Path.cwd();os.chdir(folder);stack.callback(os.chdir,before)
        root=Path(folder);write(root/'primary.json',primary);write(root/'definitions.json',definitions)
        stack.enter_context(patch.dict(os.environ,{'SLURM_JOB_ID':'fixture'}))
        stack.enter_context(patch.object(tensor.sys,'prefix','/fixture/'+case['python_environment']))
        realsha=gates.file_sha;repository=Path(__file__).resolve().parents[1]
        def sha(path):
            p=Path(path);return realsha(repository/p) if p.as_posix().startswith('src/') else realsha(p)
        stack.enter_context(patch.object(tensor,'file_sha',side_effect=sha))
        stack.enter_context(patch.object(tensor,'DEFINITION_SHA',realsha(root/'definitions.json')))
        receipt=stack.enter_context(patch.object(tensor,'checked_preparation_receipt',return_value=dict(scope='fixture')))
        audit=stack.enter_context(patch.object(tensor,'inspect_tensor_inputs',return_value=definitions['full_input_audit']))
        shared=stack.enter_context(patch.object(tensor,'_check_prepared_spec',return_value=dict(status='passed',case=case,
            config=case['config'],probed_train_only_seconds=60.)))
        preparation=root/'prepared';write(preparation/'graph-scan/probe.json',dict(worst_indices=[2,1],warmup_batches=2,measure_batches=100))
        write(case['config']['dataset']['split_manifest'],dict(records=[dict(id=x) for x in ['a','b','c']],partitions=dict(train=[0,1,2])))
        names=['cartesian.py','derivatives.py','finite_difference.py','precision.py']
        validators={'src/universal_gnn/benchmarks/validation/'+name:sha('src/universal_gnn/benchmarks/validation/'+name) for name in names}
        physical={}
        for mode in ['pretrained','scratch']:
            p=preparation/('derivatives-'+mode+'.json');write(p,physics(case,['c','b']));physical[mode]=sha(p)
        prepared=dict(status='passed',stage='complete',independent_full_gate_pending=True,physical_training_indices=[2,1],
            physical_structure_ids=['c','b'],physical_evidence_sha256=physical,source_sha256=validators,
            resource_estimate=dict(train_only_300_epoch_seconds=60.),**origin(case))
        write(preparation/'report.json',prepared)
        yield dict(root=root,preparation=preparation,prepared=prepared,receipt=receipt,audit=audit,shared=shared)


class TensorPreparationGate(unittest.TestCase):
    def setUp(self):
        self.primary=build_matrix(registry_fixture())
        patcher=patch.object(experiments,'PRIMARY_SHA',canonical_digest(self.primary));patcher.start();self.addCleanup(patcher.stop)
        self.definitions=experiments.build_tensor_definitions(self.primary);self.definitions['full_input_audit']={'fixture':True}

    def test_closed16_specs_and_primary_guard_are_separate(self):
        for c in self.definitions['cases']:
            with self.subTest(case=c['id']):
                s=tensor.tensor_case_spec(self.primary,self.definitions,c['id'])
                self.assertEqual(s['case'],c);self.assertEqual(set(s['configs']),{'pretrained','scratch'})
                self.assertEqual(s['counts'],c['counts']);self.assertEqual(c['seed'],123)
                with self.assertRaises(ValueError):gates.case_spec(self.definitions,c['id'])
        for failure in ['partial','config','seed','audit']:
            d=copy.deepcopy(self.definitions)
            if failure=='partial':d['cases'].pop()
            elif failure=='config':d['cases'][0]['config']['epochs']=3
            elif failure=='seed':d['cases'][0]['seed']=456
            else:d.pop('full_input_audit')
            with self.subTest(failure=failure),self.assertRaises(ValueError):tensor.tensor_case_spec(self.primary,d,self.definitions['cases'][0]['id'])

    def test_all8_physical_formats_keep_rank_parity_and_original_tolerances(self):
        for case in self.definitions['cases'][::2]:
            with self.subTest(case=case['id']):tensor.checked_tensor_physics(physics(case,['a','b']),case,['a','b'])

    def test_wrong_geometry_declarations_and_mixed_gradients_are_rejected(self):
        for case in self.definitions['cases'][::2]:
            for failure in ['cpu','dtype','ids','rank','shape','parity','projection','guarantee','gradient','omitted_gradient']:
                v=physics(case,['a','b'])
                if failure=='cpu':v['device']='cpu'
                elif failure=='dtype':v['dtype']='torch.float64'
                elif failure=='ids':v['structure_ids'].reverse()
                elif failure=='gradient':v['mixed_parameter_gradient_norms']['backbone']=0.
                elif failure=='omitted_gradient':v['mixed_parameter_gradient_norms'].pop('backbone')
                else:
                    key={'rank':'rank','shape':'shape','parity':'inversion_parity','projection':'no_symmetry_projection','guarantee':'guarantee'}[failure]
                    v['response'][key]={'rank':2,'shape':[3,3],'parity':-v['response']['inversion_parity'],'projection':False,'guarantee':'SO3_cartesian'}[failure]
                with self.subTest(case=case['id'],failure=failure),self.assertRaises(ValueError):tensor.checked_tensor_physics(v,case,['a','b'])

    def test_physical_checks_cannot_be_optional_relabelled_or_missing(self):
        case=next(c for c in self.definitions['cases'] if c['model']=='mace' and c['task']=='piezoelectric')
        for failure in ['failed','optional','tolerance','missing','extra','nonfinite','negative_error','numeric','numeric_shape']:
            v=physics(case,['a','b']);check=v['checks']['response_auxiliary_finite_difference']
            if failure=='failed':check['passed']=False
            elif failure=='optional':check['required']=False
            elif failure=='tolerance':check['atol']=1.
            elif failure=='missing':v['checks'].pop('inversion_rank3_response')
            elif failure=='extra':v['checks']['invented']=copy.deepcopy(check)
            elif failure=='nonfinite':check['max_abs_error']=float('nan')
            elif failure=='negative_error':check['max_abs_error']=-1.
            elif failure=='numeric':v['response']['numeric'][0][0][0][0]=1.
            else:v['response']['numeric']=[[0.]]
            with self.subTest(failure=failure),self.assertRaises(ValueError):tensor.checked_tensor_physics(v,case,['a','b'])

    def test_actual_allocation_and_native_parity_cannot_be_replaced_by_counts(self):
        for case in self.definitions['cases'][::2]:
            tensor.checked_preparation_origin(origin(case),case)
            for failure in ['allocation','zero_gpu','bool_gpu','parity','missing_error','nonfinite','training']:
                v=origin(case)
                if failure=='allocation':v.pop('allocation')
                elif failure=='zero_gpu':v['allocation']['gpus']=0
                elif failure=='bool_gpu':v['allocation']['gpus']=True
                elif failure=='parity':v['native_parity']['structures']=1
                elif failure=='missing_error':v['native_parity'].pop('max_feature_error')
                elif failure=='nonfinite':v['native_parity']['max_feature_error']=float('inf')
                else:v['formal_training_launched']=True
                with self.subTest(case=case['id'],failure=failure),self.assertRaises(ValueError):tensor.checked_preparation_origin(v,case)

    def test_shared_graph_capacity_artifact_and_both_high_rank_physics_are_required(self):
        for task in ['piezoelectric','elastic']:
            with self.subTest(task=task),shared_evidence(task) as f:
                gate=gates._check_prepared_spec(f['matrix'],f['spec'],f['prepared'],budget_seconds=3600)
                self.assertEqual(gate['counts'],dict(train=3,validation=1,test=1))
                self.assertEqual(set(gate['physical_evidence_sha256']),{'pretrained','scratch'})
        for failure in ['identity','rows','probe','capacity_config','resolved','artifact','worker_count','versions','scratch','physics','budget']:
            with self.subTest(failure=failure),shared_evidence() as f:
                if failure=='identity':v=read(f['prepared']/'report.json');v['seed']=456;write(f['prepared']/'report.json',v)
                elif failure=='rows':p=f['prepared']/'graph-scan/graph-sizes.jsonl';p.write_bytes(p.read_bytes().splitlines()[0]+b'\n')
                elif failure=='probe':v=read(f['prepared']/'graph-scan/report.json');v['structures']=2;write(f['prepared']/'graph-scan/report.json',v)
                elif failure=='capacity_config':f['cap']['configs']['scratch']['seed']=456;write(f['prepared']/'capacity/report.json',f['cap'])
                elif failure=='resolved':v=read(f['prepared']/'capacity/config.scratch.resolved.json');v['batch_size']=2;write(f['prepared']/'capacity/config.scratch.resolved.json',v)
                elif failure=='artifact':Path('models/official/fixture.bin').write_bytes(b'changed')
                elif failure=='worker_count':f['workers'][0]['selected_training_structures']=2
                elif failure=='versions':f['workers'][0]['versions']['torch']='changed'
                elif failure=='scratch':f['workers'][1]['execution']['official']['parameter_coverage']=.5
                elif failure=='physics':v=read(f['prepared']/'derivatives-scratch.json');v['checks']['response_auxiliary_finite_difference']['required']=False;write(f['prepared']/'derivatives-scratch.json',v)
                with self.assertRaises(ValueError):gates._check_prepared_spec(f['matrix'],f['spec'],f['prepared'],budget_seconds=.1 if failure=='budget' else 3600)

    def test_retained_receipt_binds_real_request_terminal_owner_source_and_resources(self):
        case=self.definitions['cases'][0]
        with receipt_fixture(case) as f:
            result=tensor.checked_preparation_receipt(case,f['preparation'],f['prepared'],f['claim']/'job.json')
            self.assertEqual(result['slurm_job_id'],'1233');self.assertEqual(f['source_identity'].call_count,2)
        for failure in ['request','terminal_hash','terminal_owner','terminal_state','terminal_raw','resource','case','source_dirty']:
            with self.subTest(failure=failure),receipt_fixture(case) as f:
                if failure=='request':(f['claim']/'request.sh').write_bytes(b'changed')
                elif failure=='terminal_hash':f['terminal']['report_sha256']='f'*64
                elif failure in ['terminal_owner','terminal_state']:
                    f['terminal']['fields']['UserId' if failure=='terminal_owner' else 'JobState']='other(999)' if failure=='terminal_owner' else 'FAILED'
                    f['terminal']['raw']=' '.join(k+'='+shlex.quote(v) for k,v in f['terminal']['fields'].items())
                elif failure=='terminal_raw':f['terminal']['raw']+=' Extra=changed'
                elif failure=='resource':f['receipt']['sbatch_argv'][4]='--gres=gpu:0';f['terminal']['entry']=copy.deepcopy(f['receipt'])
                elif failure=='case':f['receipt']['seed']=456
                else:f['source_identity'].side_effect=lambda args,**kwargs:'a'*40+'\n' if 'rev-parse' in args else ' M source.py'
                write(f['claim']/'job.json',f['receipt']);write(f['claim']/'terminal.json',f['terminal'])
                with self.assertRaises(ValueError):tensor.checked_preparation_receipt(case,f['preparation'],f['prepared'],f['claim']/'job.json')

    def test_independent_wrapper_checks_both_physics_and_source_after_shared_gate(self):
        for case in self.definitions['cases'][::2]:
            with self.subTest(case=case['id']),wrapper_fixture(self.primary,self.definitions,case) as f:
                original=(f['preparation']/'report.json').read_bytes()
                result=tensor.check_tensor_preparation(f['root']/'definitions.json',case['id'],f['preparation'],
                    budget_seconds=3600,primary_path=f['root']/'primary.json')
                self.assertEqual(result['kind'],'independent_supplemental_tensor_execution_gate')
                self.assertEqual(result['physical_structure_ids'],['c','b']);self.assertEqual(result['formal_training_runs'],0)
                self.assertEqual(f['shared'].call_count,1);self.assertEqual(f['receipt'].call_count,1)
                self.assertEqual((f['preparation']/'report.json').read_bytes(),original)

    def test_independent_wrapper_rejects_incomplete_or_rebound_observations(self):
        case=self.definitions['cases'][0]
        for failure in ['pending','self_certified','cpu','audit','indices','ids','physical_hash','validator','estimate','definition','schedule']:
            with self.subTest(failure=failure),wrapper_fixture(self.primary,self.definitions,case) as f:
                if failure=='pending':f['prepared']['status']='running'
                elif failure=='self_certified':f['prepared']['independent_full_gate_pending']=False
                elif failure=='cpu':f['prepared']['allocation']['gpus']=0
                elif failure=='audit':f['audit'].return_value={'changed':True}
                elif failure=='indices':f['prepared']['physical_training_indices']=[0,1]
                elif failure=='ids':f['prepared']['physical_structure_ids']=['a','b']
                elif failure=='physical_hash':f['prepared']['physical_evidence_sha256']['scratch']='f'*64
                elif failure=='validator':f['prepared']['source_sha256']['src/universal_gnn/benchmarks/validation/cartesian.py']='f'*64
                elif failure=='estimate':f['prepared']['resource_estimate']['train_only_300_epoch_seconds']=1.
                elif failure=='definition':(f['root']/'definitions.json').write_bytes(b'changed')
                else:write(f['preparation']/'graph-scan/probe.json',dict(worst_indices=[2,1],warmup_batches=1,measure_batches=100))
                write(f['preparation']/'report.json',f['prepared'])
                with self.assertRaises(ValueError):tensor.check_tensor_preparation(f['root']/'definitions.json',case['id'],f['preparation'],
                    budget_seconds=3600,primary_path=f['root']/'primary.json')

    def test_login_guard_precedes_any_source_access(self):
        with patch.dict(os.environ,{},clear=True),self.assertRaisesRegex(RuntimeError,'Slurm'):
            tensor.check_tensor_preparation('missing','missing','missing',budget_seconds=3600)

    def test_public_pair_cli_preserves_both_modes_and_partial_failures(self):
        script=Path(__file__).resolve().parents[1]/'scripts/check_tensor_preparation.py'
        case=self.definitions['cases'][0]
        for failed_second in [False,True]:
            with self.subTest(failed_second=failed_second),wrapper_fixture(self.primary,self.definitions,case) as f,ExitStack() as stack:
                stack.enter_context(patch.object(gates,'compatible_sources',return_value='a'*40))
                stack.enter_context(patch('universal_gnn.benchmarks.submission.planning.measured_train_estimate',return_value=60.))
                stack.enter_context(patch('universal_gnn.benchmarks.submission.planning.partition_maximum',return_value=None))
                stub=dict(status='passed',common_batch_size=4,counts=case['counts'])
                full=stack.enter_context(patch.object(tensor,'check_tensor_preparation',side_effect=[stub,ValueError('fixture rejected scratch')] if failed_second else [stub,stub]))
                output=f['root']/'gate'
                argv=[str(script),'--definitions',str(f['root']/'definitions.json'),'--primary-matrix',str(f['root']/'primary.json'),
                      '--pair',case['pair_id'],'--preparation',str(f['preparation']),'--output',str(output)]
                stack.enter_context(patch.object(sys,'argv',argv))
                if failed_second:
                    with self.assertRaisesRegex(ValueError,'rejected scratch'):runpy.run_path(str(script),run_name='__main__')
                else:runpy.run_path(str(script),run_name='__main__')
                report=read(output/'report.json')
                self.assertEqual(report['status'],'failed' if failed_second else 'passed')
                self.assertEqual(report['formal_training_runs'],0);self.assertEqual(report['new_training_jobs'],0)
                self.assertEqual(full.call_count,2)
                self.assertTrue(full.call_args_list[0].args[1].endswith('--pretrained'))
                self.assertTrue(full.call_args_list[1].args[1].endswith('--scratch'))
                self.assertTrue((output/'gate-pretrained.json').exists())
                self.assertEqual((output/'gate-scratch.json').exists(),not failed_second)

    def test_public_cli_refuses_login_before_creating_output(self):
        script=Path(__file__).resolve().parents[1]/'scripts/check_tensor_preparation.py'
        with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',[str(script),'--pair','unused','--preparation','unused','--output','unused']),self.assertRaises(SystemExit) as caught:
            runpy.run_path(str(script),run_name='__main__')
        self.assertEqual(caught.exception.code,2)


def read(path):return json.loads(Path(path).read_bytes())


if __name__=='__main__':unittest.main()

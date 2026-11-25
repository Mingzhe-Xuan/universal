"""Standard-library tests; real model/CPU/CUDA controls run through Slurm."""

import copy
import unittest

from universal_gnn.data.preparation.qm9.conversion import numeric, parse_xyz
from universal_gnn.data.preparation.qm9.source import HARTREE_TO_EV, UNITS, excluded_ids
from universal_gnn.benchmarks.qm9.definitions import build_definitions, canonical
from universal_gnn.benchmarks.qm9.submission import campaign_layout, check_job, seconds
from universal_gnn.data.splits.manifest import create_manifest, validate_manifest
from universal_gnn.properties.catalog import property_spec


def xyz(index=1):
    return (f"3\ngdb {index} 1 2 3 0 4 -0.25 0.125 0.375 5 6 7 8 9 10 11\n"
            "O 0 0 0 -0.8\nH 0 0 1 0.4\nH 1 0 0 0.4\n100 200 300\nO O\nInChI=1/H2O InChI=1/H2O\n")


class QM9ParsingTests(unittest.TestCase):
    def test_original_columns_units_and_nonperiodic_geometry(self):
        row = parse_xyz(xyz())
        self.assertEqual(row['numbers'], [8, 1, 1])
        self.assertEqual(row['positions'], [[0.,0.,0.],[0.,0.,1.],[1.,0.,0.]])
        self.assertEqual(row['pbc'], [False]*3)
        self.assertAlmostEqual(row['targets']['homo'], -.25*HARTREE_TO_EV)
        self.assertAlmostEqual(row['targets']['lumo'], .125*HARTREE_TO_EV)
        self.assertEqual(row['targets']['dipole_magnitude'], 0.)
        self.assertEqual(row['targets']['isotropic_polarizability'], 4.)

    def test_fortran_and_mathematica_exponents(self):
        for text in ['1.25D-2', '1.25d-2', '1.25*^-2', '1.25e-2']:
            self.assertEqual(numeric(text), .0125)

    def test_reject_nonfinite_unknown_species_and_truncation(self):
        for text in [xyz().replace('O 0 0 0', 'O nan 0 0'), xyz().replace('O 0 0 0', 'Cl 0 0 0'),
                     xyz().replace('0 4 -0.25','-1 4 -0.25'), xyz().replace('0 4 -0.25','0 -4 -0.25'),
                     '\n'.join(xyz().splitlines()[:-2]), xyz(index=0), xyz().replace('gdb 1','other 1')]:
            with self.assertRaises(ValueError):
                parse_xyz(text)

    def test_exclusions_are_original_one_based_and_unique(self):
        self.assertEqual(excluded_ids('header\n# Index\n1 C C 0\n133885 O O 0\n',expected_count=2),{1,133885})
        for text in ['1 a\n1 b','0 a\n2 b','1 a']:
            with self.assertRaises(ValueError):excluded_ids(text,expected_count=2)

    def test_property_semantics(self):
        for name, unit in UNITS.items():
            p=property_spec(name)
            self.assertEqual((p.scope,p.shape,p.unit,p.kind,p.reduction,p.construction),
                             ('graph',(1,),unit,'regression','mean','direct'))


class QM9DefinitionsTests(unittest.TestCase):
    def fixtures(self):
        cases=[]
        for model in ['cgcnn','alignn','mace','nequip']:
            for mode in ['pretrained','scratch']:
                cfg=dict(seed=123,structures='all',dtype='float32',device='cuda',batch_size=32,epochs=300,
                         max_atoms=None,backbone=dict(name=model,implementation='official',initialization=mode),
                         task=dict(kind='supervised',property='bandgap'),prediction=dict(version=1,head_mode='reset',readout=dict(name='graph_mlp',pooling='mean')),
                         optimization=dict(train_backbone=True,train_readout=True),dataset=dict(path='old'))
                cases.append(dict(seed=123,task='bandgap',model=model,initialization=mode,config=cfg,python_environment='env-'+model))
        primary=dict(cases=cases)
        data=dict(status='passed',clean_count=130831,units=UNITS,dataset=dict(path='new',sha256='a'*64,split_manifest='split.json',split_manifest_sha256='b'*64))
        return primary,data

    def test_exact_32_matrix_keeps_official_initializations_and_original_recipe(self):
        primary,data=self.fixtures();original=copy.deepcopy(primary)
        result=build_definitions(primary,data)
        self.assertEqual(primary,original)
        self.assertEqual(len({c['id'] for c in result['cases']}),32)
        self.assertEqual(result['training_seeds'],[123])
        for c in result['cases']:
            cfg=c['config'];self.assertEqual(c['config_sha256'],canonical(cfg))
            self.assertEqual(cfg['dataset'],dict(data['dataset'],partition='train'))
            self.assertEqual(cfg['backbone']['initialization'],c['initialization'])
            self.assertEqual(cfg['task'],dict(kind='supervised',property=c['property']))
            if c['model'] in ['cgcnn','alignn']:
                self.assertEqual(cfg['backbone']['input_profile'],'molecular_radius')
                self.assertEqual(cfg['backbone']['input_cutoff'],6.)
        for prop in UNITS:
            self.assertEqual(sum(c['property']==prop for c in result['cases']),8)

    def test_reject_partial_data_wrong_units_and_ambiguous_template(self):
        primary,data=self.fixtures()
        for bad in [dict(data,status='running'),dict(data,clean_count=133885),dict(data,units={'homo':'Hartree'})]:
            with self.assertRaises(ValueError):build_definitions(primary,bad)
        primary['cases'].append(copy.deepcopy(primary['cases'][0]))
        with self.assertRaises(ValueError):build_definitions(primary,data)

    def test_group_split_is_training_seed_independent_complete_and_no_smiles_leakage(self):
        records=[dict(id=str(i),group=str(i//2)) for i in range(40)]
        m=create_manifest(records,source_sha256='a'*64,seed=0)
        self.assertEqual(m,create_manifest(records,source_sha256='a'*64,seed=0))
        self.assertEqual(sorted(sum(m['partitions'].values(),[])),list(range(40)))
        altered=copy.deepcopy(m)
        altered['partitions']['test'][0]=altered['partitions']['train'][0]
        with self.assertRaises(ValueError):validate_manifest(altered,source_sha256='a'*64,source_count=40)


class QM9SlurmTests(unittest.TestCase):
    def test_32_full_trainings_require_cpu_and_gpu_gates_and_independent_assessment(self):
        layout=campaign_layout();seen=set()
        self.assertEqual(len(layout),146)
        counts={}
        for stage in layout:
            self.assertNotIn(stage['key'],seen)
            if stage['parent'] is not None:self.assertIn(stage['parent'],seen)
            seen.add(stage['key']);kind=stage['command'][0];counts[kind]=counts.get(kind,0)+1
            if kind=='train':
                self.assertEqual(stage['parent'],'preflight-'+stage['options']['model'])
                self.assertEqual(stage['options']['gpus'],1)
                self.assertIn('--seed-123--',stage['key'])
            elif kind=='assess':self.assertEqual(stage['parent'],stage['command'][2])
            elif kind=='preflight':self.assertEqual(stage['parent'],'smoke-'+stage['options']['model'])
            elif kind=='terminal':self.assertEqual(stage['dependency_kind'],'afterany')
        self.assertEqual(counts,dict(prepare=1,terminal=73,smoke=4,preflight=4,train=32,assess=32))

    def test_identity_rejects_wrong_owner_source_gpu_time_and_held_dependency(self):
        e=dict(job='100',name='ugnn-qm9-test',source_checkout='/source',submission_token='token',cpus=2,
               memory_gib=64,gpus=1,time='14-00:00:00',dependency='afterok:99')
        f=dict(JobId='100',JobName=e['name'],WorkDir='/source',Comment='token',Partition='compute',ReqNodeList='node42',
               NumCPUs='2',MinMemoryNode='64G',Requeue='0',UserId='xmz(1010)',TimeLimit='14-00:00:00',
               TresPerNode='gres:gpu:1',JobState='PENDING',Priority='0',Reason='JobHeldUser',Dependency='afterok:99(unfulfilled)')
        check_job(e,f,held=True)
        for k,v in dict(JobId='999',UserId='other(1)',WorkDir='/wrong',Comment='wrong',TresPerNode='gres:gpu:2',
                        TimeLimit='00:01:00',Dependency='afterok:42(unfulfilled)',JobState='RUNNING',Priority='3').items():
            with self.assertRaises(ValueError):check_job(e,dict(f,**{k:v}),held=True)
        self.assertEqual(seconds('0-04:00:00'),seconds('04:00:00'))


if __name__=='__main__':unittest.main()

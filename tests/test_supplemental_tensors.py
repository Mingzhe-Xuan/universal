"""Pure contracted-label and cross-source split controls; no model runtime."""

import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.supplemental_tensors.partitions import AnchorConflict, build_partitions, task_manifest
from universal_gnn.benchmarks.supplemental_tensors.preparation import prepare_supplemental_tensors
from universal_gnn.benchmarks.supplemental_tensors.targets import elastic_targets, piezoelectric_targets
from universal_gnn.data.preparation.gmtnet import prepare_gmtnet


def candidate(identifier, geometry=None, reference=None):
    return dict(id=identifier, geometry=hashlib.sha256((geometry or identifier).encode()).hexdigest(), reference=reference)


def anchors():
    return [dict(candidate("anchor-"+role), role=role, group="original-"+role)
            for role in ("train", "validation", "test")]


class SupplementalTensorTests(unittest.TestCase):
    def test_all_cartesian_components_follow_released_pair_order_without_factor2(self):
        pairs={(0,0):0,(1,1):1,(2,2):2,(0,1):3,(1,0):3,(1,2):4,(2,1):4,(0,2):5,(2,0):5}
        piezo=[[100*i+j+.25 for j in range(6)] for i in range(3)]
        elastic=[[100*i+j+.25 for j in range(6)] for i in range(6)]
        p=piezoelectric_targets(dict(piezoelectric_C_m2=piezo))["piezoelectric"]
        c=elastic_targets(dict(elastic_total_kbar=elastic))["elastic"]
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    self.assertEqual(p[i][j][k],piezo[i][pairs[j,k]])
                    for l in range(3):self.assertEqual(c[i][j][k][l],.1*elastic[pairs[i,j]][pairs[k,l]])
        self.assertNotEqual(c[0][0][1][1],c[1][1][0][0])
        self.assertEqual(p[1][0][1],103.25)

    def test_zero_large_negative_and_major_asymmetric_labels_are_retained(self):
        p=piezoelectric_targets(dict(piezoelectric_C_m2=[[0.]*6 for _ in range(3)]))
        self.assertEqual(p['piezoelectric'],[[[0.]*3 for _ in range(3)] for _ in range(3)])
        values=[[1.e6 if i<j else -2.e6 for j in range(6)] for i in range(6)]
        c=elastic_targets(dict(elastic_total_kbar=values))['elastic']
        self.assertEqual(c[0][0][1][1],1.e5)
        self.assertEqual(c[1][1][0][0],-2.e5)

    def test_invalid_contract_labels_are_rejected(self):
        for converter,key,n in [(piezoelectric_targets,'piezoelectric_C_m2',3),(elastic_targets,'elastic_total_kbar',6)]:
            valid=[[1.]*6 for _ in range(n)]
            invalid=[None,'na',valid[:-1],valid+[valid[0]],[[1.]*5 for _ in range(n)]]
            for value in [True,float('nan'),float('inf'),'1']:
                changed=copy.deepcopy(valid);changed[0][0]=value;invalid.append(changed)
            for value in invalid:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):converter({key:value})

    def test_direct_id_geometry_and_reference_anchors_and_transitive_cross_task_group(self):
        primary=anchors();primary[2]['reference']='https://materialsproject.org/materials/mp-77/'
        rows=dict(piezoelectric=[candidate('anchor-train','other'),candidate('renamed','anchor-validation'),
                                 candidate('reference-only','extra','mp-77'),candidate('chain','anchor-train','mp-88')],
                  elastic=[candidate('new-elastic','new','mp-88')])
        result=build_partitions(rows,primary)
        mapped={row['id']:row for task in result['records'].values() for row in task}
        self.assertEqual(mapped['renamed']['role'],'validation')
        self.assertEqual(mapped['reference-only']['role'],'test')
        self.assertEqual(mapped['new-elastic']['role'],'train')
        self.assertEqual(mapped['new-elastic']['group'],mapped['chain']['group'])
        self.assertEqual(mapped['new-elastic']['direct_anchor_kinds'],[])
        self.assertIn('geometry',mapped['renamed']['direct_anchor_kinds'])
        self.assertIn('reference',mapped['reference-only']['direct_anchor_kinds'])

    def test_conflicting_primary_anchors_fail_without_moving_or_deleting_records(self):
        primary=anchors();before=copy.deepcopy(primary)
        rows=dict(piezoelectric=[candidate('anchor-train','bridge','mp-5')],
                  elastic=[candidate('anchor-test','different','mp-5')])
        with self.assertRaises(AnchorConflict) as caught:build_partitions(rows,primary)
        self.assertEqual(primary,before)
        self.assertEqual(caught.exception.conflicts[0]['roles'],['test','train'])
        self.assertEqual({r['task'] for r in caught.exception.conflicts[0]['members']}, {'dielectric','elastic','piezoelectric'})

    def test_seed_independent_task_splits_and_primary_original_groups_are_preserved(self):
        primary=anchors()
        extra=dict(candidate('another-primary','another-geometry'),role='train',group=primary[0]['group'])
        primary.append(extra)
        rows=dict(piezoelectric=[candidate('new-primary-name','another-geometry')],elastic=[candidate('isolated')])
        first=build_partitions(rows,primary,seed=0)
        reversed_rows={k:list(reversed(v)) for k,v in reversed(list(rows.items()))}
        second=build_partitions(reversed_rows,list(reversed(primary)),seed=0)
        mapping=lambda result:{(task,r['id']):(r['group'],r['role']) for task,rr in result['records'].items() for r in rr}
        self.assertEqual(mapping(first),mapping(second))
        self.assertEqual(first['records']['piezoelectric'][0]['role'],'train')
        for kind in rows:
            for row in first['records'][kind]:self.assertEqual(row['role'],mapping(second)[kind,row['id']][1])

    def test_invalid_identity_or_incomplete_anchors_and_manifest_ids_are_rejected(self):
        rows=dict(piezoelectric=[],elastic=[])
        with self.assertRaises(ValueError):build_partitions(rows,anchors()[:-1])
        rows['elastic']=[dict(id='bad',geometry='not-a-sha')]
        with self.assertRaises(ValueError):build_partitions(rows,anchors())
        with self.assertRaises(ValueError):task_manifest([dict(id='different',group='g')],source_sha256='a'*64,
            seed=0,partition_records=[dict(id='original',group='g',role='train')],protocol={})

    def fixture(self,root):
        rows=[]
        for i in range(15):
            n=24 if i==14 else 1
            rows.append(dict(JARVIS_ID='JVASP-'+str(i),dielectric=[[float(i),0.,0.],[0.,1.,0.],[0.,0.,2.]],
                piezoelectric_C_m2=[[0. if i==0 else (100*r+c+.25) for c in range(6)] for r in range(3)],
                elastic_total_kbar=[[100*r+c+.25 for c in range(6)] for r in range(6)],
                atoms=dict(elements=['Si']*n,coords=[[j*.1,i*.1,0.] for j in range(n)],
                           lattice_mat=[[8.,0.,0.],[0.,8.,0.],[0.,0.,8.]],cartesian=True)))
        piezo=root/'piezo.pkl';elastic=root/'elastic.pkl'
        piezo.write_bytes(pickle.dumps(rows));elastic.write_bytes(pickle.dumps(rows))
        raw_sha=hashlib.sha256(piezo.read_bytes()).hexdigest()
        prepare_gmtnet(piezo,root/'primary',expected_sha256=raw_sha)
        hashes=dict(piezoelectric=raw_sha,elastic=hashlib.sha256(elastic.read_bytes()).hexdigest(),
                    dielectric=hashlib.sha256((root/'primary/structures.jsonl').read_bytes()).hexdigest(),
                    dielectric_split=canonical_digest(json.loads((root/'primary/split.json').read_text())))
        return rows,piezo,elastic,hashes

    def run_preparation(self,root,piezo,elastic,hashes,name='supplemental'):
        return prepare_supplemental_tensors(piezo,elastic,root/'primary/structures.jsonl',root/'primary/split.json',
                                            root/name,expected_hashes=hashes)

    def test_complete_conversion_retains_full_geometry_labels_roles_units_and_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,piezo,elastic,hashes=self.fixture(root)
            report=self.run_preparation(root,piezo,elastic,hashes)
            self.assertEqual(report['status'],'passed');self.assertEqual(report['datasets_prepared'],2)
            primary=json.loads((root/'primary/split.json').read_text())
            primary_roles={primary['records'][i]['id']:role for role,ii in primary['partitions'].items() for i in ii}
            for kind,shape,unit in [('piezoelectric',[3,3,3],'C/m^2'),('elastic',[3,3,3,3],'GPa')]:
                audit=report['audits'][kind];self.assertEqual(audit['counts']['written_records'],15)
                self.assertEqual(audit['maximum_atoms'],24);self.assertEqual(audit['tasks'],[kind])
                self.assertEqual(audit['tensor_shape'],shape);self.assertEqual(audit['tensor_unit'],unit)
                manifest=json.loads((root/'supplemental'/kind/'split.json').read_text())
                roles={manifest['records'][i]['id']:role for role,ii in manifest['partitions'].items() for i in ii}
                self.assertEqual(roles,primary_roles)
            data=[json.loads(line) for line in (root/'supplemental/piezoelectric/structures.jsonl').read_text().splitlines()]
            self.assertEqual(data[0]['targets']['piezoelectric'],[[[0.]*3 for _ in range(3)] for _ in range(3)])
            self.assertEqual(data[-1]['numbers'],[14]*24)
            with self.assertRaises(FileExistsError):self.run_preparation(root,piezo,elastic,hashes)

    def test_invalid_record_and_identical_duplicate_are_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);rows,piezo,elastic,hashes=self.fixture(root)
            rows[3]['elastic_total_kbar']='na';rows.append(copy.deepcopy(rows[4]))
            elastic.write_bytes(pickle.dumps(rows));hashes['elastic']=hashlib.sha256(elastic.read_bytes()).hexdigest()
            report=self.run_preparation(root,piezo,elastic,hashes)
            audit=report['audits']['elastic'];self.assertEqual(audit['counts']['source_records'],16)
            self.assertEqual(audit['counts']['written_records'],14)
            self.assertEqual(audit['counts']['identical_duplicate_id'],1)
            self.assertEqual(audit['counts']['missing_nonfinite_or_wrong_tensor_shape'],1)

    def test_fixed_source_anchor_hash_order_and_restricted_pickle_guards(self):
        for kind in ['piezoelectric','elastic','dielectric','dielectric_split']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);_,piezo,elastic,hashes=self.fixture(root);hashes[kind]='0'*64
                with self.assertRaises(ValueError):self.run_preparation(root,piezo,elastic,hashes)
                self.assertEqual(json.loads((root/'supplemental/report.json').read_text())['status'],'failed')
                self.assertFalse((root/'supplemental/piezoelectric').exists())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);_,piezo,elastic,hashes=self.fixture(root)
            piezo.write_bytes(pickle.dumps(Path('not-allowed')));hashes['piezoelectric']=hashlib.sha256(piezo.read_bytes()).hexdigest()
            with self.assertRaises(pickle.UnpicklingError):self.run_preparation(root,piezo,elastic,hashes)

    def test_real_preparation_anchor_conflict_is_retained_before_writing_datasets(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);rows,piezo,elastic,hashes=self.fixture(root)
            manifest=json.loads((root/'primary/split.json').read_text())
            indices=[manifest['partitions'][role][0] for role in ['train','test']]
            for index in indices:rows[index]['reference']='mp-987654321'
            elastic.write_bytes(pickle.dumps(rows));hashes['elastic']=hashlib.sha256(elastic.read_bytes()).hexdigest()
            with self.assertRaises(AnchorConflict):self.run_preparation(root,piezo,elastic,hashes)
            report=json.loads((root/'supplemental/report.json').read_text())
            self.assertEqual(report['status'],'failed');self.assertEqual(report['stage'],'immutable_anchor_grouping')
            self.assertTrue((root/'supplemental/anchor-conflicts.json').exists())
            self.assertFalse((root/'supplemental/piezoelectric').exists())
            self.assertEqual(hashlib.sha256((root/'primary/structures.jsonl').read_bytes()).hexdigest(),hashes['dielectric'])

    def test_primary_order_and_geometry_guards_do_not_trust_a_new_checksum(self):
        for mode in ['order','geometry']:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);_,piezo,elastic,hashes=self.fixture(root)
                data=root/'primary/structures.jsonl'
                rows=[json.loads(line) for line in data.read_text().splitlines()]
                if mode=='order':rows[0],rows[1]=rows[1],rows[0]
                else:rows[0]['metadata']['geometry_sha256']='f'*64
                data.write_bytes(''.join(json.dumps(row)+'\n' for row in rows).encode())
                hashes['dielectric']=hashlib.sha256(data.read_bytes()).hexdigest()
                manifest=json.loads((root/'primary/split.json').read_text());manifest['source_sha256']=hashes['dielectric']
                (root/'primary/split.json').write_text(json.dumps(manifest))
                hashes['dielectric_split']=canonical_digest(manifest)
                with self.assertRaisesRegex(ValueError,'ordered IDs|geometry fingerprint'):
                    self.run_preparation(root,piezo,elastic,hashes)

    def test_login_cli_refuses_before_data_loading(self):
        script=Path(__file__).resolve().parents[1]/'scripts/prepare_supplemental_tensors.py'
        result=subprocess.run([sys.executable,str(script),'--elastic-source','unused','--output','unused'],
                              capture_output=True,text=True,env={k:v for k,v in os.environ.items() if k!='SLURM_JOB_ID'})
        self.assertNotEqual(result.returncode,0)
        self.assertIn('must run through Slurm',result.stderr)


if __name__=='__main__':unittest.main()

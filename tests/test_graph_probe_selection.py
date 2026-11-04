"""Complete-stream and extreme-selection fixtures; never construct a numerical graph."""

import copy
import hashlib
import json
import unittest

from universal_gnn.benchmarks.probes.selection import METRICS, select_probe
from universal_gnn.benchmarks.probes.schedule import iter_probe_batches


def fixtures(count=40):
    records=[dict(id=f'structure-{index}',source_index=10+3*index) for index in range(count)]
    rows=[dict(index=index,**record,atoms=2,native_edges=2,native_triplets=0,auxiliary_edges=0,maximum_degree=1)
          for index,record in enumerate(records)]
    binding=dict(source_sha256='a'*64,split_manifest_sha256='b'*64,graph_definition_sha256='c'*64,
                 dtype='float32',native_edge_kind='directed_edges')
    return rows,records,binding


class GraphProbeSelectionTests(unittest.TestCase):
    def test_complete_stream_selects_each_metric_extreme_and_true_ordinary_records(self):
        rows,records,binding=fixtures()
        rows[3]['atoms']=100
        rows[7].update(native_edges=1000,maximum_degree=10)
        rows[11].update(native_edges=50,native_triplets=500,maximum_degree=5)
        rows[13].update(auxiliary_edges=2000,maximum_degree=20)
        rows[17].update(native_edges=400,maximum_degree=300)
        probe=select_probe(iter(rows),records,binding,worst_per_metric=1,ordinary_count=3,measure_batches=3)
        self.assertEqual(set(probe['worst_indices']),{3,7,11,13,17})
        self.assertEqual(len(probe['selection']['ordinary_indices']),3)
        self.assertFalse(set(probe['selection']['ordinary_indices'])&set(probe['worst_indices']))
        self.assertEqual(len(probe['indices']),8)
        self.assertTrue(all(index<len(records) for index in probe['indices']))
        self.assertTrue(any(row['source_index']>=len(records) for row in probe['selection']['selected_records']))
        self.assertFalse(probe['coverage']['verified_full_training_scan'])
        self.assertTrue(probe['coverage']['complete_training_records_observed'])
        batches=[row for row in iter_probe_batches(probe,1) if row['phase']=='measure']
        self.assertEqual(len(batches),6)
        self.assertEqual({row['indices'][0] for row in batches if row['kind']=='worst'},{3,7,11,13,17})
        self.assertIn(batches[-1]['indices'][0],probe['selection']['ordinary_indices'])
        for metric in METRICS:
            self.assertEqual(probe['coverage']['sums'][metric],sum(row[metric] for row in rows))

    def test_missing_extra_misordered_or_duplicate_training_identities_are_rejected(self):
        rows,records,binding=fixtures()
        variants=[rows[:-1],rows+[rows[-1]],[rows[1],rows[0],*rows[2:]]]
        changed=copy.deepcopy(rows);changed[1]['id']=changed[0]['id'];variants.append(changed)
        changed=copy.deepcopy(rows);changed[1]['source_index']=changed[0]['source_index'];variants.append(changed)
        for stream in variants:
            with self.subTest(stream_length=len(stream)),self.assertRaises(ValueError):select_probe(stream,records,binding)
        for duplicate in ('id','source_index'):
            expected=copy.deepcopy(records);expected[1][duplicate]=expected[0][duplicate]
            with self.subTest(duplicate=duplicate),self.assertRaises(ValueError):select_probe(rows,expected,binding)

    def test_stable_ties_and_id_sampling_ignore_labels_and_input_order(self):
        rows,records,binding=fixtures()
        first=select_probe(rows,records,binding,worst_per_metric=2,ordinary_count=4)
        for row in rows:row['targets']={'not_used':'different label'}
        self.assertEqual(first,select_probe(rows,records,binding,worst_per_metric=2,ordinary_count=4))
        rows=list(reversed(rows));records=list(reversed(records))
        for index,row in enumerate(rows):row['index']=index
        second=select_probe(rows,records,binding,worst_per_metric=2,ordinary_count=4)
        chosen=lambda value:{row['id'] for row in value['selection']['selected_records']}
        self.assertEqual(chosen(first),chosen(second))
        self.assertEqual(first['selection']['worst_by_metric']['native_triplets'],[])

    def test_single_pass_keeps_bounded_candidates_and_row_digest(self):
        rows,records,binding=fixtures(1000)
        class Once:
            used=False
            def __iter__(self):
                if self.used:raise RuntimeError('Stream iterated twice')
                self.used=True;return iter(rows)
        probe=select_probe(Once(),records,binding,worst_per_metric=2,ordinary_count=32)
        self.assertLessEqual(len(probe['selection']['selected_records']),len(METRICS)*2+32)
        payload=b''.join(json.dumps(row,sort_keys=True,separators=(',',':')).encode()+b'\n' for row in rows)
        self.assertEqual(probe['coverage']['graph_size_rows_sha256'],hashlib.sha256(payload).hexdigest())
        self.assertEqual(probe['coverage']['structures'],1000)

    def test_invalid_counts_and_bindings_never_produce_partial_proof(self):
        rows,records,binding=fixtures()
        for key,value in [('atoms',0),('native_edges',True),('auxiliary_edges',-1),('maximum_degree',99),('source_index',True)]:
            changed=copy.deepcopy(rows);changed[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):select_probe(changed,records,binding)
        for key,value in [('dtype','float16'),('source_sha256','bad'),('native_edge_kind','physical_bonds')]:
            with self.subTest(key=key),self.assertRaises(ValueError):select_probe(rows,records,{**binding,key:value})
        for options in [dict(seed=True),dict(worst_per_metric=0),dict(ordinary_count=0),dict(measure_batches=True)]:
            with self.subTest(options=options),self.assertRaises(ValueError):select_probe(rows,records,binding,**options)

    def test_padding_semantics_and_binding_are_preserved_without_mutating_callers(self):
        rows,records,binding=fixtures()
        binding['native_edge_kind']='padded_neighbor_slots'
        before=copy.deepcopy((rows,records,binding))
        result=select_probe(rows,records,binding)
        self.assertEqual((rows,records,binding),before)
        binding['native_edge_kind']='directed_edges'
        self.assertEqual(result['coverage']['binding']['native_edge_kind'],'padded_neighbor_slots')


if __name__=='__main__':unittest.main()

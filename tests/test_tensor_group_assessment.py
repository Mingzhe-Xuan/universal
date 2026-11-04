import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

from universal_gnn.benchmarks.assessment import GroupedRegressionMetrics, evaluate_tensor_groups
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.data.splits.manifest import create_manifest


def fixture(root):
    zero = [[0., 0.], [0., 0.]]
    rows = [dict(id=str(i), targets={'raw_tensor': copy.deepcopy(zero)}) for i in range(4)]
    rows[-1]['targets']['raw_tensor'][0][0] = 1 / 3
    source = root / 'source.jsonl'
    source.write_bytes(b''.join((json.dumps(row) + '\n').encode() for row in rows))
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = create_manifest([dict(id=str(i), group=str(i)) for i in range(4)], source_sha256=sha,
                               official={'0': 'train', '1': 'validation', '2': 'test', '3': 'test'})
    split = root / 'split.json';split.write_text(json.dumps(manifest), encoding='utf8')
    config = dict(structures='all', dtype='float32', task=dict(kind='supervised', property='tensor'),
                  dataset=dict(path=str(source), sha256=sha, split_manifest=str(split), partition='train',
                               split_manifest_sha256=canonical_digest(manifest),
                               bindings=dict(tensor=dict(key='raw_tensor', unit='dimensionless'))))
    rounded = struct.unpack('f', struct.pack('f', 1 / 3))[0]
    predictions = [dict(id='2', predictions={'tensor': [[[1., 2.], [3., 4.]]]}, targets={'tensor': [zero]}),
                   dict(id='3', predictions={'tensor': [[[rounded + 1., 0.], [0., 0.]]]},
                        targets={'tensor': [[[rounded, 0.], [0., 0.]]]})]
    path = root / 'predictions.jsonl';path.write_text(''.join(json.dumps(row) + '\n' for row in predictions), encoding='utf8')
    report = dict(passed=True, config=config, selected_structures=1, heldout=dict(partition='test', checkpoint_role='validation_best',
                  structures=2, test_structures=2, source_sha256=sha, predictions=str(path),
                  declared_train_structures=1, validation_structures=1, source_structures=4,
                  selection=dict(best_sha256='a' * 64), metrics=dict(tensor=dict(structures=2, finite_elements=8,
                  masked_target_elements=0, zero_norm_target_structures=1, mae=11/8, rmse=math.sqrt(31/8),
                  mean_structure_frobenius_error=(math.sqrt(30)+1)/2))))
    report_path = root / 'training.json';report_path.write_text(json.dumps(report), encoding='utf8')
    return report_path, report, predictions


class TensorGroupAssessmentTests(unittest.TestCase):
    def test_zero_nonzero_absolute_components_and_missing_labels(self):
        metrics = GroupedRegressionMetrics((2, 2))
        self.assertEqual(metrics.update([[1., 2.], [3., 4.]], [[0., 0.], [0., -0.]]), 'zero')
        self.assertEqual(metrics.update([[3., 99.], [4., 0.]], [[1., None], [0., 0.]]), 'nonzero')
        self.assertIsNone(metrics.update([[8., 8.], [8., 8.]], [[None, None], [None, None]]))
        result = metrics.result();zero=result['groups']['zero'];nonzero=result['groups']['nonzero']
        self.assertEqual(result['structures'], 3)
        self.assertEqual(result['unlabelled_structures'], 1)
        self.assertEqual(result['overall']['metrics']['masked_target_elements'], 5)
        self.assertAlmostEqual(result['overall']['metrics']['mae'], 16/7)
        self.assertAlmostEqual(result['overall']['metrics']['rmse'], math.sqrt(50/7))
        self.assertEqual(zero['metrics']['mae'], 2.5)
        self.assertAlmostEqual(zero['metrics']['mean_structure_frobenius_error'], math.sqrt(30))
        self.assertIsNone(zero['metrics']['mean_relative_structure_frobenius_error'])
        self.assertEqual(nonzero['metrics']['mae'], 2.)
        self.assertEqual(nonzero['component_finite_counts'], [1, 0, 1, 1])
        self.assertEqual(nonzero['component_mae'], [2., None, 4., 0.])
        elements=result['component_label_groups']
        self.assertEqual(elements['zero']['finite_elements'],6)
        self.assertAlmostEqual(elements['zero']['mae'],14/6)
        self.assertAlmostEqual(elements['zero']['rmse'],math.sqrt(46/6))
        self.assertEqual(elements['zero']['component_mae'],[1.,2.,3.5,2.])
        self.assertEqual(elements['nonzero']['finite_elements'],1)
        self.assertEqual(elements['nonzero']['mae'],2.)

    def test_exact_zero_empty_groups_and_declared_layout(self):
        metrics = GroupedRegressionMetrics((1,));metrics.update([0.], [1e-20])
        self.assertIsNone(metrics.result()['groups']['zero']['metrics'])
        self.assertEqual(metrics.result()['groups']['nonzero']['metrics']['structures'], 1)
        for shape in [[], [True], [-1], None]:
            with self.subTest(shape=shape), self.assertRaises(ValueError):GroupedRegressionMetrics(shape)
        for prediction,target in [([[1,2]],[1]), ([True],[1]), ([float('nan')],[1])]:
            with self.subTest(prediction=prediction), self.assertRaises((ValueError,FloatingPointError)):
                metrics.update(prediction,target)

    def test_complete_source_dtype_targets_and_original_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,report,_=fixture(root);before=path.read_bytes()
            result=evaluate_tensor_groups(path,root/'out',shape=(2,2))
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual((result['status'],result['structures'],result['source_structures']),('passed',2,4))
            self.assertEqual(result['overall']['metrics']['mae'],11/8)
            self.assertEqual(result['groups']['zero']['metrics']['mae'],2.5)
            self.assertEqual(result['groups']['nonzero']['component_mae'],[1.,0.,0.,0.])
            self.assertEqual(result['component_label_groups']['zero']['finite_elements'],7)
            self.assertEqual(result['component_label_groups']['nonzero']['mae'],1.)
            self.assertEqual(result['unit'],'dimensionless')
            self.assertEqual(result['formal_training_runs'],0)
            self.assertEqual(result['best_checkpoint_sha256'],'a'*64)
            groups=[json.loads(line) for line in (root/'out/groups.jsonl').read_text().splitlines()]
            self.assertEqual(groups,[dict(id='2',group='zero'),dict(id='3',group='nonzero')])
            self.assertEqual(result['prediction_sha256'],hashlib.sha256(Path(report['heldout']['predictions']).read_bytes()).hexdigest())

    def test_source_and_manifest_identity_cannot_be_replaced(self):
        for change in ['bytes','manifest','order']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path,report,_=fixture(root)
                if change=='bytes':
                    with Path(report['config']['dataset']['path']).open('ab') as stream:stream.write(b' \n')
                else:
                    manifest=json.loads((root/'split.json').read_text());manifest['records'][0]['id']='changed'
                    (root/'split.json').write_text(json.dumps(manifest))
                    if change=='order':
                        report['config']['dataset']['split_manifest_sha256']=canonical_digest(manifest)
                        path.write_text(json.dumps(report))
                with self.assertRaisesRegex(ValueError,'fingerprint|IDs/order'):
                    evaluate_tensor_groups(path,root/'out',shape=(2,2))
                self.assertFalse((root/'out/report.json').exists())

    def test_float64_labels_are_preserved_without_float32_rounding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,report,rows=fixture(root)
            report['config']['dtype']='float64'
            rows[1]['targets']['tensor'][0][0][0]=1/3
            rows[1]['predictions']['tensor'][0][0][0]=1+1/3
            Path(report['heldout']['predictions']).write_text(''.join(json.dumps(row)+'\n' for row in rows))
            path.write_text(json.dumps(report))
            result=evaluate_tensor_groups(path,root/'out',shape=(2,2))
            self.assertEqual(result['dtype'],'float64')
            self.assertAlmostEqual(result['overall']['metrics']['mae'],11/8)

    def test_invalid_predictions_labels_and_metric_population_rejected(self):
        for change in ['duplicate','missing','foreign','label','shape','nonfinite','population']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path,report,rows=fixture(root)
                if change=='duplicate':rows.append(copy.deepcopy(rows[0]))
                elif change=='missing':rows.pop()
                elif change=='foreign':rows[0]['id']='0'
                elif change=='label':rows[1]['targets']['tensor'][0][0][0]=1/3
                elif change=='shape':rows[0]['predictions']['tensor']=[[[1.,2.,3.,4.]]]
                elif change=='nonfinite':rows[0]['predictions']['tensor'][0][0][0]=float('inf')
                else:report['heldout']['metrics']['tensor']['finite_elements']=7
                Path(report['heldout']['predictions']).write_text(''.join(json.dumps(row)+'\n' for row in rows))
                path.write_text(json.dumps(report))
                with self.assertRaises((ValueError,FloatingPointError)):
                    evaluate_tensor_groups(path,root/'out',shape=(2,2))
                self.assertFalse((root/'out/report.json').exists())

    def test_transforms_debug_subsets_and_existing_outputs_refused(self):
        for change in ['binding','subset','role','dtype','counts']:
            with self.subTest(change=change),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path,report,_=fixture(root)
                if change=='binding':report['config']['dataset']['bindings']['tensor']['factor']=2.
                elif change=='subset':report['config']['structures']=2
                elif change=='role':report['heldout']['partition']='validation'
                elif change=='dtype':report['config']['dtype']='float16'
                else:report['selected_structures']=2
                path.write_text(json.dumps(report))
                with self.assertRaises(ValueError):evaluate_tensor_groups(path,root/'out',shape=(2,2))
                self.assertFalse((root/'out/report.json').exists())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path,_,_=fixture(root);(root/'out').mkdir();(root/'out/keep').write_text('keep')
            with self.assertRaises(FileExistsError):evaluate_tensor_groups(path,root/'out',shape=(2,2))
            self.assertEqual((root/'out/keep').read_text(),'keep')


if __name__=='__main__':unittest.main()

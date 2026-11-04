import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from universal_gnn.benchmarks.baselines import evaluate_scalar_mean
from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.data.splits.manifest import create_manifest


def fixture(root, targets=None):
    values = [1.,3.,5.,1000.,-1000.,-999.,7.] if targets is None else targets
    rows = [dict(id=str(i),targets={'gap':value}) for i,value in enumerate(values)]
    source = root/'data.jsonl'
    source.write_bytes(b''.join((json.dumps(row)+'\n').encode() for row in rows))
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = create_manifest([dict(id=row['id'],group=row['id']) for row in rows],source_sha256=sha,
                               official={str(i):'train' if i<3 else 'validation' if i<5 else 'test' for i in range(7)})
    path = root/'split.json';path.write_text(json.dumps(manifest),encoding='utf8')
    return dict(structures='all',task=dict(kind='supervised',property='bandgap'),
                dataset=dict(path=str(source),sha256=sha,partition='train',split_manifest=str(path),
                             split_manifest_sha256=canonical_digest(manifest),
                             bindings=dict(bandgap=dict(key='gap',unit='eV'))))


class ScalarBaselineTests(unittest.TestCase):
    def test_train_only_mean_complete_heldout_and_original_unit_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=fixture(root);original=copy.deepcopy(config)
            result=evaluate_scalar_mean(config,root/'out')
            self.assertEqual(config,original)
            self.assertEqual(result['training_mean'],3.)
            self.assertEqual(result['training_structures'],3)
            self.assertEqual(result['partitions']['validation']['mae'],1000.)
            self.assertEqual(result['partitions']['test']['mae'],503.)
            self.assertAlmostEqual(result['partitions']['test']['rmse'],502010.**.5)
            rows=[json.loads(line) for line in (root/'out/predictions.jsonl').read_text().splitlines()]
            self.assertEqual([row['id'] for row in rows],['3','4','5','6'])
            self.assertTrue(all(row['unit']=='eV' and row['prediction']==3. for row in rows))
            self.assertEqual(result['formal_training_runs'],0)

    def test_changed_source_bytes_cannot_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=fixture(root)
            with Path(config['dataset']['path']).open('ab') as stream:stream.write(b' \n')
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                evaluate_scalar_mean(config,root/'out')
            self.assertFalse((root/'out/report.json').exists())

    def test_manifest_hash_and_order_are_checked_independently(self):
        for wrong_hash in [True,False]:
            with self.subTest(wrong_hash=wrong_hash),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config=fixture(root)
                manifest=json.loads(Path(config['dataset']['split_manifest']).read_text())
                manifest['records'][0]['id']='different'
                Path(config['dataset']['split_manifest']).write_text(json.dumps(manifest),encoding='utf8')
                if not wrong_hash:config['dataset']['split_manifest_sha256']=canonical_digest(manifest)
                with self.assertRaisesRegex(ValueError,'fingerprint|IDs/order'):
                    evaluate_scalar_mean(config,root/'out')
                self.assertFalse((root/'out/report.json').exists())

    def test_invalid_scalar_labels_are_rejected_without_completed_report(self):
        for value in [float('nan'),True,[1.,2.]]:
            with self.subTest(value=value),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config=fixture(root,[1.,3.,5.,value,-1000.,-999.,7.])
                with self.assertRaisesRegex(ValueError,'finite label'):
                    evaluate_scalar_mean(config,root/'out')
                self.assertFalse((root/'out/report.json').exists())

    def test_existing_results_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=fixture(root)
            evaluate_scalar_mean(config,root/'out');original=(root/'out/report.json').read_bytes()
            with self.assertRaises(FileExistsError):evaluate_scalar_mean(config,root/'out')
            self.assertEqual((root/'out/report.json').read_bytes(),original)

    def test_partial_selection_and_nontraining_fit_are_refused(self):
        for patch in [dict(structures=3),dict(max_atoms=2),dict(partition='test')]:
            with self.subTest(patch=patch),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);config=fixture(root)
                if 'partition' in patch:config['dataset'].update(patch)
                else:config.update(patch)
                with self.assertRaises(ValueError):evaluate_scalar_mean(config,root/'out')


if __name__=='__main__':
    unittest.main()

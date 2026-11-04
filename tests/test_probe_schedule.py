"""Independent coverage assertions; no model, Torch import or numerical work."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest

from universal_gnn.benchmarks.probes.schedule import iter_probe_batches, schedule_settings


class ProbeScheduleTests(unittest.TestCase):
    def test_batch_one_short_sampling_covers_all_worst_after_warmup(self):
        probe=dict(indices=list(range(10)),worst_indices=[9,8,7,6,5,4,3],warmup_batches=1,measure_batches=5)
        settings=schedule_settings(probe,1)
        batches=list(iter_probe_batches(probe,1))
        self.assertEqual(settings['requested_measure_batches'],5)
        self.assertEqual(settings['measure_batches'],7)
        self.assertEqual([row['indices'][0] for row in batches if row['phase']=='measure'],probe['worst_indices'])
        self.assertEqual([row['phase'] for row in batches],['warmup']+['measure']*7)

    def test_each_extreme_fills_a_full_batch_instead_of_packing_extremes_together(self):
        for size in (1,2,8):
            probe=dict(indices=[0,1,2,3],worst_indices=[1,3],warmup_batches=2,measure_batches=2)
            batches=list(iter_probe_batches(probe,size))
            measured=[row['indices'] for row in batches if row['phase']=='measure']
            self.assertEqual(measured,[[1]*size,[3]*size])
            self.assertTrue(all(len(row['indices'])==size for row in batches))

    def test_training_budget_retained_and_remaining_measurements_cycle_ordinary_indices(self):
        probe=dict(indices=[0,2,4,6],worst_indices=[6,2,4],warmup_batches=2,measure_batches=100)
        batches=list(iter_probe_batches(probe,3));measured=[row for row in batches if row['phase']=='measure']
        self.assertEqual(len(batches),102);self.assertEqual(len(measured),100)
        self.assertEqual([row['kind'] for row in measured[:4]],['worst']*3+['ordinary'])
        self.assertEqual(measured[3]['indices'],[0,2,4]);self.assertEqual(measured[4]['indices'],[6,0,2])
        self.assertEqual({index for row in measured[3:] for index in row['indices']},set(probe['indices']))

    def test_defaults_are_deterministic_and_leave_inputs_unchanged(self):
        probe=dict(indices=[5,1,9]);before=copy.deepcopy(probe)
        first=list(iter_probe_batches(probe,2));second=list(iter_probe_batches(probe,2))
        self.assertEqual(first,second);self.assertEqual(probe,before)
        self.assertEqual(len(first),102)
        self.assertEqual([row['indices'] for row in first[2:5]],[[5,5],[1,1],[9,9]])

    def test_invalid_sets_or_counts_cannot_drop_or_duplicate_worst(self):
        for change in (dict(indices=[]),dict(indices=[0,0]),dict(indices=[True]),dict(indices=[-1]),
                       dict(worst_indices=[]),dict(worst_indices=[0,0]),dict(worst_indices=[3]),
                       dict(worst_indices=[False]),dict(measure_batches=0),dict(warmup_batches=True)):
            with self.subTest(change=change),self.assertRaises(ValueError):
                list(iter_probe_batches({**dict(indices=[0,1]),**change},1))
        for batch in (0,True,1.5):
            with self.subTest(batch=batch),self.assertRaises(ValueError):schedule_settings(dict(indices=[0]),batch)

    def test_metadata_import_requires_no_torch_or_site_packages(self):
        env={**os.environ,'PYTHONPATH':str(Path('src').resolve())}
        result=subprocess.run([sys.executable,'-S','-c',
            'import sys; import universal_gnn.benchmarks.probes.schedule; import universal_gnn.benchmarks.probe_worker; assert "torch" not in sys.modules'],
            env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()

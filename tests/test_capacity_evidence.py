from contextlib import contextmanager
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.experiments.registry import canonical_digest
from universal_gnn.benchmarks.pairing.capacity import run_paired_capacity
from universal_gnn.benchmarks.pairing.evidence import verify_capacity_evidence
_fixtures = runpy.run_path(str(Path(__file__).with_name('test_paired_capacity.py')))
configurations, WORKER = _fixtures['configurations'], _fixtures['WORKER']


@contextmanager
def receipt(batch=32, scenario='stable'):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        addition="""
if result['status']=='passed':
 result.update(stage='complete',measured_batches=100,completed_worst_indices=request['probe']['worst_indices'],
  all_declared_worst_cases_completed=True,peak_allocated_bytes=128,peak_reserved_bytes=256)
"""
        worker=WORKER.replace('json.dump(result,open(sys.argv[2],"w"));sys.exit(code)',
                              addition+'\njson.dump(result,open(sys.argv[2],"w"));sys.exit(code)')
        (root/'capacity_evidence_worker.py').write_text(worker,encoding='utf8')
        probe=dict(indices=[0,1,2],worst_indices=[2],warmup_batches=2,measure_batches=100)
        environment={'PYTHONPATH':str(root)+os.pathsep+os.environ.get('PYTHONPATH',''),
                     'PAIR_FIXTURE_SCENARIO':scenario,'PAIR_FIXTURE_HISTORY':str(root/'history.jsonl')}
        with patch.dict(os.environ,environment):
            result=run_paired_capacity(configurations(batch),root/'capacity',probe=probe,python=sys.executable,
                                       worker_module='capacity_evidence_worker')
        yield root/'capacity',probe,result


class CapacityEvidenceTests(unittest.TestCase):
    def test_no_retry_has_four_complete_trials(self):
        with receipt(batch=2) as (root,probe,_):
            result=verify_capacity_evidence(root,probe)
            self.assertEqual((result['trial_count'],result['successful_worker_count'],result['cuda_oom_attempts']),(4,4,0))

    def test_typed_oom_attempts_are_retained_and_accepted(self):
        with receipt() as (root,probe,_):
            result=verify_capacity_evidence(root,probe)
            self.assertEqual(result['trial_count'],4)
            self.assertEqual(result['common_batch_size'],4)
            self.assertEqual(result['cuda_oom_attempts'],5)
            self.assertEqual(len(list(root.rglob('result.json'))),9)

    def test_common_retry_requires_a_fresh_success_for_both_modes(self):
        with receipt(scenario='shrink') as (root,probe,_):
            result=verify_capacity_evidence(root,probe)
            self.assertEqual(result['trial_count'],6)
            self.assertEqual(result['successful_worker_count'],6)
            self.assertEqual(result['common_batch_size'],2)
            self.assertEqual([r['batch_size'] for r in result['successful_workers'][-2:]],[2,2])

    def test_unknown_worker_error_never_becomes_accepted_retry(self):
        with receipt(scenario='unknown') as (root,probe,capacity):
            self.assertFalse(capacity['passed'])
            with self.assertRaises(ValueError):verify_capacity_evidence(root,probe)

    def test_semantically_invalid_attempts_fail_even_with_matching_parent_hash(self):
        for failure in ['exit','type','measure','worst','phase','request']:
            with self.subTest(failure=failure),receipt() as (root,probe,capacity):
                trial=capacity['trials'][0];path=Path(trial['directory'])/'report.json'
                parent=json.loads(path.read_text())
                if failure=='exit':parent['attempts'][0]['returncode']=1
                elif failure=='type':parent['attempts'][0]['worker']['error_type']='RuntimeError'
                else:
                    attempt=parent['attempts'][-1]
                    if failure=='measure':attempt['worker']['measured_batches']=99
                    elif failure=='worst':attempt['worker']['completed_worst_indices']=[]
                    elif failure=='phase':attempt['worker']['phase']='sample'
                    else:
                        request=Path(attempt['directory'])/'request.json';value=json.loads(request.read_text())
                        value['config']['batch_size']=999;request.write_text(json.dumps(value),encoding='utf8')
                for attempt in parent['attempts']:
                    (Path(attempt['directory'])/'result.json').write_text(json.dumps(attempt['worker']),encoding='utf8')
                path.write_text(json.dumps(parent),encoding='utf8');trial['report_sha256']=canonical_digest(parent)
                (root/'report.json').write_text(json.dumps(capacity),encoding='utf8')
                with self.assertRaises(ValueError):verify_capacity_evidence(root,probe)

    def test_parent_hash_and_final_common_batch_are_verified(self):
        for failure in ['hash','common']:
            with self.subTest(failure=failure),receipt(batch=2) as (root,probe,capacity):
                if failure=='hash':
                    path=Path(capacity['trials'][0]['directory'])/'report.json'
                    value=json.loads(path.read_text());value['started_at']='changed';path.write_text(json.dumps(value),encoding='utf8')
                else:
                    capacity['common_batch_size']=1;(root/'report.json').write_text(json.dumps(capacity),encoding='utf8')
                with self.assertRaises(ValueError):verify_capacity_evidence(root,probe)


if __name__=='__main__':unittest.main()

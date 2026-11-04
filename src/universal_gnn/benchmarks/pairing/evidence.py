"""Verify retained capacity receipts, including legitimate typed-OOM retries."""
import json
from pathlib import Path

from ..experiments.registry import canonical_digest


def verify_capacity_evidence(directory, probe, *, minimum_batches=100):
    """Return successful workers and audit counts; never execute a model or retry."""
    directory = Path(directory).resolve()
    capacity = json.loads((directory/'report.json').read_text(encoding='utf8'))
    if (capacity.get('version') != 1 or capacity.get('kind') != 'paired_capacity' or
            capacity.get('status') != 'passed' or capacity.get('passed') is not True or
            capacity.get('phase') not in {'train','sample'} or capacity.get('probe') != probe):
        raise ValueError('Capacity receipt is incomplete or belongs to another probe')
    common = capacity.get('common_batch_size')
    if type(common) is not int or common < 1 or type(minimum_batches) is not int or minimum_batches < 1:
        raise ValueError('Capacity common batch/minimum must be positive integers')
    trials = capacity.get('trials', [])
    if len(trials) < 4 or len(trials) % 2:
        raise ValueError('Require both individual trials and complete common trial pairs')
    workers, parent_reports, oom_count = [], [], 0
    for trial in trials:
        target = Path(trial['directory']).resolve()
        if not target.is_relative_to(directory):
            raise ValueError('Trial directory is outside the capacity output')
        parent = json.loads((target/'report.json').read_text(encoding='utf8'))
        if (not trial.get('passed') or parent.get('passed') is not True or parent.get('status') != 'passed' or
                canonical_digest(parent) != trial['report_sha256'] or parent.get('probe') != probe or
                parent.get('phase') != capacity['phase'] or
                parent['config']['backbone']['initialization'] != trial['initialization']):
            raise ValueError('Preflight trial identity/hash/acceptance mismatch')
        batch = parent['initial_batch_size']
        attempts = parent.get('attempts', [])
        if not attempts:
            raise ValueError('Preflight has no retained attempts')
        for index, attempt in enumerate(attempts):
            path = Path(attempt['directory']).resolve()
            if not path.is_relative_to(target):
                raise ValueError('Worker attempt is outside its trial')
            request = json.loads((path/'request.json').read_text(encoding='utf8'))
            worker = json.loads((path/'result.json').read_text(encoding='utf8'))
            expected = dict(parent['config'], batch_size=batch)
            if (attempt.get('batch_size') != batch or request.get('config') != expected or
                    request.get('probe') != probe or request.get('phase') != capacity['phase'] or
                    worker != attempt.get('worker') or worker.get('version') != 1 or
                    worker.get('batch_size') != batch or worker.get('phase') != capacity['phase']):
                raise ValueError('Worker identity/request/retained result mismatch')
            if index < len(attempts)-1:
                if (batch <= 1 or attempt.get('returncode') != 42 or attempt.get('status') != 'cuda_oom' or
                        worker.get('status') != 'cuda_oom' or worker.get('error_type') != 'cuda_out_of_memory'):
                    raise ValueError('Only typed CUDA OOM may precede a smaller successful attempt')
                batch = max(1, batch//2)
                oom_count += 1
            else:
                if (attempt.get('returncode') != 0 or attempt.get('status') != 'passed' or
                        worker.get('status') != 'passed' or worker.get('stage') != 'complete' or
                        worker.get('measured_batches', 0) < max(minimum_batches, probe['measure_batches']) or
                        worker.get('completed_worst_indices') != probe['worst_indices'] or
                        worker.get('all_declared_worst_cases_completed') is not True or
                        worker.get('peak_allocated_bytes', 0) <= 0 or worker.get('peak_reserved_bytes', 0) <= 0):
                    raise ValueError('Final worker lacks complete measured/worst-case GPU acceptance')
                workers.append(worker)
        if batch != parent['final_batch_size'] or batch != trial['final_batch_size']:
            raise ValueError('Final batch differs from its accepted worker')
        parent_reports.append(parent)
    if ([t['initialization'] for t in trials[:2]] != ['pretrained','scratch'] or
            any(t['stage'] != 'individual' for t in trials[:2])):
        raise ValueError('Individual initialization trials are missing')
    candidate = min(t['final_batch_size'] for t in trials[:2])
    for offset in range(2,len(trials),2):
        pair = trials[offset:offset+2]
        stage = f'common-{offset//2:02d}-b{candidate}'
        if ([t['initialization'] for t in pair] != ['pretrained','scratch'] or
                any(t['stage'] != stage for t in pair) or
                any(p['initial_batch_size'] != candidate for p in parent_reports[offset:offset+2])):
            raise ValueError('Common-batch trial ordering or requested batch differs')
        accepted = min(t['final_batch_size'] for t in pair)
        if offset+2 == len(trials):
            if common != candidate or any(t['final_batch_size'] != common for t in pair):
                raise ValueError('Both final modes must be rechecked at the declared common batch')
        elif accepted >= candidate:
            raise ValueError('A repeated common round must follow a reduced batch')
        candidate = accepted
    return dict(phase=capacity['phase'], common_batch_size=common, trial_count=len(trials),
                successful_workers=workers, successful_worker_count=len(workers),
                cuda_oom_attempts=oom_count, capacity_sha256=canonical_digest(capacity))

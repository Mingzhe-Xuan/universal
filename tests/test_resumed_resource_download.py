"""Pinned resource I/O and actual loopback curl, without numerical/model libraries."""

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/download_offline_cuda_resources.py'
spec=importlib.util.spec_from_file_location('resumed_resource_worker',SCRIPT)
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


class ResumedDownloadTests(unittest.TestCase):
    def setUp(self):
        base=Path('tmp').resolve();base.mkdir(exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(prefix='resource-tests-',dir=base)
        self.root=Path(self.temporary.name).resolve();self.base=base
        self.data=bytes(range(128))*8
        self.resource=dict(filename='fixture.whl',size=len(self.data),sha256=hashlib.sha256(self.data).hexdigest())
        self.calls=0

    def tearDown(self):
        if not self.root.is_relative_to(self.base):raise RuntimeError('Temporary cleanup escaped the test workspace')
        self.temporary.cleanup()

    def runner(self,args,**kwargs):
        self.calls+=1
        parts=[[]]
        for arg in args[2:]:
            if arg=='--next':parts.append([])
            else:parts[-1].append(arg)
        metrics=[]
        for index,part in enumerate(parts):
            start,end=map(int,part[part.index('--header')+1].split('=')[1].split('-'))
            output=Path(part[part.index('--output')+1]);header=Path(part[part.index('--dump-header')+1])
            header.write_text(f'HTTP/1.1 206 Partial Content\nContent-Range: bytes {start}-{end}/{len(self.data)}\n\n')
            with output.open('ab') as stream:stream.write(self.data[start:end+1])
            metrics.append(dict(http_code=206,size_download=end-start+1,num_connects=1 if index==0 else 0,exitcode=0))
        return subprocess.CompletedProcess(args,0,'\n'.join(json.dumps(row) for row in metrics),'')

    def download(self,**kwargs):
        return worker.download_resource(self.resource,self.root,base_url='http://127.0.0.1:54339/cuda/',
            runner=kwargs.pop('runner',self.runner),chunk_bytes=128,chunks=3,sleep=lambda seconds:None,**kwargs)

    def test_range_tail_and_non_aligned_existing_resume(self):
        self.assertEqual(worker.ranges_for(3,10,4,2),[(3,6),(7,9)])
        self.assertEqual(worker.ranges_for(10,10,4,2),[])
        partial=self.root/'fixture.whl.partial';partial.write_bytes(self.data[:13])
        final=self.download()
        self.assertEqual(final.read_bytes(),self.data);self.assertFalse(partial.exists());self.assertGreater(self.calls,1)
        for values in [(True,10,4,2),(11,10,4,2),(0,10,0,2),(0,10,4,33)]:
            with self.assertRaises(ValueError):worker.ranges_for(*values)

    def test_interrupted_prefix_is_resumed_without_losing_or_duplicating_bytes(self):
        original=self.runner
        def interrupted(args,**kwargs):
            if not self.calls:
                self.calls+=1;part=args[2:]
                output=Path(part[part.index('--output')+1]);header=Path(part[part.index('--dump-header')+1])
                output.write_bytes(self.data[:17]);header.write_text(f'HTTP/1.1 206 Partial Content\nContent-Range: bytes 0-127/{len(self.data)}\n\n')
                return subprocess.CompletedProcess(args,28,json.dumps(dict(http_code=206,size_download=17,exitcode=28)),'timeout')
            return original(args,**kwargs)
        self.assertEqual(self.download(runner=interrupted).read_bytes(),self.data)

    def test_invalid_range_or_append_count_rolls_back_only_unverified_suffix(self):
        original=self.runner
        for scenario in ('header','bytes','malformed'):
            partial=self.root/'fixture.whl.partial';partial.write_bytes(self.data[:13])
            def invalid(args,**kwargs):
                result=original(args,**kwargs)
                if scenario=='header':Path(args[args.index('--dump-header')+1]).write_text('Content-Range: bytes 0-127/1024\n')
                elif scenario=='bytes':
                    with partial.open('ab') as stream:stream.write(b'wrong')
                else:result.stdout='not-json'
                return result
            with self.subTest(scenario=scenario),self.assertRaises(ValueError):self.download(runner=invalid)
            self.assertEqual(partial.read_bytes(),self.data[:13]);self.assertFalse((self.root/'fixture.whl').exists())

    def test_wrong_full_sha_never_publishes_a_final_wheel(self):
        self.resource['sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'SHA'):self.download()
        self.assertFalse((self.root/'fixture.whl').exists());self.assertTrue((self.root/'fixture.whl.partial').exists())

    def test_verified_existing_skips_network_and_conflict_is_preserved(self):
        final=self.root/'fixture.whl';final.write_bytes(self.data)
        self.assertEqual(self.download(),final);self.assertEqual(self.calls,0)
        final.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError,'Conflicting'):self.download()
        self.assertEqual(final.read_bytes(),b'other');self.assertEqual(self.calls,0)

    def test_no_progress_is_bounded_and_ruleset_rejection_never_retried(self):
        elapsed=[0];calls=[0]
        def clock():elapsed[0]+=6;return elapsed[0]
        def empty(args,**kwargs):
            calls[0]+=1;return subprocess.CompletedProcess(args,28,json.dumps(dict(http_code=0,size_download=0)), 'timeout')
        with self.assertRaisesRegex(RuntimeError,'No download progress'):
            self.download(runner=empty,clock=clock,progress_timeout=10)
        self.assertEqual(calls[0],2)
        def denied(args,**kwargs):
            calls[0]+=1;return subprocess.CompletedProcess(args,97,json.dumps(dict(http_code=0,size_download=0)), 'SOCKS ruleset rejected')
        with self.assertRaisesRegex(RuntimeError,'Unexpected curl failure 97'):self.download(runner=denied)
        self.assertEqual(calls[0],3)

    def test_disk_reserve_stops_before_network(self):
        usage=type('Usage',(),dict(free=0))()
        with patch.object(worker.shutil,'disk_usage',return_value=usage),self.assertRaisesRegex(OSError,'reserve'):
            self.download()
        self.assertEqual(self.calls,0)

    def test_real_curl_reuses_connection_and_validates_resumed_bytes(self):
        data=self.data;ports=[]
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*args):pass
            def do_GET(self):
                ports.append(self.client_address[1])
                start,end=map(int,self.headers['Range'].split('=')[1].split('-'))
                body=data[start:end+1]
                self.send_response(206);self.send_header('Content-Length',str(len(body)))
                self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}');self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            events=[]
            final=worker.download_resource(self.resource,self.root,base_url=f'http://127.0.0.1:{server.server_port}',proxy=None,
                chunk_bytes=256,chunks=8,emit=events.append,sleep=lambda seconds:None)
            self.assertEqual(final.read_bytes(),data);self.assertEqual(len(set(ports)),1)
            self.assertEqual([row['num_connects'] for row in events[-1]['curl_metrics']],[1,0,0,0])
        finally:server.shutdown();server.server_close();thread.join(timeout=5)

    def test_cli_requires_slurm_before_catalog_reads_or_posix_imports(self):
        env=dict(os.environ);env.pop('SLURM_JOB_ID',None)
        result=subprocess.run([sys.executable,'-S',str(SCRIPT),'--catalog','absent.json','--report',str(self.root/'report.json')],
                              env=env,text=True,capture_output=True)
        self.assertEqual(result.returncode,2);self.assertIn('Slurm',result.stderr)
        self.assertNotIn('ModuleNotFoundError',result.stderr);self.assertFalse((self.root/'report.json').exists())


if __name__=='__main__':unittest.main()

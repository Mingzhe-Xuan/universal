"""Pure parser controls for real legacy and modern running Slurm allocations."""

import copy
import math
import os
import shlex
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.execution.slurm import running_gpu_allocation
from universal_gnn.benchmarks.execution.runner import allocation_budget

LEGACY = "JobId=991 UserId=xmz(1010) JobState=RUNNING NodeList=node42 NumNodes=1 TRES=cpu=2,mem=64G,node=1,billing=2 TresPerNode=gres:gpu:1 TimeLimit=1-00:00:00 RunTime=00:04:32"


def fields():
    return dict(item.split("=", 1) for item in shlex.split(LEGACY) if "=" in item)


class SlurmAllocationTests(unittest.TestCase):
    def test_actual_legacy991_record_and_modern_accounting(self):
        row=fields()
        self.assertEqual(running_gpu_allocation(row,job_id="991",user="xmz"),
                         dict(gpus=1,evidence="running_nodes_and_TresPerNode",node_list="node42"))
        for key in ["TRES","AllocTRES"]:
            modern={**row,key:"cpu=2,mem=64G,gres/gpu=2,gres/gpu:a100=2"}
            value=running_gpu_allocation(modern,job_id="991",user="xmz")
            self.assertEqual((value['gpus'],value['evidence']),(2,key))

    def test_typed_legacy_and_current_per_node_syntax(self):
        for value in ["gres:gpu:2","gres:gpu:rtx5090:2","gres/gpu:rtx5090:2","gres/gpu:a100=2","gres/gpu=2"]:
            with self.subTest(value=value):
                result=running_gpu_allocation({**fields(),"NumNodes":"3","NodeList":"node[42-44]","TresPerNode":value},job_id="991",user="xmz")
                self.assertEqual(result['gpus'],6)

    def test_pending_wrong_identity_owner_and_absent_nodes_fail(self):
        for key,value in [("JobId","other"),("UserId","other(1001)"),("JobState","PENDING"),
                          ("JobState","COMPLETED"),("NodeList","(null)"),("NumNodes","0")]:
            with self.subTest(key=key,value=value),self.assertRaises(RuntimeError):
                running_gpu_allocation({**fields(),key:value},job_id="991",user="xmz")

    def test_explicit_cpu_or_zero_allocation_never_uses_request_fallback(self):
        for value in ["cpu=2,mem=64G","cpu=2,gres/gpu=0","gres/gpu=-1","gres/gpu=NaN"]:
            with self.subTest(value=value),self.assertRaises(RuntimeError):
                running_gpu_allocation({**fields(),"AllocTRES":value},job_id="991",user="xmz")
        for token in ["", "gres:gpu:0", "gres:gpu:-1", "gres:gpu:a100:NaN", "gres:gpu:1.5", "gres:gpu:1junk"]:
            with self.subTest(token=token),self.assertRaises(RuntimeError):
                running_gpu_allocation({**fields(),"TresPerNode":token},job_id="991",user="xmz")

    def test_old_explicit_gpu_zero_does_not_use_per_node_fallback(self):
        with self.assertRaises(RuntimeError):
            running_gpu_allocation({**fields(),"TRES":"cpu=2,gres/gpu=0"},job_id="991",user="xmz")

    def test_remaining_budget_legacy_unlimited_and_invalid_requested_times(self):
        with patch.dict(os.environ,{"SLURM_JOB_ID":"991"}),patch("subprocess.check_output",return_value=LEGACY),patch("getpass.getuser",return_value="xmz"):
            self.assertEqual(allocation_budget(86400,1000),86128)
            with self.assertRaises(RuntimeError):allocation_budget(86400,60000)
            for value in [True,0,-1,math.nan,math.inf]:
                with self.subTest(value=value),self.assertRaises(ValueError):allocation_budget(value,1000)
        unlimited=LEGACY.replace("TimeLimit=1-00:00:00","TimeLimit=UNLIMITED")
        with patch.dict(os.environ,{"SLURM_JOB_ID":"991"}),patch("subprocess.check_output",return_value=unlimited),patch("getpass.getuser",return_value="xmz"):
            self.assertEqual(allocation_budget(3600,1000),3600)
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):allocation_budget(3600,1000)


if __name__=="__main__":unittest.main()

from pathlib import Path
import os
import subprocess
import sys
import unittest

from universal_gnn.backbones.initialization import initialize_original, validate_initialization
from universal_gnn.backbones.official import make_official


class StateValue:
    def __init__(self, shape, origin):
        self.shape, self.origin = shape, origin


class ConstructorState:
    def __init__(self):
        self.values = {"weight": StateValue((2, 3), "constructor"),
                       "running_mean": StateValue((2,), "zero"), "counter": StateValue((), "zero")}
        self.calls = []

    def state_dict(self):
        return self.values.copy()

    def load_state_dict(self, value, *, strict):
        self.calls.append((value, strict))
        self.values = value.copy()

    def reset_parameters(self):
        raise AssertionError("A partial recursive reset is not fresh construction")


class InitializationPolicyTests(unittest.TestCase):
    def reference(self):
        return {"weight": StateValue((2, 3), "pretrained"),
                "running_mean": StateValue((2,), "fitted"), "counter": StateValue((), "fitted")}

    def test_default_loads_complete_state_strictly(self):
        model, reference = ConstructorState(), self.reference()
        result = initialize_original(model, reference)
        self.assertEqual(model.calls, [(reference, True)])
        self.assertIs(model.values["weight"], reference["weight"])
        self.assertEqual(result, {"initialization":"pretrained", "state_layout_verified":True})

    def test_scratch_preserves_constructor_parameters_and_statistics_without_loading(self):
        model = ConstructorState()
        before = model.state_dict()
        result = initialize_original(model, self.reference(), mode="scratch")
        self.assertEqual(model.calls, [])
        for key,value in before.items():
            self.assertIs(model.values[key], value)
        self.assertEqual(model.values["running_mean"].origin, "zero")
        self.assertEqual(result["initialization"], "scratch")

    def test_fresh_layout_rejects_missing_extra_and_wrong_shape_including_buffers(self):
        for key,shape in (("weight",(3,2)),("running_mean",(3,)),("counter",(1,))):
            reference = self.reference()
            reference[key] = StateValue(shape,"bad")
            with self.assertRaisesRegex(ValueError,"shapes differ"):
                initialize_original(ConstructorState(),reference,mode="scratch")
        for remove in (True,False):
            reference=self.reference()
            if remove:reference.pop("counter")
            else:reference["unexpected"]=StateValue((),"bad")
            with self.assertRaisesRegex(ValueError,"keys differ"):
                initialize_original(ConstructorState(),reference,mode="scratch")

    def test_invalid_modes_fail_before_mutating_the_model(self):
        for mode in (None,False,0,[],{},"reset","warm_start"):
            model=ConstructorState()
            with self.assertRaisesRegex(ValueError,"pretrained or scratch"):
                initialize_original(model,self.reference(),mode=mode)
            self.assertEqual(model.calls,[])
        self.assertEqual(validate_initialization("scratch"),"scratch")

    def test_unsupported_provider_never_falls_back_to_pretrained_or_legacy(self):
        with self.assertRaisesRegex(ValueError,"no pretrained or legacy fallback"):
            make_official("unimplemented-test-provider",initialization="scratch")

    def test_public_policy_import_without_torch_or_site_packages(self):
        environment={**os.environ,"PYTHONPATH":str(Path(__file__).resolve().parents[1]/"src")}
        subprocess.run([sys.executable,"-S","-c",
                        "import sys; import universal_gnn.backbones as b; "
                        "from universal_gnn.backbones.initialization import validate_initialization; "
                        "assert validate_initialization('scratch') == 'scratch'; "
                        "assert set(b.__all__) <= set(dir(b)); assert 'torch' not in sys.modules"],
                       env=environment,check=True,capture_output=True)


if __name__ == "__main__":
    unittest.main()

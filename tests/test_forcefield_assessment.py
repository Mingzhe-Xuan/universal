import importlib
from types import SimpleNamespace

import pytest

from universal_gnn.contracts import FeatureSpec
from universal_gnn.engine import training


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.syspath_prepend("scripts")
    return importlib.import_module("validate_other_forcefields")


def test_candidate_capabilities_are_scoped_and_do_not_change_production(harness,monkeypatch):
    def factory(*a,**kw):
        return SimpleNamespace(gradient_capabilities={"positions":True,"strain":False,"mixed":False})
    monkeypatch.setattr(training,"make_backbone",factory)
    with pytest.raises(RuntimeError):
        with harness.candidate_capabilities():
            candidate=training.make_backbone("test")
            assert all(candidate.gradient_capabilities.values())
            assert not candidate.assessment_original_capabilities["mixed"]
            raise RuntimeError("test exception cleanup")
    assert training.make_backbone is factory and not training.make_backbone().gradient_capabilities["mixed"]


def test_assessment_configuration_keeps_force_only_and_explicit_representation(harness):
    scalar=FeatureSpec(8,"8x0e","invariant","scalar","invariant")
    vector=FeatureSpec(3,"1x1o","equivariant","e3nn/component","O3")
    for spec in (scalar,vector):
        c=harness.configuration("nequip","real.json",spec,frozen=True,epochs=4)
        assert c["task"]["supervised_outputs"]==["forces"]
        head=c["prediction"]["readout"]
        assert head["name"]=="node_mlp" and head["pooling"]=="sum"
        assert ("feature_processing" in head)==(spec is vector)
        assert not c["optimization"]["train_backbone"]

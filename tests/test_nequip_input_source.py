"""Source-only guard; actual geometry and autograd are tested in Slurm."""

import ast
from pathlib import Path
import subprocess
import unittest


class NequIPInputSourceTests(unittest.TestCase):
    def test_only_nonperiodic_shift_normalization_added_to_original_adapter(self):
        root=Path(__file__).resolve().parents[1]
        path="src/universal_gnn/backbones/official/nequip.py"
        original=ast.parse(subprocess.check_output(["git","show","72000aa:"+path],cwd=root))
        current=ast.parse((root/path).read_text(encoding="utf8"))
        helpers=[node for node in current.body if isinstance(node,ast.FunctionDef) and node.name=="_respect_nonperiodic_axes"]
        self.assertEqual(len(helpers),1)
        current.body.remove(helpers[0])
        class RemoveNormalization(ast.NodeTransformer):
            calls=0
            def visit_Call(self,node):
                node=self.generic_visit(node)
                if isinstance(node.func,ast.Name) and node.func.id=="_respect_nonperiodic_axes":
                    self.calls+=1
                    assert len(node.args)==2 and not node.keywords
                    return node.args[0]
                return node
        transform=RemoveNormalization();current=transform.visit(current)
        self.assertEqual(transform.calls,1)
        self.assertEqual(ast.dump(current,include_attributes=False),ast.dump(original,include_attributes=False))

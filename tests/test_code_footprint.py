"""Tiny committed-source fixtures only, never scientific experiment evidence."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from universal_gnn.benchmarks.code_footprint import runtime


class CodeFootprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.repository = cls.root / "repository"
        cls.repository.mkdir()
        cls.groups = {"shared": ("src/",), "plugin": ("example/",), "configuration": ("configs/demo.yaml",)}
        cls.bodies = {
            "src/a.py": b'"""doc"""\n\n# comment\nx = 1\nif x:\n    y = 2\n',
            "src/nested/b.py": b"def f():\n    return 2\n",
            "src/__init__.py": b"",
            "example/model.py": b"class Model:\n    pass\n",
            "configs/demo.yaml": b"backbone:\n  name: plugin\n",
            "docs/readme.md": b"Outside the declared inventory.\n",
        }
        for name, raw in cls.bodies.items():
            path = cls.repository / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        subprocess.run(["git", "init", "-q", str(cls.repository)], env=env, check=True)
        subprocess.run(["git", "-C", str(cls.repository), "add", "."], env=env, check=True)
        subprocess.run(["git", "-C", str(cls.repository), "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=" + str(cls.root / "no-hooks"), "commit", "-qm", "fixture"], env=env, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def collect(self, **kwargs):
        return runtime.inventory(self.repository, groups=kwargs.pop("groups", self.groups), **kwargs)

    def test_actual_git_blobs_have_declared_counts_and_exact_source_hashes(self):
        report = self.collect()
        self.assertEqual(report["totals"], dict(files=5, bytes=sum(len(raw) for name, raw in self.bodies.items() if not name.startswith("docs/")),
            physical_lines=12, nonblank_lines=11, python_statement_nodes=8))
        self.assertEqual(report["groups"]["shared"]["files"], 3)
        self.assertEqual(report["excluded_tracked_paths"], ["docs/readme.md"])
        for row in report["files"]:
            self.assertEqual(row["sha256"], hashlib.sha256(self.bodies[row["path"]]).hexdigest())
            self.assertEqual(row["bytes"], len(self.bodies[row["path"]]))

    def test_working_tree_edits_and_untracked_files_do_not_enter_commit_inventory(self):
        original = self.collect()
        path = self.repository / "src/a.py"
        untracked = self.repository / "src/untracked.py"
        try:
            path.write_bytes(b"This is deliberately invalid uncommitted Python.\n")
            untracked.write_bytes(b"raise RuntimeError('not a committed source')\n")
            self.assertEqual(self.collect(), original)
        finally:
            path.write_bytes(self.bodies["src/a.py"])
            untracked.unlink()

    def test_group_order_and_repeated_calls_preserve_rows_and_totals(self):
        left = self.collect()
        right = self.collect(groups=dict(reversed(list(self.groups.items()))))
        self.assertEqual(left, right)
        self.assertEqual(left["files"], sorted(left["files"], key=lambda row: row["path"]))
        for key in runtime.FIELDS:
            self.assertEqual(left["totals"][key], sum(group[key] for group in left["groups"].values()))

    def test_full_commit_is_accepted_but_options_branches_and_short_hashes_refuse(self):
        report = self.collect()
        self.assertEqual(self.collect(commit=report["measured_commit"]), report)
        for value in ["--help", "main", "a" * 7, "a" * 39, "HEAD~1"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.collect(commit=value)

    def test_overlapping_groups_and_duplicate_selectors_refuse(self):
        for groups in [{"all": ("src/",), "twice": ("src/a.py",)}, {"same": ("src/a.py", "src/a.py")}]:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                self.collect(groups=groups)

    def test_missing_empty_or_unsupported_boundaries_refuse(self):
        for groups in [{}, {"empty": ()}, {"missing": ("absent/",)}, {"missing": ("src/absent.py",)}, {"docs": ("docs/readme.md",)}]:
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                self.collect(groups=groups)

    def test_posix_windows_traversal_and_control_paths_refuse(self):
        for name in ["", "/etc/x.py", "../x.py", "src/../x.py", "./src/a.py", "src//a.py", "C:/x.py", "src\\a.py", ".git/config", "src/a\nb.py", "src/a\tb.py"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                runtime.safe_path(name)

    def test_symlink_and_submodule_inside_boundary_are_not_silently_excluded(self):
        for name, mode, kind in [("src/link.py", "120000", "blob"), ("src/README.md", "120000", "blob"), ("src/vendor", "160000", "commit")]:
            entries = {"src/a.py": dict(mode="100644", kind="blob", git_blob="a" * 40), name: dict(mode=mode, kind=kind, git_blob="b" * 40)}
            with self.subTest(name=name), self.assertRaises(ValueError):
                runtime.select(entries, {"source": ("src/",)})

    def test_tree_duplicate_and_bad_object_identity_refuse(self):
        record = b"100644 blob " + b"a" * 40 + b"\tsrc/a.py\x00"
        for raw in [record + record, record.replace(b"a" * 40, b"z" * 40)]:
            with self.assertRaises(ValueError):
                runtime.parse_tree(raw)

    def test_binary_batch_boundaries_and_git_object_hash_are_verified(self):
        body = b"a\n\x00b"
        oid = hashlib.sha1(b"blob 4\x00" + body).hexdigest()
        raw = (oid + " blob 4\n").encode("ascii") + body + b"\n"
        self.assertEqual(runtime.parse_blobs(raw, [oid]), {oid: body})
        for changed in [raw + b"extra", raw[:-1], raw.replace(body, b"xxxx"), raw.replace(b" blob ", b" tree ")]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                runtime.parse_blobs(changed, [oid])

    def test_utf8_bytes_comments_docstrings_and_compound_statements_have_explicit_meanings(self):
        raw = '# 注释\n"""two\nlines"""\n\nasync def f():\n    return 1\n'.encode("utf8")
        counts = runtime.count_source("a.py", raw)
        self.assertEqual(counts, dict(files=1, bytes=len(raw), physical_lines=6, nonblank_lines=5, python_statement_nodes=3))
        self.assertEqual(runtime.count_source("c.yaml", b"# comment\nx: 1\n")["python_statement_nodes"], 0)

    def test_invalid_python_or_utf8_refuse_and_empty_source_counts_zero(self):
        with self.assertRaises(SyntaxError):
            runtime.count_source("x.py", b"def :\n")
        with self.assertRaises(UnicodeDecodeError):
            runtime.count_source("x.py", b"\xff")
        self.assertEqual(runtime.count_source("x.py", b""), dict(files=1, bytes=0, physical_lines=0, nonblank_lines=0, python_statement_nodes=0))

    def test_output_is_fresh_and_all_payload_hashes_match(self):
        output = self.root / "new-output"
        with patch.object(runtime, "GROUPS", self.groups), patch.object(runtime, "provenance", return_value={"fixture": True}):
            report = runtime.write_inventory(self.repository, "HEAD", output)
            with self.assertRaises(FileExistsError):
                runtime.write_inventory(self.repository, "HEAD", output)
        saved = json.loads((output / "report.json").read_bytes())
        self.assertEqual(saved, report)
        for name, digest in json.loads((output / "output-sha256.json").read_bytes()).items():
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), digest)
        self.assertEqual(len((output / "files.tsv").read_text(encoding="utf8").splitlines()), 6)
        self.assertIn("not marginal/minimum code", (output / "summary.md").read_text(encoding="utf8"))

    def test_producer_failure_leaves_no_output(self):
        output = self.root / "failed-output"
        with patch.object(runtime, "GROUPS", self.groups), patch.object(runtime, "provenance", side_effect=ValueError("changed producer")):
            with self.assertRaises(ValueError):
                runtime.write_inventory(self.repository, "HEAD", output)
        self.assertFalse(output.exists())

    def test_public_cli_refuses_missing_slurm_before_reading_repository_or_creating_output(self):
        repository = Path(__file__).resolve().parents[1]
        output = self.root / "cli-refused"
        env = dict(os.environ, PYTHONPATH=str(repository / "src"))
        env.pop("SLURM_JOB_ID", None)
        result = subprocess.run([sys.executable, "-S", str(repository / "scripts/measure_code_footprint.py"),
            "--repository", str(self.root / "absent-repository"), "--output", str(output)], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CPU Slurm", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

"""Meaningful offline regression checks; temporary fixtures, no external writes."""
import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import release_tools as t


class ReleaseToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="extension-publisher-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "extension"
        self.root.mkdir()
        (self.root / "manifest.json").write_text(json.dumps({
            "manifest_version": 3, "name": "测试插件", "version": "1.0.0",
            "action": {"default_popup": "popup.html"},
            "background": {"service_worker": "worker.js"},
        }), encoding="utf-8")
        (self.root / "popup.html").write_text("<p>测试</p>", encoding="utf-8")
        (self.root / "worker.js").write_text("// local worker\n", encoding="utf-8")
        (self.root / "私人收藏.json").write_text('{"note":"private"}', encoding="utf-8")
        self.names = ["manifest.json", "popup.html", "worker.js"]
        self.listing = self.base / "files.json"
        self.listing.write_text(json.dumps(self.names), encoding="utf-8")
        self.out = self.base / "plugin.zip"
        self.args = argparse.Namespace(root=str(self.root), files=str(self.listing), output=str(self.out))

    def expected_tree(self):
        return {"sha": "a" * 40, "truncated": False, "tree": [
            {"path": n, "type": "blob", "mode": "100644", "sha": t.blob_sha((self.root / n).read_bytes())}
            for n in self.names
        ]}

    def tree_args(self, value):
        p = self.base / "tree.json"
        p.write_text(json.dumps(value), encoding="utf-8")
        return argparse.Namespace(root=str(self.root), files=str(self.listing), tree=str(p))

    def test_allowlist_package_preserves_source_and_excludes_private_file(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
        report, code = t.package(self.args)
        self.assertEqual(code, 0)
        self.assertTrue(report["source_unchanged"])
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(set(z.namelist()), set(self.names))
            for n in self.names:
                self.assertEqual(z.read(n), (self.root / n).read_bytes())
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()})

    def test_refuses_overwrite(self):
        self.out.write_bytes(b"keep existing")
        with self.assertRaises(t.CheckError):
            t.package(self.args)
        self.assertEqual(self.out.read_bytes(), b"keep existing")

    def test_refuses_output_inside_source(self):
        self.args.output = str(self.root / "plugin.zip")
        with self.assertRaises(t.CheckError):
            t.package(self.args)
        self.assertFalse((self.root / "plugin.zip").exists())

    def test_missing_manifest_reference_blocks_package(self):
        self.listing.write_text(json.dumps(["manifest.json", "popup.html"]))
        with self.assertRaises(t.CheckError):
            t.package(self.args)
        self.assertFalse(self.out.exists())

    def test_traversal_and_duplicate_paths_rejected(self):
        for items in (["../private.txt"], ["/tmp/private.txt"], ["manifest.json", "manifest.json"], [".git/config"]):
            with self.subTest(items=items):
                self.listing.write_text(json.dumps(items))
                with self.assertRaises(t.CheckError):
                    t.file_list(self.listing)

    def test_symlink_rejected(self):
        (self.root / "link.js").symlink_to(self.root / "worker.js")
        with self.assertRaises(t.CheckError):
            t.checked_file(self.root, "link.js")

    def test_secret_report_never_echoes_synthetic_token(self):
        synthetic = "ghp_" + "Z" * 36
        (self.root / "worker.js").write_text('const credential = "' + synthetic + '";')
        report = t.inspect(argparse.Namespace(root=str(self.root)))
        self.assertNotIn(synthetic, json.dumps(report))
        self.assertTrue(any(f["rule"] == "github_token" for f in report["findings"]))
        result, code = t.package(self.args)
        self.assertEqual(code, 2)
        self.assertFalse(result["packaged"])
        self.assertFalse(self.out.exists())

    def test_tree_exact_match(self):
        report, code = t.verify_tree(self.tree_args(self.expected_tree()))
        self.assertEqual(code, 0)
        self.assertTrue(report["verified"])

    def test_tree_missing_extra_content_and_mode_difference(self):
        tree = self.expected_tree()
        tree["tree"].pop()
        tree["tree"][0]["sha"] = "0" * 40
        tree["tree"][1]["mode"] = "120000"
        tree["tree"].append({"path": "private.json", "type": "blob", "mode": "100644", "sha": "0" * 40})
        report, code = t.verify_tree(self.tree_args(tree))
        self.assertEqual(code, 2)
        self.assertEqual(report["missing"], ["worker.js"])
        self.assertEqual(report["extra"], ["private.json"])
        self.assertEqual(report["different"], ["manifest.json"])
        self.assertEqual(report["mode_differences"], ["popup.html"])

    def test_truncated_tree_rejected(self):
        tree = self.expected_tree()
        tree["truncated"] = True
        with self.assertRaises(t.CheckError):
            t.verify_tree(self.tree_args(tree))

    def test_asset_identical_different_and_self_comparison(self):
        local, downloaded = self.base / "local.zip", self.base / "downloaded.zip"
        local.write_bytes(b"original content")
        downloaded.write_bytes(local.read_bytes())
        args = argparse.Namespace(local=str(local), downloaded=str(downloaded))
        self.assertEqual(t.verify_asset(args)[1], 0)
        downloaded.write_bytes(b"changed")
        self.assertEqual(t.verify_asset(args)[1], 2)
        args.downloaded = str(local)
        with self.assertRaises(t.CheckError):
            t.verify_asset(args)

    def test_error_exit_code_for_missing_input(self):
        with contextlib.redirect_stdout(io.StringIO()) as stream:
            code = t.main(["inspect", "--root", str(self.base / "absent")])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(stream.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()

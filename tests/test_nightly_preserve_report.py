import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "nightly.py"


def load_nightly_module():
    spec = importlib.util.spec_from_file_location("nightly_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NightlyPreserveReportTest(unittest.TestCase):
    def test_rerun_preserves_existing_non_empty_report_without_force(self):
        nightly = load_nightly_module()
        with tempfile.TemporaryDirectory() as tmp:
            nightly.REPO_ROOT = Path(tmp)
            report = nightly.nightly_report_path()
            report.parent.mkdir(parents=True)
            report.write_text("filled report\n", encoding="utf-8")

            nightly.write_report_skeleton(force=False)

            self.assertEqual(report.read_text(encoding="utf-8"), "filled report\n")

    def test_force_overwrites_existing_report(self):
        nightly = load_nightly_module()
        nightly.quota_state = lambda: {"state": "green", "remaining_pct": 100}
        nightly.repo_health = lambda: {"verdict": "green"}
        with tempfile.TemporaryDirectory() as tmp:
            nightly.REPO_ROOT = Path(tmp)
            report = nightly.nightly_report_path()
            report.parent.mkdir(parents=True)
            report.write_text("filled report\n", encoding="utf-8")

            nightly.write_report_skeleton(force=True)

            self.assertIn("# Nightly Report", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

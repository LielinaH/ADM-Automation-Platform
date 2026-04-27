from pathlib import Path
import shutil
import unittest

from adm_pipeline.run_cleanup import list_runs, prune_runs


ROOT = Path(__file__).resolve().parents[1]


class RunCleanupTests(unittest.TestCase):
    def test_prune_keeps_only_newest_runs(self) -> None:
        temp_root = ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        client_root = temp_root / "cleanup-client"
        if client_root.exists():
            shutil.rmtree(client_root, ignore_errors=True)
        client_root.mkdir(parents=True)
        try:
            created = []
            for index in range(4):
                run_dir = client_root / f"run-{index}"
                run_dir.mkdir()
                marker = run_dir / "marker.txt"
                marker.write_text(str(index), encoding="utf-8")
                created.append(run_dir)
            created[0].touch()
            created[1].touch()
            created[2].touch()
            created[3].touch()

            before = list_runs(client_root)
            self.assertEqual(len(before), 4)

            report = prune_runs(client_root, keep=2, dry_run=False)
            self.assertEqual(len(report["kept"]), 2)
            self.assertEqual(len(report["deleted"]), 2)

            after = list_runs(client_root)
            self.assertEqual(len(after), 2)
        finally:
            shutil.rmtree(client_root, ignore_errors=True)

    def test_prune_dry_run_does_not_delete(self) -> None:
        temp_root = ROOT / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        client_root = temp_root / "cleanup-dry-run"
        if client_root.exists():
            shutil.rmtree(client_root, ignore_errors=True)
        client_root.mkdir(parents=True)
        try:
            for index in range(3):
                (client_root / f"run-{index}").mkdir()
            report = prune_runs(client_root, keep=1, dry_run=True)
            self.assertEqual(len(report["kept"]), 1)
            self.assertEqual(len(report["deleted"]), 2)
            self.assertEqual(len(list_runs(client_root)), 3)
        finally:
            shutil.rmtree(client_root, ignore_errors=True)

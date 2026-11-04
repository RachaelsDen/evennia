"""Exercise mirror updates against disposable local Git repositories."""

import subprocess
import tempfile
import unittest
from pathlib import Path

from downstream.sync_upstream import sync_main


class SyncTests(unittest.TestCase):
    """Verify only fast-forward updates to the mirror are possible."""

    def setUp(self):
        """Create an upstream, fork, and maintenance checkout without network access."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream = self.root / "upstream"
        self.origin = self.root / "origin.git"
        self.checkout = self.root / "checkout"
        self.git(self.root, "init", "-b", "main", str(self.upstream))
        self.git(self.upstream, "config", "user.name", "Test")
        self.git(self.upstream, "config", "user.email", "test@example.invalid")
        self.initial = self.commit(self.upstream, "initial.txt")
        self.git(self.root, "clone", "--bare", str(self.upstream), str(self.origin))
        self.git(self.origin, "branch", "ur-dev", self.initial)
        self.git(self.root, "clone", str(self.origin), str(self.checkout))
        self.git(self.checkout, "config", "user.name", "Test")
        self.git(self.checkout, "config", "user.email", "test@example.invalid")
        self.git(self.checkout, "remote", "add", "upstream", str(self.upstream))
        self.git(self.checkout, "switch", "-c", "maintenance")

    def git(self, directory, *args):
        """Run a fixture Git command and return its output.

        Args:
            directory (Path): Repository or parent directory.
            *args (str): Git arguments.

        Returns:
            str: Stripped standard output.
        """
        return subprocess.run(
            ["git", *args], cwd=directory, check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit(self, directory, filename):
        """Commit one fixture file and return its commit ID.

        Args:
            directory (Path): Working repository.
            filename (str): Unique fixture filename.

        Returns:
            str: New commit ID.
        """
        (directory / filename).write_text(filename, encoding="utf-8")
        self.git(directory, "add", filename)
        self.git(directory, "commit", "-m", filename)
        return self.git(directory, "rev-parse", "HEAD")

    def test_no_change_is_noop(self):
        """An already synchronized mirror needs neither a push nor a PR."""
        result = sync_main(self.checkout)
        self.assertFalse(result.advanced)
        self.assertFalse(result.needs_integration_pr)

    def test_fast_forward_preserves_worktree_and_integration_branch(self):
        """New upstream commits advance main without touching local work or ur-dev."""
        latest = self.commit(self.upstream, "upstream.txt")
        local = self.commit(self.checkout, "local.txt")
        result = sync_main(self.checkout)
        self.assertTrue(result.advanced)
        self.assertTrue(result.needs_integration_pr)
        self.assertEqual(self.git(self.origin, "rev-parse", "main"), latest)
        self.assertEqual(self.git(self.origin, "rev-parse", "ur-dev"), self.initial)
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD"), local)
        self.assertEqual(self.git(self.checkout, "branch", "--show-current"), "maintenance")

    def test_existing_unintegrated_update_still_requests_pr(self):
        """A previous mirror update must not hide a still-needed integration PR."""
        latest = self.commit(self.upstream, "upstream.txt")
        self.git(self.origin, "fetch", str(self.upstream), "main")
        self.git(self.origin, "update-ref", "refs/heads/main", latest)
        result = sync_main(self.checkout)
        self.assertFalse(result.advanced)
        self.assertTrue(result.needs_integration_pr)

    def test_local_patch_on_main_is_rejected(self):
        """A fork-only commit is never overwritten, even if upstream has not moved."""
        custom = self.commit(self.checkout, "accidental-main.txt")
        self.git(self.checkout, "push", "origin", f"{custom}:refs/heads/main")
        with self.assertRaisesRegex(RuntimeError, "not a fast-forward"):
            sync_main(self.checkout)
        self.assertEqual(self.git(self.origin, "rev-parse", "main"), custom)

    def test_diverged_main_is_rejected(self):
        """Concurrent upstream and fork-only commits require human investigation."""
        custom = self.commit(self.checkout, "accidental-main.txt")
        self.git(self.checkout, "push", "origin", f"{custom}:refs/heads/main")
        self.commit(self.upstream, "upstream.txt")
        with self.assertRaisesRegex(RuntimeError, "not a fast-forward"):
            sync_main(self.checkout)
        self.assertEqual(self.git(self.origin, "rev-parse", "main"), custom)

    def test_already_integrated_upstream_does_not_request_pr(self):
        """A patched branch already containing upstream needs no redundant PR."""
        self.git(self.checkout, "switch", "-c", "ur-dev", "origin/ur-dev")
        self.commit(self.checkout, "patch.txt")
        self.commit(self.upstream, "upstream.txt")
        self.git(self.checkout, "fetch", "upstream", "main")
        self.git(self.checkout, "merge", "--no-edit", "upstream/main")
        self.git(self.checkout, "push", "origin", "ur-dev")
        integrated = self.git(self.origin, "rev-parse", "ur-dev")
        result = sync_main(self.checkout)
        self.assertTrue(result.advanced)
        self.assertFalse(result.needs_integration_pr)
        self.assertEqual(self.git(self.origin, "rev-parse", "ur-dev"), integrated)

    def test_upstream_history_rewrite_is_rejected(self):
        """An unrelated upstream history must never replace the mirror."""
        self.git(self.upstream, "switch", "--orphan", "rewritten")
        rewritten = self.commit(self.upstream, "rewritten.txt")
        self.git(self.upstream, "update-ref", "refs/heads/main", rewritten)
        with self.assertRaisesRegex(RuntimeError, "not a fast-forward"):
            sync_main(self.checkout)
        self.assertEqual(self.git(self.origin, "rev-parse", "main"), self.initial)

    def test_rejected_push_is_not_retried_with_force(self):
        """A remote rejection propagates rather than triggering a force retry."""
        self.commit(self.upstream, "upstream.txt")
        hook = self.origin / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        with self.assertRaises(subprocess.CalledProcessError):
            sync_main(self.checkout)
        self.assertEqual(self.git(self.origin, "rev-parse", "main"), self.initial)


if __name__ == "__main__":
    unittest.main()

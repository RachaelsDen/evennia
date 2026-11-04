"""Keep the engine's declared minimums above the audited security floor."""

import tomllib
import unittest
from pathlib import Path


class DependencyPolicyTests(unittest.TestCase):
    """Prevent future upstream merges from restoring vulnerable constraints."""

    def test_security_minimums(self):
        """The three affected packages must permit and require patched releases."""
        with (Path(__file__).resolve().parents[2] / "pyproject.toml").open("rb") as stream:
            requirements = tomllib.load(stream)["project"]["dependencies"]
        normalized = {requirement.replace(" ", "").lower() for requirement in requirements}
        for requirement in (
            "django>=6.0.10,<6.1",
            "twisted>=26.10.0,<27",
            "autobahn>=26.11.1,<27",
            "djangorestframework>=3.18.3,<3.19",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, normalized)

    def test_security_audit_covers_locked_extras(self):
        """Maintenance CI must audit the locked optional dependencies without ignores."""
        root = Path(__file__).resolve().parents[2]
        workflow = (root / ".github/workflows/ur-maintenance.yml").read_text()
        self.assertIn("uv export --locked --all-extras", workflow)
        self.assertIn("pip-audit==2.10.1", workflow)
        self.assertNotIn("--ignore-vuln", workflow)


if __name__ == "__main__":
    unittest.main()

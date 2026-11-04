"""Fast-forward the clean upstream mirror without merging downstream patches."""

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyncResult:
    """Describe a mirror update and whether integration review is needed."""

    upstream_sha: str
    advanced: bool
    needs_integration_pr: bool


def git(repo, *args):
    """Run Git and return stripped standard output.

    Args:
        repo (Path): Working checkout.
        *args (str): Git arguments.

    Returns:
        str: Command output.

    Raises:
        subprocess.CalledProcessError: Git rejected the operation.
    """
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def is_ancestor(repo, ancestor, descendant):
    """Check ancestry without treating operational Git errors as divergence.

    Args:
        repo (Path): Working checkout.
        ancestor (str): Possible ancestor commit ID.
        descendant (str): Possible descendant commit ID.

    Returns:
        bool: Whether the first commit is an ancestor of the second.

    Raises:
        subprocess.CalledProcessError: Git could not perform the check.
    """
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        result.check_returncode()
    return result.returncode == 0


def sync_main(repo):
    """Mirror upstream/main with a non-force push, leaving ur-dev unchanged.

    Args:
        repo (Path): Checkout with origin and upstream remotes configured.

    Returns:
        SyncResult: Updated upstream revision and integration-review requirement.

    Raises:
        RuntimeError: Mirror has fork-only history or upstream rewrote history.
        subprocess.CalledProcessError: Fetch or push failed; no force retry occurs.
    """
    git(
        repo,
        "fetch",
        "--no-tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        "+refs/heads/ur-dev:refs/remotes/origin/ur-dev",
    )
    git(repo, "fetch", "--no-tags", "upstream", "+refs/heads/main:refs/remotes/upstream/main")
    mirror = git(repo, "rev-parse", "refs/remotes/origin/main^{commit}")
    upstream = git(repo, "rev-parse", "refs/remotes/upstream/main^{commit}")
    integration = git(repo, "rev-parse", "refs/remotes/origin/ur-dev^{commit}")
    if not is_ancestor(repo, mirror, upstream):
        raise RuntimeError(
            "Mirror update is not a fast-forward. Investigate main divergence or an "
            "upstream history rewrite; refusing to merge, reset, or force-push."
        )
    advanced = mirror != upstream
    if advanced:
        git(repo, "push", "origin", f"{upstream}:refs/heads/main")
    return SyncResult(upstream, advanced, not is_ancestor(repo, upstream, integration))


def main():
    """Synchronize the mirror and publish machine-readable workflow outputs."""
    result = sync_main(Path.cwd())
    values = asdict(result)
    print(json.dumps(values))
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={str(value).lower()}\n")


if __name__ == "__main__":
    main()

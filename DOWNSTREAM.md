# Unified Realms downstream maintenance

Public fork: https://github.com/RachaelsDen/evennia

## Branch contract

- **main** is an exact mirror of `evennia/evennia:main`. No custom commits, merge
  commits, PR merges, rebases, or force pushes. Advance only by fast-forward.
- **ur-dev** is the reviewed downstream integration branch and the fork's default
  branch. It contains upstream plus our minimal maintenance patches.
- **feature/** and **fix/** branches propose changes by PR into **ur-dev**, never
  into main. Do not use the game repository's dev-to-main promotion convention in
  this engine fork: main is exclusively an upstream mirror.
- Do not use GitHub's generic Sync fork button against default ur-dev; the
  maintenance workflow explicitly targets mirror main and proposes integration.
- Game-specific rules, UI, and authentication integrations belong in the private
  game repository where extension hooks suffice. Keep this public fork generic;
  never copy private game data, network details, or credentials into it.

The BSD license and upstream notices remain unchanged. Prefer contributing generic
fixes upstream so our patch set can shrink over time.

## Synchronization

`ur-sync-upstream.yml` runs daily at 06:23 UTC and can be dispatched manually.
GitHub schedules run from the default branch, hence the default **ur-dev** rather
than main. The workflow becomes available only after its PR is reviewed and merged
into ur-dev and Actions is enabled for the fork.

The job fetches the official upstream, checks that origin/main is its ancestor,
and pushes the exact upstream commit without force. It never checks out, commits
to, or merges into main. Divergence or upstream history rewrites fail the run for
maintainer investigation; there is no automatic reset or repair.

When upstream commits are missing from ur-dev, it opens one draft **main -> ur-dev**
PR (or leaves the existing PR to track new mirror commits). It never auto-merges.
Repository Actions permissions must allow GitHub Actions to create pull requests;
if policy blocks that, mirror updates can still succeed while PR creation fails.
Use workflow failure notifications and create the integration PR manually.
Bot-created PR checks may require maintainer approval. Public scheduled workflows
can also be disabled after 60 days of inactivity; check/enable the workflow when
resuming maintenance. Mirror scheduling is not a production security-update SLA.

## Local commands

```sh
git remote add upstream https://github.com/evennia/evennia.git
uv run --no-project python -m unittest discover -s downstream/tests -v
uv run --no-project python -m downstream.sync_upstream
```

The last command **writes origin/main** when it is safely behind upstream. It does
not open a PR locally. Use it only with the intended fork's origin remote.
Tests use temporary local repositories and never contact GitHub.

## Acceptance and game pinning

Upstream engine CI is also enabled for PRs targeting ur-dev. Before adopting a
downstream revision, require upstream tests, the private game's PostgreSQL/browser/
native-client integration checks, and a dependency security audit. A merged
maintenance PR is not proof the engine is production-safe.

Pin games to a reviewed **full commit ID**, not a floating main/ur-dev branch. Game
lockfiles and Docker builds change only through a separate reviewed update. The
initial game still uses published Evennia 6.1.0; creating this fork does not resolve
its documented dependency advisories or switch the running game.

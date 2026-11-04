# Downstream dependency security

## 2026-11-04 update

The published Evennia 6.1.0 dependency set audited with 16 advisory entries across
Autobahn 20.12.3, Django REST framework 3.16.1, and Twisted 24.11.0. The downstream
now requires these patched stable releases or later within the tested series:

| Package | New minimum | Upper bound |
| --- | --- | --- |
| Twisted | 26.10.0 | <27 |
| Autobahn | 26.11.1 | <27 |
| Django REST framework | 3.18.3 | <3.19 |
| Django | 6.0.10 | <6.1 |

Django remains on its existing 6.0 series to avoid combining an unrelated feature
migration with the security update. `uv.lock` is refreshed, including optional
dependencies, and records exact tested versions. No prereleases are selected.

Local `pip-audit==2.10.1` against Python 3.14.8 with all optional features installed
reported **zero known advisories across 152 installed distributions**. This includes
the earlier Twisted IMAP advisory that reported no fixed version against the old
release; the selected new release is not flagged by the current advisory data.
No advisory IDs are ignored or suppressed.

The maintenance CI exports the locked dependency set including extras and audits
it on Python 3.14.8. Any reported advisory fails the check. The engine suite still
runs separately on PostgreSQL 18.4. A clean audit is not proof of compatibility or
of application security; the engine and consuming game's integration tests must
pass before adoption. Browser assets are not covered by the Python package audit.

# Security Policy

## Supported versions

Security fixes are applied to the latest released version.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Report it privately to the maintainers
through the repository's security advisory channel with reproduction steps, impact, and any safe
mitigation you identified. We will acknowledge reports within five business days and coordinate
disclosure after a fix is available.

## Local data handling

This package is local-first: credentials belong only in ignored `.env` files, source databases are
never uploaded by the package, and generated outputs must not be committed. Report any suspected
credential exposure or read-only policy bypass as a security issue.

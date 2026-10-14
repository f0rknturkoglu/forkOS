# Security Policy

## Scope & Philosophy

forkOS is a **single-user, local-first personal operating system**. By design:

- All services (FastAPI, React web UI, PostgreSQL, worker) bind strictly to `127.0.0.1` (loopback).
- There is no public internet-facing authentication, remote tenant layer, or cloud data synchronization.
- Sensitive files (`.env`, `*.user`, `*.db`, personal Obsidian vaults) are git-ignored and remain on your local disk.

---

## Supported Versions

Only the latest commit on the `main` branch is actively maintained.

| Version | Supported          |
| ------- | ------------------ |
| v1.x / `main` | :white_check_mark: |
| < v1.0  | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability (such as unintended external network exposure, unsafe file access, or injection risks in local parsing):

1. **Do not open a public issue.**
2. Report the vulnerability privately via **[GitHub Private Vulnerability Reporting](https://github.com/f0rknturkoglu/forkOS/security/advisories/new)**.
3. If private vulnerability reporting is unavailable, reach out directly to the maintainer via GitHub profile contact.

Please include:
- A description of the issue and potential impact.
- Steps to reproduce or proof of concept.
- Proposed remediation or fix if available.

We appreciate responsible disclosure and will investigate and address reported issues promptly.

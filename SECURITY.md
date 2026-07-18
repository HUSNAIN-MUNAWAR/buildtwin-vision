# Security Policy

## Supported Versions

The public repository tracks the latest `main` branch. Security fixes should target `main` unless a maintained release branch is introduced.

## Reporting a Vulnerability

Please use GitHub Security Advisories for responsible disclosure when available. If advisories are unavailable, open a minimal public issue that says a vulnerability report is available and avoid posting exploit details, secrets, tokens, or private data.

## Current Security Scope

Implemented local/demo controls include:

- PBKDF2-SHA256 salted password hashes.
- Signed expiring JWT access tokens.
- Organization-scoped data access.
- Role-gated mutation endpoints.
- Upload extension and size validation.
- Generated safe filenames and fixed media roots.
- CORS allowlisting for local development.
- Common security headers.
- Audit logging for sensitive workflow changes.

## Production Hardening Notes

Before using this system beyond a local/demo environment, add managed secrets, HTTPS, identity-provider integration or refresh-token rotation, rate limiting, malware scanning for uploads, database least privilege, object storage with signed URLs, dependency/container scanning, backups, centralized logs, and formal authorization tests.

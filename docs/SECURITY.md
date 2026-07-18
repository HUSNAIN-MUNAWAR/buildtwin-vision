# Security

Implemented controls include PBKDF2-SHA256 salted password hashes, signed expiring JWTs, organization-scoped access, role-gated mutations, validated upload extensions/sizes, generated safe filenames, fixed media roots, CORS allowlisting, common security headers, input schemas, audit logging, and environment-only secrets.

Before public deployment: use a managed secret store, HTTPS, refresh-token rotation or an identity provider, CSRF strategy if cookie sessions are introduced, antivirus/content scanning, database least privilege, S3 presigned URLs, rate limiting, dependency/container scanning, backup/restore drills, centralized logs, and formal authorization tests for every new endpoint.

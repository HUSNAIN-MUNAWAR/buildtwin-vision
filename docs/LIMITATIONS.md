# Honest limitations

- The lightweight IFC STEP adapter extracts supported records but not full geometry/property graphs. Use IfcOpenShell for production BIM semantics.
- Camera-to-BIM registration is manual; there is no photogrammetry, SLAM, LiDAR, or point-cloud reconstruction.
- Visual progress is based on deterministic change/occupancy evidence, not a trained enterprise construction model.
- PPE and equipment classes are not claimed because no specialist model is bundled.
- Quality results are candidates and require qualified inspection.
- Schedule analysis is a longest-path approximation, not complete Primavera/MS Project CPM behavior.
- Local jobs are synchronous. Redis is included as an infrastructure adapter, but a queue worker is not falsely claimed as operated.
- SQLite is for demo use. Production needs PostgreSQL, object storage, backups, monitoring, rate limiting, SSO, and security hardening.
- Synthetic media demonstrates the actual pipeline but does not establish field accuracy.

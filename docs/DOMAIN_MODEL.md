# Domain model

BuildTwin separates source evidence, automated interpretation, and human-approved project state.

- **Organization boundary:** every owned record carries `organization_id`; route helpers reject cross-organization IDs with a not-found response.
- **Project hierarchy:** project → building → floor → zone. Zones contain validated polygons and restricted/staleness configuration.
- **BIM:** an import record preserves source status/report; each supported IFC entity retains GlobalId, class, name, approximate metadata, zone, progress state, and confidence.
- **Schedule:** activity records hold baseline dates, planned progress, AI progress, approved progress, status, criticality, contractor, and risk. Dependencies are relational edges, not JSON.
- **Evidence:** media assets preserve path, source type, capture time, camera/zone links, and whether the asset is synthetic.
- **Observation:** AI progress remains an observation with algorithm/version/confidence/evidence/review state. It never silently overwrites approved progress.
- **Events:** safety and quality records are operational exceptions with severity, evidence, state, assignment/corrective action, and notes.
- **Governance:** every material mutation produces an append-only audit event with actor, entity, before/after values, and correlation ID.

Trace path:

`dashboard KPI → activity → approved/AI progress → observation → media asset → algorithm output → reviewer action → audit event`

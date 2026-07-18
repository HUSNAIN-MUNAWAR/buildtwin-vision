# Architecture

## System context

```mermaid
flowchart LR
  PM[Project manager] --> WEB[Next.js operations console]
  SE[Site engineer] --> WEB
  RV[Reviewer] --> WEB
  CAM[Fixed camera / drone upload] --> API[FastAPI]
  IFC[IFC model] --> API
  SCH[CSV / JSON schedule] --> API
  WEB --> API
  API --> DB[(PostgreSQL / SQLite)]
  API --> MEDIA[(Evidence storage)]
  API --> REDIS[(Redis adapter)]
  API --> PDF[PDF reports]
```

## Container architecture

```mermaid
flowchart TB
  B[Browser] --> W[Next.js web]
  W --> A[FastAPI API]
  A --> P[(PostgreSQL)]
  A --> R[(Redis)]
  A --> S[(Mounted media / future object store)]
  A --> J[Job interface: synchronous local / queued production]
```

## Backend modules

```mermaid
flowchart LR
  Routes[API routes] --> Auth[Auth + RBAC]
  Routes --> Services[Domain services]
  Services --> Repos[SQLAlchemy session/repositories]
  Services --> Vision[Vision package]
  Services --> BIM[BIM parser]
  Services --> Schedule[Schedule graph]
  Services --> Risk[Risk model]
  Services --> Reports[Report generator]
  Repos --> DB[(Database)]
```

## Media-processing pipeline

```mermaid
sequenceDiagram
  participant U as User
  participant API as Capture API
  participant JOB as Processing job
  participant CV as OpenCV pipeline
  participant DB as Database
  participant FS as Evidence storage
  U->>API: Upload image/MP4
  API->>FS: Validate and persist source
  API->>DB: Create media asset
  U->>JOB: Run processing
  JOB->>CV: Stream/decode/sample frames
  CV->>FS: Save annotated evidence
  JOB->>DB: Persist metrics/output/status
  JOB-->>U: Completed or explicit failure
```

## IFC-ingestion pipeline

```mermaid
flowchart LR
  Upload --> Validate[Extension + STEP header]
  Validate --> Parse[Parse supported IFC entities]
  Parse --> Preserve[Preserve GlobalId, class, name]
  Preserve --> Persist[Persist BIM elements]
  Parse --> Failures[Collect per-record failures]
  Persist --> Report[Ingestion report + audit event]
  Failures --> Report
```

## 4D progress calculation

```mermaid
flowchart LR
  Date[Current date] --> Planned[Planned progress]
  Schedule[Activity schedule] --> Planned
  AI[AI estimate + confidence] --> Analytical[Analytical progress]
  Review[Human approval] --> Approved[Approved actual progress]
  Planned --> Variance[Schedule variance]
  Approved --> Variance
  Variance --> Risk[Explainable risk]
  Evidence[Evidence freshness] --> Risk
  Dependencies[Delayed predecessors] --> Risk
```

## Safety-event lifecycle

```mermaid
stateDiagram-v2
  [*] --> Candidate
  Candidate --> Open: rule threshold met
  Open --> Open: duplicate frame updates last_seen
  Open --> Assigned
  Assigned --> Resolved
  Open --> Duplicate
  Resolved --> [*]
```

## Human-review workflow

```mermaid
flowchart LR
  Obs[Automated observation] --> Queue[Review queue]
  Queue --> Approve
  Queue --> Reject
  Queue --> Modify[Modify progress]
  Approve --> Effective[Approved activity progress]
  Modify --> Effective
  Reject --> Preserve[Preserve previous approved value]
  Effective --> Audit[Audit event]
  Preserve --> Audit
```

## Schedule dependency graph

```mermaid
flowchart LR
  A100[Foundations] --> A110[Ground slab]
  A110 --> A120[Core columns]
  A120 --> A130[Core beams]
  A120 --> A140[Patient-room masonry]
  A130 --> A150[Roof mechanical curbs]
```

## Deployment

```mermaid
flowchart TB
  Internet --> Proxy[Nginx / TLS proxy]
  Proxy --> Web[Next.js container]
  Proxy --> API[FastAPI container]
  API --> PG[(Managed PostgreSQL)]
  API --> Redis[(Managed Redis)]
  API --> Object[(S3-compatible object storage)]
  Worker[Queue worker] --> PG
  Worker --> Redis
  Worker --> Object
```

## Entity overview

```mermaid
erDiagram
  ORGANIZATION ||--o{ USER : has
  ORGANIZATION ||--o{ PROJECT : owns
  PROJECT ||--o{ ZONE : contains
  PROJECT ||--o{ BIM_MODEL : imports
  BIM_MODEL ||--o{ BIM_ELEMENT : contains
  PROJECT ||--o{ ACTIVITY : schedules
  ACTIVITY ||--o{ DEPENDENCY : successor
  ACTIVITY ||--o{ PROGRESS_OBSERVATION : receives
  MEDIA_ASSET ||--o{ PROGRESS_OBSERVATION : evidences
  PROJECT ||--o{ SAFETY_EVENT : records
  PROJECT ||--o{ QUALITY_OBSERVATION : records
  ACTIVITY ||--o{ RISK_ASSESSMENT : assessed
  PROJECT ||--o{ AUDIT_EVENT : traces
```

## Capture-to-approved-progress sequence

```mermaid
sequenceDiagram
  participant E as Site engineer
  participant API as API
  participant CV as Vision pipeline
  participant R as Reviewer
  participant DB as Database
  E->>API: Upload capture
  API->>DB: Persist immutable media source
  E->>API: Run processing
  API->>CV: Decode and assess evidence
  CV->>DB: Store AI observation separately
  R->>API: Approve / reject / modify
  API->>DB: Update approved progress if accepted
  API->>DB: Append audit event
  API-->>R: Effective progress response
```

## Important decision

Local development executes jobs synchronously through the same persisted `ProcessingJob` contract. Production can replace the executor with Celery, Dramatiq, or RQ without changing observation, audit, or UI contracts.

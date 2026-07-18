# Schedule engine

Imports accept CSV or JSON with activity ID, name, planned dates/progress, actual progress, and predecessor IDs. Validation rejects duplicate IDs, invalid/missing dates, finish-before-start, progress outside 0–100, missing predecessors, and cycles.

NetworkX builds a directed acyclic graph. The demo exposes dependency nodes/edges and a duration-weighted longest-path approximation. It is suitable for a portfolio demonstration, not a substitute for full CPM logic with calendars, constraints, relationship types, float, and resource leveling.

Progress variance is `approved actual progress − planned progress`. Negative values indicate the accepted field state trails the schedule baseline.

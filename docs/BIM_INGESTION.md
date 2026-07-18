# BIM ingestion

The initial adapter performs real parsing of IFC STEP text rather than displaying a filename. It validates the `.ifc` extension and ISO-10303-21 header, parses supported entity records, preserves GlobalId/class/name, records unsupported or malformed rows, persists successful elements, and emits an import report/audit event.

Supported demo classes: IfcWall, IfcSlab, IfcColumn, IfcBeam, IfcDoor, IfcWindow, IfcRoof, IfcStair, IfcRailing, IfcBuildingStorey, and IfcSpace.

The parser intentionally does not claim geometric fidelity. Production geometry, placements, property sets, materials, and computed bounding boxes should use the `IfcOpenShell` adapter behind the same ingestion service. The generated `sample_data/ifc/northstar_minimal.ifc` is synthetic and redistributable with this repository.

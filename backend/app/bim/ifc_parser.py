from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TYPE_NAMES = {"IFCWALL":"IfcWall","IFCSLAB":"IfcSlab","IFCCOLUMN":"IfcColumn","IFCBEAM":"IfcBeam","IFCDOOR":"IfcDoor","IFCWINDOW":"IfcWindow","IFCROOF":"IfcRoof","IFCSTAIR":"IfcStair","IFCRAILING":"IfcRailing","IFCBUILDINGSTOREY":"IfcBuildingStorey","IFCSPACE":"IfcSpace"}
SUPPORTED = set(TYPE_NAMES)
ENTITY_RE = re.compile(r"#(?P<id>\d+)\s*=\s*(?P<type>IFC[A-Z0-9_]+)\s*\((?P<body>.*)\)\s*;", re.I)
STRING_RE = re.compile(r"'((?:[^']|'')*)'")

@dataclass
class ParsedElement:
    source_id: str
    ifc_guid: str
    element_type: str
    name: str


def parse_ifc(path: str) -> tuple[list[ParsedElement], list[str]]:
    p = Path(path)
    if p.suffix.lower() != ".ifc":
        raise ValueError("Only .ifc files are supported")
    text = p.read_text(encoding="utf-8", errors="replace")
    if "ISO-10303-21" not in text[:500]:
        raise ValueError("File does not contain an IFC STEP header")
    elements: list[ParsedElement] = []; failures: list[str] = []
    for raw in text.splitlines():
        match = ENTITY_RE.search(raw.strip())
        if not match: continue
        entity_type = match.group("type").upper()
        if entity_type not in SUPPORTED: continue
        strings = STRING_RE.findall(match.group("body"))
        guid = strings[0] if strings else f"STEP-{match.group('id')}"
        name = strings[2] if len(strings) > 2 and strings[2] else (strings[1] if len(strings)>1 else f"{entity_type}-{match.group('id')}")
        if len(guid) < 5:
            failures.append(f"#{match.group('id')} invalid GlobalId")
            continue
        elements.append(ParsedElement(match.group("id"), guid, TYPE_NAMES[entity_type], name))
    if not elements:
        raise ValueError("No supported IFC building elements were found")
    return elements, failures

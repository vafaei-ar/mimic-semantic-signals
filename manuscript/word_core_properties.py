"""Set accurate, source-grounded Word title/creator without changing edit history.

Only the two factual `docProps/core.xml` fields are modified. The original
revision number, application, creator history, and timestamps are untouched.
"""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DC = "http://purl.org/dc/elements/1.1/"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DCTERMS = "http://purl.org/dc/terms/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ET.register_namespace("dc", DC)
ET.register_namespace("cp", CP)
ET.register_namespace("dcterms", DCTERMS)
ET.register_namespace("xsi", XSI)

def set_title_creator(path: Path, title: str, creator: str) -> dict:
    """Patch supported, verified metadata fields. Preserve other ZIP members."""
    if not title.strip() or not creator.strip():
        raise ValueError("The title and creator must be source-grounded")
    with zipfile.ZipFile(path, "r") as z:
        entries = [(info, z.read(info.filename)) for info in z.infolist()]
    hits = [(i, payload) for i, (info, payload) in enumerate(entries)
            if info.filename == "docProps/core.xml"]
    if len(hits) != 1:
        raise ValueError("Expected exactly one Office core-properties part")
    ix, payload = hits[0]
    root = ET.fromstring(payload)
    for key, value in (("title", title.strip()), ("creator", creator.strip())):
        name = "{" + DC + "}" + key
        node = root.find(name)
        if node is None:
            node = ET.SubElement(root, name)
        node.text = value
    revised = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    ET.fromstring(revised)
    temp = path.with_suffix(".coreprops.tmp")
    with zipfile.ZipFile(temp, "w") as z:
        for i, (info, original) in enumerate(entries):
            z.writestr(info, revised if i == ix else original)
    with zipfile.ZipFile(temp) as z:
        if z.testzip() is not None:
            raise ValueError("Invalid ZIP after core property edit")
        verified = ET.fromstring(z.read("docProps/core.xml"))
        got_title = verified.find("{" + DC + "}title")
        got_creator = verified.find("{" + DC + "}creator")
        if got_title is None or got_title.text != title or got_creator is None or got_creator.text != creator:
            raise ValueError("Metadata verification failed")
    temp.replace(path)
    return {"title": title, "creator": creator, "revision_and_editor_history_preserved": True}

def inspect_title_creator(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("docProps/core.xml"))
    def get(key):
        node = root.find("{" + DC + "}" + key)
        return node.text if node is not None else None
    return {"title": get("title"), "creator": get("creator")}

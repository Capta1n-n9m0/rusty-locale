"""Generate rusty-locale/type-hierarchy.lua from the game's machine-readable prototype docs.

The input is doc-html/prototype-api.json in the Factorio install (also at
https://lua-api.factorio.com/latest/prototype-api.json). A type missing from the tree is skipped by
`prototypes.find()`, so regenerate the tree whenever the game adds prototype types.

Mapping, so the names the library relies on keep their meaning:
- `PrototypeBase` and `Prototype` (both carry localised_name) -> 'prototype-base'; `locale.localised_types`
  is built from its descendants.
- Types without a parent in the docs (font, sprite, sound, ...) become roots outside 'prototype-base'.
- Abstract classes are kept as nodes under their kebab-case name (entity-with-owner, active-trigger, ...).

usage: python generate_type_hierarchy.py <prototype-api.json> <rusty-locale/type-hierarchy.lua>
"""
import json, re, sys

api = json.load(open(sys.argv[1], encoding="utf-8"))
by_class = {p["name"]: p for p in api["prototypes"]}


def tname(cls):
    if cls in ("PrototypeBase", "Prototype"):
        return "prototype-base"
    p = by_class[cls]
    if p.get("typename"):
        return p["typename"]
    s = cls[:-len("Prototype")] if cls.endswith("Prototype") else cls
    return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()


top_down = {}
for p in api["prototypes"]:
    cls, parent = p["name"], p.get("parent")
    if cls in ("PrototypeBase", "Prototype"):
        continue
    if not parent:
        top_down.setdefault(tname(cls), None)  # root
    else:
        top_down[tname(cls)] = tname(parent)

children = {}
for t, parent in top_down.items():
    children.setdefault(parent, []).append(t)
roots = sorted(children.get(None, [])) + ["prototype-base"]


def key(t):
    return t if re.fullmatch(r"[A-Za-z_]\w*", t) else f"['{t}']"


out = [f"-- Generated from prototype-api.json of Factorio {api['application_version']} "
       f"by tools/generate_type_hierarchy.py", "return {", "\ttop_down = {"]
for t in sorted(t for t, p in top_down.items() if p is not None):
    out.append(f"\t\t{key(t)} = '{top_down[t]}',")
out += ["\t},", "\tbottom_up = {"]


def emit(t, depth):
    kids = sorted(children.get(t, []))
    ind = "\t" * depth
    if not kids:
        out.append(f"{ind}{key(t)} = {{}},")
        return
    out.append(f"{ind}{key(t)} = {{")
    for k in kids:
        emit(k, depth + 1)
    out.append(f"{ind}}},")


for r in roots:
    emit(r, 2)
out += ["\t},", "}", ""]
with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(out))
print(f"{len(top_down)} types, {len(roots)} roots")

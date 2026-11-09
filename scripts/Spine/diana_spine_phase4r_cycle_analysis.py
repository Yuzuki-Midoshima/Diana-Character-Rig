# -*- coding: utf-8 -*-
"""Read-only DG/DAG audit for Diana Spine Phase 4-R.

Run inside Maya with the rolled-back validation scene open.  The script does
not create, delete, connect, parent, or edit scene nodes.
"""
from __future__ import absolute_import, division, print_function

import datetime
import json
import os
from collections import defaultdict, deque

import maya.cmds as cmds
import maya.api.OpenMaya as om

HERE = os.path.dirname(__file__)
OUTPUT = os.path.join(HERE, "Character_spine37_phase4r_cycle_analysis.json")

PARTS = {
    "HIP": "hip_fk_Spine_anim_jnt",
    "LOWER": "lower_fk_Spine_anim",
    "MIDDLE": "middle_fk_Spine_anim",
    "SHOULDER": "shoulder_fk_Spine_anim_jnt",
}

FOCUS = (
    "DIANA_SPINE_INDEPENDENT_IK_CURVE",
    "DIANA_SPINE_LOWER_LIVE_DRIVER",
    "DIANA_SPINE_MIDDLE_LIVE_DRIVER",
    "DIANA_SPINE_SHOULDER_LIVE_DRIVER",
    "back_spine_curve",
    "RIG_spineStretch_MD",
)


def _node(plug):
    return plug.split(".", 1)[0]


def _canonical(name):
    """Normalize short/long DAG names and leave unique DG names intact."""
    found = cmds.ls(name, long=True) or cmds.ls(name) or []
    if not found:
        return name
    exact = [x for x in found if x == name]
    return exact[0] if exact else sorted(found, key=len)[0]


def _canonical_plug(plug):
    if "." not in plug:
        return _canonical(plug)
    n, attr = plug.split(".", 1)
    return _canonical(n) + "." + attr


def _all_edges():
    """Return source->destination plug edges plus explicit DAG dependencies."""
    edges = []
    seen = set()
    for dst in cmds.ls(dependencyNodes=True) or []:
        raw = cmds.listConnections(dst, source=True, destination=False,
                                   connections=True, plugs=True,
                                   skipConversionNodes=False) or []
        # With source=True Maya returns destination,source pairs.
        for i in range(0, len(raw) - 1, 2):
            a, b = raw[i], raw[i + 1]
            if cmds.connectionInfo(a, isDestination=True):
                dest, source = a, b
            elif cmds.connectionInfo(b, isDestination=True):
                dest, source = b, a
            else:
                continue
            item = (_canonical_plug(source), _canonical_plug(dest), "DG")
            if item not in seen:
                seen.add(item)
                edges.append(item)
    for child in cmds.ls(dag=True, long=True) or []:
        parents = cmds.listRelatives(child, parent=True, fullPath=True) or []
        if parents:
            # A child's inclusive/world matrix depends on its parent's world.
            item = (parents[0] + ".worldMatrix[0]",
                    child + ".parentMatrix[0]", "DAG_PARENT")
            if item not in seen:
                seen.add(item)
                edges.append(item)
    return edges


def _node_graph(edges):
    graph = defaultdict(list)
    for source, dest, kind in edges:
        graph[_node(source)].append((_node(dest), source, dest, kind))
    return graph


def _shortest_path(graph, starts, goals, max_visits=250000):
    starts = {_canonical(x) for x in starts if cmds.objExists(x)}
    goals = {_canonical(x) for x in goals if cmds.objExists(x)}
    queue = deque(starts)
    previous = {x: None for x in starts}
    via = {}
    visits = 0
    hit = None
    while queue and visits < max_visits:
        current = queue.popleft()
        visits += 1
        if current in goals:
            hit = current
            break
        for nxt, source, dest, kind in graph.get(current, []):
            if nxt not in previous:
                previous[nxt] = current
                via[nxt] = {"source": source, "destination": dest, "kind": kind}
                queue.append(nxt)
    if hit is None:
        return []
    result = []
    while previous[hit] is not None:
        result.append(via[hit])
        hit = previous[hit]
    result.reverse()
    return result


def _upstream(graph, target):
    reverse = defaultdict(list)
    for source, outgoing in graph.items():
        for dest, source_plug, dest_plug, kind in outgoing:
            reverse[dest].append((source, source_plug, dest_plug, kind))
    start = _canonical(target)
    queue, seen = deque([start]), {start}
    while queue:
        current = queue.popleft()
        for source, _sp, _dp, _kind in reverse.get(current, []):
            if source not in seen:
                seen.add(source)
                queue.append(source)
    return seen


def _connections(node):
    if not cmds.objExists(node):
        return []
    raw = cmds.listConnections(node, source=True, destination=True,
                               connections=True, plugs=True,
                               skipConversionNodes=False) or []
    return [_canonical_plug(x) for x in raw]


def _plug_upstream(node_name, attr_name, logical_index=None):
    """OpenMaya plug-level traversal, honoring attribute-affects relationships."""
    selection = om.MSelectionList()
    selection.add(node_name)
    obj = selection.getDependNode(0)
    root = om.MFnDependencyNode(obj).findPlug(attr_name, False)
    if logical_index is not None:
        root = root.elementByLogicalIndex(logical_index)
    iterator = om.MItDependencyGraph(
        root, om.MFn.kInvalid,
        om.MItDependencyGraph.kUpstream,
        om.MItDependencyGraph.kDepthFirst,
        om.MItDependencyGraph.kPlugLevel,
    )
    result = []
    while not iterator.isDone():
        try:
            result.append(iterator.currentPlug().name())
        except RuntimeError:
            pass
        iterator.next()
    return sorted(set(result))


def run(path=OUTPUT):
    scene = cmds.file(query=True, sceneName=True)
    if "PHASE4_VALIDATION" not in os.path.basename(scene):
        raise RuntimeError("Refusing non-validation scene: " + scene)
    if cmds.ls("DIANA_SPINE_P4_*"):
        raise RuntimeError("Scene is not rolled back; P4 nodes still exist")

    edges = _all_edges()
    graph = _node_graph(edges)
    mode1 = ["DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM".format(p) for p in PARTS]
    production_fk = list(PARTS.values())

    fk_to_mode1 = {}
    for part, fk in PARTS.items():
        fk_to_mode1[part] = _shortest_path(graph, [fk], mode1)

    curve = "DIANA_SPINE_INDEPENDENT_IK_CURVE"
    curve_shape = (cmds.listRelatives(curve, shapes=True, fullPath=True) or [None])[0]
    curve_upstream = _upstream(graph, curve_shape or curve)
    cv_plug_paths = {}
    cv_upstream_nodes = set()
    if curve_shape:
        indices = cmds.getAttr(curve_shape + ".controlPoints", multiIndices=True) or []
        for index in indices:
            plug = "{}.controlPoints[{}]".format(curve_shape.rsplit("|", 1)[-1], index)
            plugs = _plug_upstream(curve_shape.rsplit("|", 1)[-1],
                                   "controlPoints", index)
            cv_plug_paths[str(index)] = plugs
            cv_upstream_nodes.update(_canonical(_node(x)) for x in plugs)
    ik_name_hits = sorted(x for x in curve_upstream
                          if any(token in x.lower() for token in
                                 ("ik_", "ikhip", "ikupper", "spine_ik", "hip_ik", "upper_ik")))
    fk_hits = sorted(x for x in curve_upstream
                     if _canonical(x) in {_canonical(v) for v in production_fk}
                     or "fk_spine" in x.lower())

    paths_to_curve = {}
    candidates = [x for x in cmds.ls(transforms=True) or []
                  if "ik" in x.lower() and ("spine" in x.lower() or "hip" in x.lower()
                                             or "upper" in x.lower())]
    for candidate in candidates:
        p = _shortest_path(graph, [candidate], [curve, curve_shape] if curve_shape else [curve])
        if p:
            paths_to_curve[_canonical(candidate)] = p
    fk_to_independent_curve = {
        part: _shortest_path(graph, [fk], [curve, curve_shape] if curve_shape else [curve])
        for part, fk in PARTS.items()
    }

    result = {
        "version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": scene,
        "read_only": True,
        "p4_nodes_present": cmds.ls("DIANA_SPINE_P4_*") or [],
        "edge_count": len(edges),
        "fk_to_mode1_paths": fk_to_mode1,
        "independent_ik_curve": {
            "transform": _canonical(curve),
            "shape": curve_shape,
            "upstream_count": len(curve_upstream),
            "upstream_nodes": sorted(curve_upstream),
            "cv_plug_level_upstream": cv_plug_paths,
            "cv_plug_level_production_fk_hits": sorted(
                cv_upstream_nodes & {_canonical(v) for v in production_fk}),
            "production_fk_hits": fk_hits,
            "ik_named_hits": ik_name_hits,
            "controller_paths": paths_to_curve,
            "production_fk_paths": fk_to_independent_curve,
            "transform_connections": _connections(curve),
            "shape_connections": _connections(curve_shape) if curve_shape else [],
        },
        "focus_connections": {name: _connections(name) for name in FOCUS},
        "legacy_curve_shapes": {
            shape: _connections(shape)
            for shape in (cmds.listRelatives("back_spine_curve", shapes=True,
                                             fullPath=True) or [])
        },
        "mode1_upstream_fk_hits": {
            part: sorted(_upstream(graph, node) & {_canonical(v) for v in production_fk})
            for part, node in zip(PARTS, mode1)
        },
        "interpretation": {
            "cycle_closure": "Adding MODE1 -> Follow -> production FK closes any existing production FK -> MODE1 path.",
            "inactive_branches": "All DG connections were traversed without evaluating selector values.",
        },
    }
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))

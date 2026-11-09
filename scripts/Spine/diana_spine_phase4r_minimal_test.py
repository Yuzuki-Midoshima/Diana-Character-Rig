# -*- coding: utf-8 -*-
"""Disposable Phase 4-R cycle reproduction and safe-layer topology test."""
from __future__ import absolute_import, division, print_function

import datetime
import json
import os
from collections import defaultdict

import maya.cmds as cmds

ROOT = "DIANA_SPINE_P4R_MINIMAL_TEST_GRP"
OUTPUT = os.path.join(os.path.dirname(__file__),
                      "Character_spine37_phase4r_minimal_test.json")


def _edges(nodes):
    result = []
    node_set = set(nodes)
    for node in nodes:
        raw = cmds.listConnections(node, s=True, d=False, c=True, p=True) or []
        for i in range(0, len(raw) - 1, 2):
            a, b = raw[i], raw[i + 1]
            dst, src = (a, b) if cmds.connectionInfo(a, isDestination=True) else (b, a)
            if src.split(".", 1)[0] in node_set:
                result.append((src, dst, "DG"))
        parent = cmds.listRelatives(node, parent=True, fullPath=False) or []
        if parent and parent[0] in node_set:
            result.append((parent[0] + ".worldMatrix[0]",
                           node + ".parentMatrix[0]", "DAG_PARENT"))
    return result


def _cyclic_nodes(edges):
    graph = defaultdict(list)
    nodes = set()
    for src, dst, _kind in edges:
        a, b = src.split(".", 1)[0], dst.split(".", 1)[0]
        graph[a].append(b); nodes.update((a, b))
    index, stack, on_stack, indices, low, cyclic = [0], [], set(), {}, {}, set()
    def visit(v):
        indices[v] = low[v] = index[0]; index[0] += 1
        stack.append(v); on_stack.add(v)
        for w in graph[v]:
            if w not in indices:
                visit(w); low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], indices[w])
        if low[v] == indices[v]:
            component = []
            while True:
                w = stack.pop(); on_stack.remove(w); component.append(w)
                if w == v: break
            if len(component) > 1 or v in graph[v]: cyclic.update(component)
    for node in list(nodes):
        if node not in indices: visit(node)
    return sorted(cyclic)


def cleanup():
    nodes = cmds.ls("DIANA_P4R_*") or []
    if nodes:
        cmds.delete(nodes)


def run(path=OUTPUT):
    cleanup()
    root = cmds.createNode("transform", name=ROOT)

    # Minimal reproduction: FK world -> legacy/MODE1 -> Follow OPM -> FK parent.
    repro = cmds.createNode("transform", name="DIANA_P4R_REPRO", parent=root)
    follow = cmds.createNode("transform", name="DIANA_P4R_REPRO_FOLLOW", parent=repro)
    fk = cmds.createNode("transform", name="DIANA_P4R_REPRO_FK", parent=follow)
    legacy = cmds.createNode("multMatrix", name="DIANA_P4R_REPRO_MODE1", parent=None)
    cmds.connectAttr(fk + ".worldMatrix[0]", legacy + ".matrixIn[0]")
    cmds.connectAttr(legacy + ".matrixSum", follow + ".offsetParentMatrix")
    repro_nodes = [repro, follow, fk, legacy]
    repro_edges = _edges(repro_nodes)
    repro_cycle = _cyclic_nodes(repro_edges)

    # Recommended topology: a separate operation control follows an independent
    # MODE1 source. Its local rotate contributes only downstream to MODE2.
    safe = cmds.createNode("transform", name="DIANA_P4R_SAFE", parent=root)
    mode1 = cmds.createNode("fourByFourMatrix", name="DIANA_P4R_SAFE_MODE1")
    for i in range(4): cmds.setAttr("{}.in{}{}".format(mode1, i, i), 1.0)
    operation = cmds.createNode("transform", name="DIANA_P4R_SAFE_OPERATION_FK", parent=safe)
    cmds.connectAttr(mode1 + ".output", operation + ".offsetParentMatrix")
    delta = cmds.createNode("composeMatrix", name="DIANA_P4R_SAFE_FK_DELTA")
    cmds.connectAttr(operation + ".rotate", delta + ".inputRotate")
    final = cmds.createNode("multMatrix", name="DIANA_P4R_SAFE_MODE2_FINAL")
    cmds.connectAttr(delta + ".outputMatrix", final + ".matrixIn[0]")
    cmds.connectAttr(mode1 + ".output", final + ".matrixIn[1]")
    safe_nodes = [safe, mode1, operation, delta, final]
    safe_edges = _edges(safe_nodes)
    safe_cycle = _cyclic_nodes(safe_edges)

    result = {
        "version": 1,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "scene": cmds.file(q=True, sn=True),
        "production_nodes_modified": False,
        "reproduction": {
            "edges": repro_edges,
            "cyclic_nodes": repro_cycle,
            "cycle_reproduced": bool(repro_cycle),
        },
        "recommended_topology": {
            "formula": "FK local delta x MODE1 final",
            "edges": safe_edges,
            "cyclic_nodes": safe_cycle,
            "cycle_free": not safe_cycle,
        },
    }
    cleanup()
    result["test_nodes_remaining"] = cmds.ls("DIANA_P4R_*") or []
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, sort_keys=True)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))

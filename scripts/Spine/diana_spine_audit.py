# -*- coding: utf-8 -*-
"""Read-only scene audit for the Diana spine rig.

This module intentionally creates no Maya nodes, changes no attributes, and
changes no connections.  Run ``run()`` in Maya's Script Editor and attach the
written JSON report when reviewing a scene.
"""

from __future__ import absolute_import, division, print_function

import datetime
import json
import os

import maya.cmds as cmds


REPORT_VERSION = 1

EXACT_NODES = (
    "Terminal",
    "DIANA_SPINE_INDEPENDENT_IK_CURVE",
    "DIANA_SPINE_LOWER_LIVE_DRIVER",
    "DIANA_SPINE_MIDDLE_LIVE_DRIVER",
    "DIANA_SPINE_SHOULDER_LIVE_DRIVER",
    "DIANA_SPINE_LOWER_FOLLOW_POCI",
    "DIANA_SPINE_MIDDLE_FOLLOW_POCI",
    "DIANA_SPINE_SHOULDER_FOLLOW_POCI",
    "hip_fk_Spine_anim_jnt",
    "lower_fk_Spine_anim",
    "middle_fk_Spine_OFFSET",
    "middle_fk_Spine_anim",
    "shoulder_fk_Spine_anim_jnt",
    "shoulder_spine_anim_pad",
    "shoulder_spine_anim",
)

DISCOVERY_PATTERNS = (
    "DIANA_SPINE_*",
    "*fk_Spine*",
    "*spine_anim*",
    "back_spine_curve*",
)

TRANSFORM_TYPES = {"transform", "joint"}


def _safe(callable_, default=None):
    try:
        return callable_()
    except Exception as exc:  # Audit must continue past locked/invalid plugs.
        return {"query_error": str(exc)} if default is None else default


def _plug_value(plug):
    def query():
        value = cmds.getAttr(plug)
        # Maya frequently wraps vector values in a one-item tuple/list.
        if isinstance(value, (tuple, list)) and len(value) == 1:
            value = value[0]
        return value

    return _safe(query)


def _connections(node):
    raw = cmds.listConnections(
        node, source=True, destination=True, connections=True, plugs=True
    ) or []
    pairs = []
    for index in range(0, len(raw) - 1, 2):
        pairs.append({"plug": raw[index], "connected_plug": raw[index + 1]})
    return sorted(pairs, key=lambda item: (item["plug"], item["connected_plug"]))


def _matrix(plug):
    value = _plug_value(plug)
    if isinstance(value, (tuple, list)) and len(value) == 1:
        value = value[0]
    return list(value) if isinstance(value, (tuple, list)) else value


def _transform_data(node, node_type):
    if node_type not in TRANSFORM_TYPES:
        return None
    data = {
        "parent": (cmds.listRelatives(node, parent=True, fullPath=True) or [None])[0],
        "children": cmds.listRelatives(node, children=True, fullPath=True) or [],
        "world_matrix": _matrix(node + ".worldMatrix[0]"),
        "parent_inverse_matrix": _matrix(node + ".parentInverseMatrix[0]"),
        "rotate_order": _plug_value(node + ".rotateOrder"),
        "translate": _plug_value(node + ".translate"),
        "rotate": _plug_value(node + ".rotate"),
        "scale": _plug_value(node + ".scale"),
        "rotate_pivot_local": _safe(lambda: cmds.xform(node, q=True, rp=True, os=True)),
        "rotate_pivot_world": _safe(lambda: cmds.xform(node, q=True, rp=True, ws=True)),
        "offset_parent_matrix": _matrix(node + ".offsetParentMatrix"),
    }
    if node_type == "joint":
        data["joint_orient"] = _plug_value(node + ".jointOrient")
        data["segment_scale_compensate"] = _plug_value(
            node + ".segmentScaleCompensate"
        )
    return data


def _node_data(node):
    node_type = cmds.nodeType(node)
    interesting_attrs = {}
    for attr in (
        "Spine_Mode",
        "inputCurve",
        "parameter",
        "turnOnPercentage",
        "position",
        "tangent",
        "matrixSum",
        "outputMatrix",
    ):
        plug = node + "." + attr
        if cmds.objExists(plug):
            interesting_attrs[attr] = _plug_value(plug)
    return {
        "name": node,
        "type": node_type,
        "referenced": bool(cmds.referenceQuery(node, isNodeReferenced=True)),
        "locked": bool(cmds.lockNode(node, q=True, lock=True)[0]),
        "transform": _transform_data(node, node_type),
        "interesting_attributes": interesting_attrs,
        "connections": _connections(node),
    }


def _discover_nodes():
    found = set()
    for pattern in DISCOVERY_PATTERNS:
        found.update(cmds.ls(pattern, long=False) or [])
    found.update(node for node in EXACT_NODES if cmds.objExists(node))
    return sorted(found)


def _find_skin_clusters():
    result = []
    for node in cmds.ls(type="skinCluster") or []:
        influences = _safe(lambda n=node: cmds.skinCluster(n, q=True, influence=True), [])
        spine_influences = [
            influence
            for influence in influences
            if "spine" in influence.lower() or "back" in influence.lower()
        ]
        if spine_influences:
            result.append(
                {
                    "name": node,
                    "spine_influences": spine_influences,
                    "geometry": _safe(
                        lambda n=node: cmds.skinCluster(n, q=True, geometry=True), []
                    ),
                }
            )
    return result


def collect():
    """Return a JSON-serializable snapshot without modifying the scene."""
    nodes = _discover_nodes()
    mode_plug = "Terminal.Spine_Mode"
    return {
        "report_version": REPORT_VERSION,
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "maya_version": cmds.about(version=True),
        "scene": cmds.file(q=True, sceneName=True),
        "scene_modified_before_audit": bool(cmds.file(q=True, modified=True)),
        "evaluation_mode": cmds.evaluationManager(q=True, mode=True),
        "cycle_check_enabled": bool(cmds.cycleCheck(q=True, evaluation=True)),
        "namespace": cmds.namespaceInfo(currentNamespace=True),
        "mode": {
            "plug_exists": cmds.objExists(mode_plug),
            "value": _plug_value(mode_plug) if cmds.objExists(mode_plug) else None,
            "enum": _safe(lambda: cmds.attributeQuery("Spine_Mode", node="Terminal", listEnum=True)),
            "incoming": cmds.connectionInfo(mode_plug, sourceFromDestination=True)
            if cmds.objExists(mode_plug)
            else None,
            "destinations": cmds.connectionInfo(mode_plug, destinationFromSource=True)
            if cmds.objExists(mode_plug)
            else [],
        },
        "required_node_presence": {
            node: bool(cmds.objExists(node)) for node in EXACT_NODES
        },
        "discovered_nodes": [_node_data(node) for node in nodes],
        "skin_clusters_using_spine_influences": _find_skin_clusters(),
    }


def run(output_path=None):
    """Collect, print, and optionally save the audit report.

    If ``output_path`` is omitted, only a compact summary is printed and the
    full report is returned.  Supplying a path writes JSON but still does not
    alter the Maya scene.
    """
    was_modified = bool(cmds.file(q=True, modified=True))
    report = collect()
    is_modified = bool(cmds.file(q=True, modified=True))
    report["scene_modified_after_audit"] = is_modified
    report["audit_changed_modified_flag"] = was_modified != is_modified

    if output_path:
        output_path = os.path.abspath(os.path.expanduser(output_path))
        parent = os.path.dirname(output_path)
        if parent and not os.path.isdir(parent):
            raise RuntimeError("Output directory does not exist: " + parent)
        with open(output_path, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, ensure_ascii=False)
        print("[DIANA SPINE AUDIT] Wrote: " + output_path)

    missing = [
        name for name, exists in report["required_node_presence"].items() if not exists
    ]
    print("[DIANA SPINE AUDIT] Discovered nodes:", len(report["discovered_nodes"]))
    print("[DIANA SPINE AUDIT] Missing named nodes:", len(missing))
    print("[DIANA SPINE AUDIT] Scene changed by audit:", report["audit_changed_modified_flag"])
    return report


if __name__ == "__main__":
    run()


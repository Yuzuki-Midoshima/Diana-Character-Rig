# -*- coding: utf-8 -*-
"""Manifest-backed rollback for Phase 5-B attachments."""
from __future__ import absolute_import, division, print_function
import json
import maya.cmds as cmds
from . import diana_spine_phase5b_integrate as integration


def rollback(path=integration.MANIFEST):
    with open(path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    for stage in reversed(manifest.get("stages", [])):
        side = stage["side"]
        spec = integration.SIDE_DATA[side]
        constraint = stage["constraint"]
        body_target = stage["body_target"]
        if cmds.objExists(constraint) and cmds.objExists(body_target):
            targets = cmds.parentConstraint(constraint, q=True, targetList=True) or []
            if body_target in targets:
                cmds.parentConstraint(body_target, spec["hand_const"], e=True, rm=True)
        old_plug = constraint + "." + stage["old_alias"]
        if cmds.objExists(old_plug):
            current = integration.source(old_plug)
            if current:
                cmds.disconnectAttr(current, old_plug)
            if stage["old_source"]:
                cmds.connectAttr(stage["old_source"], old_plug, force=True)
            else:
                original = manifest["sides"][side]["constraint"]["targets"][0]["value"]
                cmds.setAttr(old_plug, original)
        for node, saved in manifest["sides"][side]["roots"].items():
            plug = node + ".offsetParentMatrix"
            current = integration.source(plug)
            if current:
                cmds.disconnectAttr(current, plug)
            if saved["opm_source"]:
                cmds.connectAttr(saved["opm_source"], plug, force=True)
            else:
                cmds.setAttr(plug, *saved["opm"], type="matrix")
    nodes = []
    if cmds.objExists(integration.REGISTRY):
        nodes = cmds.listConnections(integration.REGISTRY + ".nodes", s=True, d=False) or []
    nodes = [x for x in nodes if cmds.objExists(x)]
    if nodes:
        cmds.delete(nodes)
    if cmds.objExists(integration.REGISTRY):
        cmds.delete(integration.REGISTRY)
    return {"remaining": cmds.ls("DIANA_SPINE_P5B_*") or [],
            "root_exists": cmds.objExists(integration.ROOT)}


if __name__ == "__main__":
    print(rollback())

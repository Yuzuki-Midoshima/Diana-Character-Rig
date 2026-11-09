# -*- coding: utf-8 -*-
"""Build the disposable Diana Spine Phase 2/3 proxy network.

Production nodes are read-only inputs.  All created nodes are parented below
ROOT or registered in its ``dianaProxyNodes`` message array.
"""

from __future__ import absolute_import, division, print_function

import json

import maya.cmds as cmds


ROOT = "DIANA_SPINE_P23_PROXY_GRP"
VERSION = 1

PARTS = (
    ("HIP", "hip_fk_Spine_anim_jnt"),
    ("LOWER", "lower_fk_Spine_anim"),
    ("MIDDLE", "middle_fk_Spine_anim"),
    ("SHOULDER", "shoulder_fk_Spine_anim_jnt"),
)


def _required():
    names = ["Terminal"]
    for part, fk in PARTS:
        names.extend(
            [fk, "DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM".format(part)]
        )
    names.extend(("shoulder_spine_anim_pad", "shoulder_spine_anim"))
    missing = [name for name in names if not cmds.objExists(name)]
    if missing:
        raise RuntimeError("Missing required nodes: " + ", ".join(missing))
    if not cmds.objExists("Terminal.Spine_Mode"):
        raise RuntimeError("Missing Terminal.Spine_Mode")


def _register(root, node):
    index = len(cmds.getAttr(root + ".dianaProxyNodes", multiIndices=True) or [])
    cmds.connectAttr(node + ".message", "{}.dianaProxyNodes[{}]".format(root, index))


def _node(root, node_type, name):
    node = cmds.createNode(node_type, name=name)
    _register(root, node)
    return node


def _matrix_value(plug):
    value = cmds.getAttr(plug)
    if isinstance(value, (tuple, list)) and len(value) == 1:
        value = value[0]
    return list(value)


def _copy_transform_values(source, target):
    for attr in ("translate", "rotate", "scale", "shear", "rotatePivot",
                 "rotatePivotTranslate", "scalePivot", "scalePivotTranslate"):
        if cmds.objExists(source + "." + attr) and cmds.objExists(target + "." + attr):
            value = cmds.getAttr(source + "." + attr)[0]
            cmds.setAttr(target + "." + attr, *value)
    cmds.setAttr(target + ".rotateOrder", cmds.getAttr(source + ".rotateOrder"))


def build():
    """Create the isolated proxy. Refuses to overwrite an existing proxy."""
    _required()
    if cmds.objExists(ROOT):
        raise RuntimeError("Proxy already exists; run diana_spine_proxy_cleanup.remove()")

    root = cmds.createNode("transform", name=ROOT)
    cmds.addAttr(root, longName="dianaProxyVersion", attributeType="long", defaultValue=VERSION)
    cmds.addAttr(root, longName="dianaProxyNodes", attributeType="message", multi=True)
    cmds.addAttr(root, longName="dianaProxyManifest", dataType="string")
    cmds.addAttr(root, longName="productionReadOnly", attributeType="bool", defaultValue=True)
    cmds.setAttr(root + ".productionReadOnly", lock=True)

    proxies = {}
    previous = root
    manifest = {"version": VERSION, "root": ROOT, "parts": {}}

    for part, fk in PARTS:
        prefix = "DIANA_SPINE_P23_" + part
        proxy = cmds.createNode("transform", name=prefix + "_PROXY", parent=previous)
        _register(root, proxy)
        proxies[part] = proxy

        cmds.setAttr(proxy + ".rotateOrder", cmds.getAttr(fk + ".rotateOrder"))
        for attr in ("translate", "rotate"):
            cmds.setAttr(proxy + "." + attr, 0.0, 0.0, 0.0)
        cmds.setAttr(proxy + ".scale", 1.0, 1.0, 1.0)

        # Compose animator rotation in the controller's real Euler order.
        delta_cm = _node(root, "composeMatrix", prefix + "_FK_DELTA_CM")
        cmds.connectAttr(fk + ".rotate", delta_cm + ".inputRotate")
        if cmds.objExists(delta_cm + ".inputRotateOrder"):
            cmds.connectAttr(fk + ".rotateOrder", delta_cm + ".inputRotateOrder")

        # Mode 0: FK world. Mode 1: MODE1 only. Mode 2: local FK delta once.
        delta_choice = _node(root, "choice", prefix + "_DELTA_CHOICE")
        cmds.connectAttr("Terminal.Spine_Mode", delta_choice + ".selector")
        # Each choice.input element is generic independently. Typed matrix
        # connections are therefore used for all elements (setAttr cannot set
        # an untyped generic element to matrix data in Maya 2026).
        identity_fbf = _node(root, "fourByFourMatrix", prefix + "_IDENTITY_FBF")
        for index in range(4):
            cmds.setAttr("{}.in{}{}".format(identity_fbf, index, index), 1.0)
        cmds.connectAttr(identity_fbf + ".output", delta_choice + ".input[0]")
        cmds.connectAttr(identity_fbf + ".output", delta_choice + ".input[1]")
        cmds.connectAttr(delta_cm + ".outputMatrix", delta_choice + ".input[2]")

        base_choice = _node(root, "choice", prefix + "_BASE_CHOICE")
        cmds.connectAttr("Terminal.Spine_Mode", base_choice + ".selector")
        cmds.connectAttr(fk + ".worldMatrix[0]", base_choice + ".input[0]")
        mode1 = "DIANA_SPINE_DEFORM_{}_MODE1_FINAL_MM.matrixSum".format(part)
        cmds.connectAttr(mode1, base_choice + ".input[1]")
        cmds.connectAttr(mode1, base_choice + ".input[2]")

        desired_mm = _node(root, "multMatrix", prefix + "_DESIRED_WORLD_MM")
        cmds.connectAttr(delta_choice + ".output", desired_mm + ".matrixIn[0]")
        cmds.connectAttr(base_choice + ".output", desired_mm + ".matrixIn[1]")

        local_mm = _node(root, "multMatrix", prefix + "_PARENT_LOCAL_MM")
        cmds.connectAttr(desired_mm + ".matrixSum", local_mm + ".matrixIn[0]")
        cmds.connectAttr(previous + ".worldInverseMatrix[0]", local_mm + ".matrixIn[1]")
        cmds.connectAttr(local_mm + ".matrixSum", proxy + ".offsetParentMatrix")

        jo = cmds.getAttr(fk + ".jointOrient")[0] if cmds.nodeType(fk) == "joint" else (0, 0, 0)
        for axis, value in zip("XYZ", jo):
            cmds.addAttr(proxy, longName="sourceJointOrient" + axis,
                         attributeType="double", defaultValue=value)
            cmds.setAttr(proxy + ".sourceJointOrient" + axis, lock=True)

        manifest["parts"][part] = {
            "fk": fk,
            "proxy": proxy,
            "mode1": mode1,
            "rotate_order": cmds.getAttr(fk + ".rotateOrder"),
            "joint_orient": list(jo),
            "build_fk_world": _matrix_value(fk + ".worldMatrix[0]"),
        }
        previous = proxy

    # Reproduce the unusual shoulder pad/control/pivot below the shoulder proxy.
    pad = cmds.createNode("transform", name="DIANA_SPINE_P23_SHOULDER_PAD_PROXY",
                          parent=proxies["SHOULDER"])
    _register(root, pad)
    _copy_transform_values("shoulder_spine_anim_pad", pad)
    ctrl = cmds.createNode("transform", name="DIANA_SPINE_P23_SHOULDER_CTRL_PROXY",
                           parent=pad)
    _register(root, ctrl)
    _copy_transform_values("shoulder_spine_anim", ctrl)
    manifest["shoulder_pivot"] = {
        "pad": pad,
        "control": ctrl,
        "source_local_pivot": list(cmds.xform("shoulder_spine_anim", q=True, os=True, rp=True)),
    }

    cmds.setAttr(root + ".dianaProxyManifest", json.dumps(manifest, sort_keys=True), type="string")
    print("[DIANA SPINE P23] Proxy built. Production nodes are read-only inputs.")
    return manifest


def status():
    if not cmds.objExists(ROOT):
        return {"exists": False}
    nodes = cmds.listConnections(ROOT + ".dianaProxyNodes", source=True, destination=False) or []
    return {"exists": True, "root": ROOT, "registered_nodes": sorted(set(nodes))}


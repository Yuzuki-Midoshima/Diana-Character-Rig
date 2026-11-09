# -*- coding: utf-8 -*-
"""Drag this file into a Maya 2026 viewport to install Diana Character Rig.

The generated Maya module file points at this repository's current location.
Move the repository by moving the whole folder, then run this installer again.
"""
from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel

MODULE_NAME = "DianaCharacterRig"
MODULE_VERSION = "1.0"
MODULE_FILENAME = MODULE_NAME + ".mod"
SHELF_NAME = "DianaCharacterRig"
SHELF_LABEL = "Diana Rig"
SHELF_BUTTONS = (
    {
        "doc_tag": "DianaCharacterRig.PivotTransfer",
        "label": "Diana Pivot",
        "annotation": "Open Diana Pivot Transfer",
        "command": "from Pivot_Transfer import Shelf; Shelf.show()",
    },
    {
        "doc_tag": "DianaCharacterRig.EquipmentManager",
        "label": "Equipment",
        "annotation": "Open Diana Equipment Manager",
        "command": "import launch_equipment_manager as equipment; equipment.show()",
    },
)


def _repository_root():
    root = Path(__file__).resolve().parent
    required = root / "scripts" / "diana_pivot_autostart.py"
    if not required.is_file():
        raise RuntimeError("Incomplete Diana repository: missing {}".format(required))
    return root


def _modules_directory():
    return Path(cmds.internalVar(userAppDir=True)) / "modules"


def _module_text(root):
    # Maya .mod files use forward slashes on every supported platform.
    return "+ {} {} {}\n".format(
        MODULE_NAME, MODULE_VERSION, root.as_posix()
    )


def _shelf_top_level():
    return mel.eval("$tmp = $gShelfTopLevel")


def _save_shelves():
    mel.eval("saveAllShelves $gShelfTopLevel;")


def _ensure_shelf():
    top_level = _shelf_top_level()
    if cmds.shelfLayout(SHELF_NAME, exists=True):
        shelf = SHELF_NAME
    else:
        shelf = cmds.shelfLayout(SHELF_NAME, parent=top_level)
    cmds.tabLayout(top_level, edit=True, tabLabel=(shelf, SHELF_LABEL))
    return shelf


def _remove_managed_buttons(shelf):
    """Remove only buttons owned by this installer."""
    managed_tags = {item["doc_tag"] for item in SHELF_BUTTONS}
    for control in cmds.shelfLayout(shelf, query=True, childArray=True) or []:
        try:
            tag = cmds.shelfButton(control, query=True, docTag=True)
        except RuntimeError:
            continue
        if tag in managed_tags:
            cmds.deleteUI(control)


def install_shelf():
    """Create a repeatable Diana shelf with Pivot and Equipment buttons."""
    shelf = _ensure_shelf()
    _remove_managed_buttons(shelf)
    for item in SHELF_BUTTONS:
        cmds.shelfButton(
            parent=shelf,
            label=item["label"],
            annotation=item["annotation"],
            command=item["command"],
            sourceType="python",
            image1="pythonFamily.png",
            docTag=item["doc_tag"],
        )
    _save_shelves()
    print("[DIANA] Shelf installed: {}".format(SHELF_LABEL))


def install():
    """Install a small .mod pointer; repository files are not copied."""
    root = _repository_root()
    modules_dir = _modules_directory()
    modules_dir.mkdir(parents=True, exist_ok=True)
    module_file = modules_dir / MODULE_FILENAME
    module_file.write_text(_module_text(root), encoding="utf-8")
    install_shelf()
    message = (
        "Diana Character Rig was installed.\n\n"
        "Restart Maya 2026 to load it.\n\n{}"
    ).format(module_file)
    cmds.confirmDialog(title="Diana Character Rig", message=message, button=["OK"])
    print("[DIANA] Installed module: {}".format(module_file))
    return module_file


def uninstall():
    """Remove only this installer's module pointer."""
    module_file = _modules_directory() / MODULE_FILENAME
    if module_file.exists():
        module_file.unlink()
        print("[DIANA] Removed module: {}".format(module_file))
    else:
        print("[DIANA] Module is not installed: {}".format(module_file))
    if cmds.shelfLayout(SHELF_NAME, exists=True):
        _remove_managed_buttons(SHELF_NAME)
        remaining = cmds.shelfLayout(
            SHELF_NAME, query=True, childArray=True
        ) or []
        if not remaining:
            cmds.deleteUI(SHELF_NAME)
        _save_shelves()
        print("[DIANA] Managed shelf buttons removed")
    return module_file


def onMayaDroppedPythonFile(*_args, **_kwargs):
    module_file = _modules_directory() / MODULE_FILENAME
    if not module_file.exists():
        install()
        return

    choice = cmds.confirmDialog(
        title="Diana Character Rig",
        message="Diana Character Rig is already installed.",
        button=["Reinstall", "Uninstall", "Cancel"],
        defaultButton="Reinstall",
        cancelButton="Cancel",
        dismissString="Cancel",
    )
    if choice == "Reinstall":
        install()
    elif choice == "Uninstall":
        uninstall()
        cmds.confirmDialog(
            title="Diana Character Rig",
            message="Uninstalled. Restart Maya 2026 to finish.",
            button=["OK"],
        )

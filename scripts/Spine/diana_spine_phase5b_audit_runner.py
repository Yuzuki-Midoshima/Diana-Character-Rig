# -*- coding: utf-8 -*-
import os, sys
import maya.standalone
maya.standalone.initialize(name="python")
import maya.cmds as cmds
scripts = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if scripts not in sys.path: sys.path.insert(0, scripts)
from Spine import diana_spine_phase5b_audit as audit
SOURCE = r"C:/Users/draco/OneDrive/ドキュメント/maya/projects/JAM_rig/scenes/Character_spine37.ma"
cmds.file(SOURCE, open=True, force=True, prompt=False)
audit.run()
maya.standalone.uninitialize()

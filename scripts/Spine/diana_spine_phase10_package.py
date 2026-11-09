# -*- coding: utf-8 -*-
"""Create a relocatable Diana Spine RC ZIP using only the standard library."""
from __future__ import absolute_import, division, print_function
import json, os, zipfile

HERE=os.path.dirname(os.path.abspath(__file__));SCRIPTS=os.path.dirname(HERE);REPO=os.path.dirname(SCRIPTS)
OUTPUT=os.path.join(REPO,"dist","Diana_Spine_RC01.zip")


def build(output=OUTPUT):
    rc=os.path.join(REPO,"dist","Character_spine37_SPINE_RC01.ma")
    if not os.path.isfile(rc):raise RuntimeError("RC scene is missing: "+rc)
    files=[rc]
    files += [os.path.join(HERE,n) for n in os.listdir(HERE) if n.endswith(".py")]
    files += [os.path.join(HERE,n) for n in ("PHASE_10_SETUP.md","PHASE_10_ANIMATOR_GUIDE.md","PHASE_10_REPORT.md",
              "Character_spine37_phase10_rc_manifest.json","Character_spine37_phase10_validation.json") if os.path.isfile(os.path.join(HERE,n))]
    os.makedirs(os.path.dirname(output),exist_ok=True)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path,os.path.relpath(path,REPO).replace("\\","/"))
    result={"zip":output,"size_bytes":os.path.getsize(output),"file_count":len(set(files))}
    print(json.dumps(result,ensure_ascii=False));return result


if __name__=="__main__":build()

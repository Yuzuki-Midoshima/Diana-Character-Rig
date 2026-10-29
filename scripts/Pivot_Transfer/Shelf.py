import os
import sys
import shutil
import importlib

FOLDER = os.path.join(
    os.path.expanduser("~"),
    "OneDrive", "ドキュメント",
    "maya", "scripts", "Diana",
    "Pivot_Transfer"
)

UI_FILE = os.path.join(
    FOLDER,
    "diana_pivot_transfer_ui.py"
)

DEPENDENCY = os.path.join(
    FOLDER,
    "diana_pivot_to_all.py"
)

OLD = (
    "import scripts.Pivot_Transfer."
    "diana_pivot_to_all as pta"
)

NEW = "import diana_pivot_to_all as pta"

print("\n===== DIANA UI IMPORT FIX =====")

for path in (UI_FILE, DEPENDENCY):
    if not os.path.isfile(path):
        raise RuntimeError(
            "Required file missing: " + path
        )

with open(UI_FILE, "r", encoding="utf-8-sig") as f:
    content = f.read()

if OLD in content:
    backup = UI_FILE + ".bak"

    if not os.path.exists(backup):
        shutil.copy2(UI_FILE, backup)
        print("BACKUP:", backup)

    content = content.replace(OLD, NEW)

    with open(UI_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("IMPORT FIXED")

elif NEW in content:
    print("Import already fixed")

else:
    raise RuntimeError(
        "Expected import statement not found. "
        "No changes made."
    )

if FOLDER not in sys.path:
    sys.path.insert(0, FOLDER)

import diana_pivot_transfer_ui as pivot_ui

importlib.reload(pivot_ui)

pivot_ui.show_ui()

print("DIANA UI STARTED")
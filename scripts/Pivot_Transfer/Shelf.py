import sys
import importlib

ROOT = r"C:\Users\draco\OneDrive\ドキュメント\GitHub\Diana-Character-Rig"

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import scripts.Pivot_Transfer.diana_pivot_transfer_ui as pivot_ui

importlib.reload(pivot_ui)

pivot_ui.show_ui()
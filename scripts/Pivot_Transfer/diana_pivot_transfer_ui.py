import maya.cmds as cmds
import importlib

from . import diana_pivot_to_all as pta


# ============================================================
# DIANA PIVOT / ALL TRANSFER UI
#
# ALL -> Pivot
#     ALLを現在のPivot位置へ移す
#     pta.bake_to_all()
#
# Pivot -> ALL
#     Pivot側からALL側へ戻す
#     pta.return_diana()
#
# ============================================================


WINDOW = "DianaPivotTransferWindow"

WINDOW_TITLE = "Diana Pivot Transfer"

WINDOW_WIDTH = 360
WINDOW_HEIGHT = 135


# ============================================================
# COLORS
# ============================================================

# ALL -> Pivot
# くすんだ赤
COLOR_ALL_TO_PIVOT = (
    0.42,
    0.28,
    0.28
)

# Pivot -> ALL
# くすんだ青
COLOR_PIVOT_TO_ALL = (
    0.30,
    0.40,
    0.50
)


# ============================================================
# ALL -> Pivot
# ============================================================

def all_to_pivot(*args):

    """
    ALLを現在のPivot位置へ移す。
    ALLが0の状態からでも実行可能。
    """

    importlib.reload(pta)

    print("\n" + "=" * 70)
    print("[DIANA UI] ALL -> Pivot")
    print("[DIANA UI] Running: pta.bake_to_all()")
    print("=" * 70)

    try:

        pta.bake_to_all()

        cmds.inViewMessage(
            amg="<hl>ALL → Pivot</hl> 完了",
            pos="midCenter",
            fade=True
        )

    except Exception as exc:

        cmds.warning(
            "[DIANA UI] ALL -> Pivot failed: {}".format(
                exc
            )
        )

        raise


# ============================================================
# Pivot -> ALL
# ============================================================

def pivot_to_all(*args):

    """
    Pivot側からALL側へ戻す。
    """

    importlib.reload(pta)

    print("\n" + "=" * 70)
    print("[DIANA UI] Pivot -> ALL")
    print("[DIANA UI] Running: pta.return_diana()")
    print("=" * 70)

    try:

        pta.return_diana()

        cmds.inViewMessage(
            amg="<hl>Pivot → ALL</hl> 完了",
            pos="midCenter",
            fade=True
        )

    except Exception as exc:

        cmds.warning(
            "[DIANA UI] Pivot -> ALL failed: {}".format(
                exc
            )
        )

        raise


# ============================================================
# UI
# ============================================================

def show_ui():

    # --------------------------------------------------------
    # 古いWindowを削除
    # --------------------------------------------------------

    if cmds.window(
        WINDOW,
        exists=True
    ):
        cmds.deleteUI(
            WINDOW
        )


    # --------------------------------------------------------
    # Window
    # --------------------------------------------------------

    window = cmds.window(
        WINDOW,
        title=WINDOW_TITLE,
        widthHeight=(
            WINDOW_WIDTH,
            WINDOW_HEIGHT
        ),
        sizeable=False
    )


    # --------------------------------------------------------
    # Main Layout
    # --------------------------------------------------------

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnAttach=(
            "both",
            12
        )
    )


    cmds.separator(
        height=4,
        style="none"
    )


    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    cmds.text(
        label="Pivot / ALL Transfer",
        height=22,
        font="boldLabelFont"
    )


    cmds.text(
        label="ALLとPivotの位置を相互に移管します",
        height=20,
        align="center"
    )


    cmds.separator(
        height=5,
        style="none"
    )


    # --------------------------------------------------------
    # Buttons
    # --------------------------------------------------------

    cmds.rowLayout(
        numberOfColumns=2,

        columnWidth2=(
            165,
            165
        ),

        columnAttach=[
            (
                1,
                "both",
                2
            ),
            (
                2,
                "both",
                2
            ),
        ]
    )


    # ========================================================
    # ALL -> Pivot
    #
    # ALLが足元へ動く方
    # ========================================================

    cmds.button(
        label="ALL → Pivot",

        height=42,

        backgroundColor=COLOR_ALL_TO_PIVOT,

        annotation=(
            "ALLを現在のPivot位置へ移します"
        ),

        command=all_to_pivot
    )


    # ========================================================
    # Pivot -> ALL
    #
    # 逆方向へ戻す方
    # ========================================================

    cmds.button(
        label="Pivot → ALL",

        height=42,

        backgroundColor=COLOR_PIVOT_TO_ALL,

        annotation=(
            "Pivot側からALL側へ戻します"
        ),

        command=pivot_to_all
    )


    cmds.setParent(
        ".."
    )


    cmds.separator(
        height=5,
        style="none"
    )


    # --------------------------------------------------------
    # Show
    # --------------------------------------------------------

    cmds.showWindow(
        window
    )


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    show_ui()

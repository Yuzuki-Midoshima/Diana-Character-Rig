import maya.cmds as cmds

import maya.api.OpenMaya as om




# ============================================================

# DIANA PIVOT / ALL TRANSFER

#

# Maya 2026 / Python 3

#

# Pivot -> ALL

#     bake_to_all()

#

# ALL -> Pivot

#     return_diana()

#

# ============================================================




ALL = "ALL_anim"

PIVOT = "Body_Rot_Pivot_anim"

SYSTEM = "Body_Rot_SYSTEM_GRP"




COG = "COG_anim"




LEFT_FOOT = "L_i_K_Foot_anim"

RIGHT_FOOT = "R_i_K_Foot_anim"




ARM_DATA = {

    "L": {

        "setting": "L_arm_settings_anim",

        "controls": [

            "Ik_L_hand_anim",

            "IK_L_elbow_anim",

        ],

    },




    "R": {

        "setting": "R_arm_settings_anim",

        "controls": [

            "Ik_R_hand_anim",

            "IK_R_elbow_anim",

        ],

    },

}




TR_CHANNELS = [

    "translateX",

    "translateY",

    "translateZ",

    "rotateX",

    "rotateY",

    "rotateZ",

]




MATRIX_TOLERANCE = 0.0001




# ============================================================

# UTILITY

# ============================================================




def _exists(node):




    if not cmds.objExists(node):

        cmds.error(

            "[DIANA] Missing node: " + node

        )




def _world_matrix(node):




    return cmds.xform(

        node,

        q=True,

        ws=True,

        matrix=True

    )




def _matrix_error(a, b):




    return max(

        abs(x - y)

        for x, y in zip(a, b)

    )




def _matrix_position(matrix):




    return [

        round(matrix[12], 5),

        round(matrix[13], 5),

        round(matrix[14], 5),

    ]




def _set_world_matrix(node, matrix):




    cmds.xform(

        node,

        ws=True,

        matrix=matrix

    )




def _ensure_scale():




    scale = cmds.getAttr(

        ALL + ".scale"

    )[0]




    target = (

        2.0,

        2.0,

        2.0,

    )




    if any(

        abs(scale[i] - target[i]) > 0.000001

        for i in range(3)

    ):




        cmds.setAttr(

            ALL + ".scale",

            2.0,

            2.0,

            2.0,

            type="double3"

        )




def _disconnect_all_tr_inputs():




    disconnected = []




    for attr in TR_CHANNELS:




        dst = ALL + "." + attr




        source = cmds.connectionInfo(

            dst,

            sourceFromDestination=True

        )




        if not source:

            continue




        try:




            cmds.disconnectAttr(

                source,

                dst

            )




            disconnected.append(

                (source, dst)

            )




            print(

                "[DIANA] Disconnected:",

                source,

                "->",

                dst

            )




        except Exception as exc:




            cmds.warning(

                "[DIANA] Could not disconnect {} -> {} : {}".format(

                    source,

                    dst,

                    exc

                )

            )




    return disconnected




def _get_animator_targets():




    """

    World Poseを保護するAnimator Controlを取得。

    Legs:
        L Foot
        R Foot

    Arms:
        IK時のみ
            Hand IK
            Elbow PV

    IMPORTANT:
        COGはWorld Matrix保護対象に含めない。

        COGには独自のrotatePivotが存在するため、
        World Matrixを書き戻すとrotatePivotTranslateが
        書き換わる場合がある。

        COGのPoseはreturn_diana()側で
        Local Translate / Rotateとして保存・復元する。
    """




    targets = [

    LEFT_FOOT,

    RIGHT_FOOT,




    ]




    for side, data in ARM_DATA.items():




        setting = data["setting"]

        plug = setting + ".FKIK"




        if not cmds.objExists(plug):




            cmds.warning(

                "[DIANA] Missing FKIK attribute: "

                + plug

            )




            continue




        value = cmds.getAttr(

            plug

        )




        print(

            "[DIANA] {} Arm FKIK = {}".format(

                side,

                value

            )

        )




        if value >= 0.5:




            print(

                "[DIANA] {} Arm = IK".format(

                    side

                )

            )




            for ctrl in data["controls"]:




                if cmds.objExists(ctrl):




                    targets.append(

                        ctrl

                    )




                else:




                    cmds.warning(

                        "[DIANA] Missing IK control: "

                        + ctrl

                    )




        else:




            print(

                "[DIANA] {} Arm = FK / ignored".format(

                    side

                )

            )




    return list(

        dict.fromkeys(targets)

    )




def _rotation_from_matrix(matrix):




    m = om.MMatrix(

        matrix

    )




    tm = om.MTransformationMatrix(

        m

    )




    euler = tm.rotation()




    return (

        om.MAngle(

            euler.x,

            om.MAngle.kRadians

        ).asDegrees(),




        om.MAngle(

            euler.y,

            om.MAngle.kRadians

        ).asDegrees(),




        om.MAngle(

            euler.z,

            om.MAngle.kRadians

        ).asDegrees(),

    )




# ============================================================

# PIVOT -> ALL

# ============================================================





# ============================================================
# ALL foot-position display alignment, without altering rig zero
# ============================================================

def align_all_to_feet_v6():
    """Align the actual ALL rotation pivot to feet, preserving world poses.

    Uses the character's ALL-local frame for the foot-height calculation.
    Does NOT touch history-driven NURBS curve geometry or rig transforms.
    Note: moving the rotate pivot does not automatically center the visible
    NURBS controller curve. This is intentional for safety.
    """
    for node in (ALL, COG, LEFT_FOOT, RIGHT_FOOT):
        _exists(node)

    all_world = om.MMatrix(_world_matrix(ALL))
    inverse = all_world.inverse()

    def local_pos(node):
        p = cmds.xform(node, q=True, ws=True, t=True)
        v = om.MPoint(p[0], p[1], p[2]) * inverse
        return om.MPoint(v.x, v.y, v.z)

    cog = local_pos(COG)
    lf = local_pos(LEFT_FOOT)
    rf = local_pos(RIGHT_FOOT)
    target_local = om.MPoint(cog.x, min(lf.y, rf.y), cog.z)
    target_world = target_local * all_world
    target = [target_world.x, target_world.y, target_world.z]

    protected = [ALL, COG, LEFT_FOOT, RIGHT_FOOT]
    before = {n: _world_matrix(n) for n in protected}
    before_tr = [cmds.getAttr(ALL + '.' + attr)[0]
                 for attr in ('translate', 'rotate', 'scale')]
    old_rp = cmds.xform(ALL, q=True, ws=True, rp=True)
    old_rpt = cmds.getAttr(ALL + '.rotatePivotTranslate')[0]
    old_local_rp = cmds.getAttr(ALL + '.rotatePivot')[0]

    if max(abs(old_rp[i] - target[i]) for i in range(3)) < 1e-5:
        print('[ALL FootPivot v6] Already aligned:', target)
        return

    # Maya's preserve flag compensates the pivot change without changing
    # the transform's world matrix. No controller curve history is edited.
    cmds.xform(ALL, ws=True, rp=target, preserve=True)
    cmds.refresh(force=True)

    new_rp = cmds.xform(ALL, q=True, ws=True, rp=True)
    pivot_err = max(abs(new_rp[i] - target[i]) for i in range(3))
    matrix_err = max(_matrix_error(before[n], _world_matrix(n))
                     for n in protected)
    after_tr = [cmds.getAttr(ALL + '.' + attr)[0]
                for attr in ('translate', 'rotate', 'scale')]
    channel_err = max(abs(before_tr[j][i] - after_tr[j][i])
                      for j in range(3) for i in range(3))
    if pivot_err > 1e-3 or matrix_err > MATRIX_TOLERANCE or channel_err > 1e-5:
        # Best-effort rollback even if the caller handles the exception.
        cmds.setAttr(ALL + '.rotatePivot', *old_local_rp, type='double3')
        cmds.setAttr(ALL + '.rotatePivotTranslate', *old_rpt, type='double3')
        raise RuntimeError('[ALL FootPivot v6] Validation failed: pivot={}, world={}, channels={}'.format(
            pivot_err, matrix_err, channel_err))

    print('[ALL FootPivot v6] Character-local target:',
          (target_local.x, target_local.y, target_local.z))
    print('[ALL FootPivot v6] World pivot:', target)
    print('[ALL FootPivot v6] World matrix error:', matrix_err)
    print('[ALL FootPivot v6] ALL T/R/S unchanged; existing shape history untouched')


def bake_to_all():




    """

    任意Pivotによる現在の変換を

    ALL_animへ移管する。




    Pivot Rotate -> 0

    ALL World Pose -> 維持

    ALL Scale -> 2

    """




    _exists(ALL)

    _exists(PIVOT)

    _exists(SYSTEM)




    print(

        "\n"

        + "=" * 70

    )




    print(

        "[DIANA] PIVOT -> ALL BAKE"

    )




    print(

        "=" * 70

    )




    before_world = _world_matrix(

        ALL

    )




    print(

        "[DIANA] ALL before:",

        _matrix_position(

            before_world

        )

    )




    cmds.undoInfo(

        openChunk=True,

        chunkName="Diana_Pivot_To_ALL"

    )




    success = False




    try:




        # ----------------------------------------------------

        # ALL T/Rの既存入力を解除

        # ----------------------------------------------------




        _disconnect_all_tr_inputs()




        # ----------------------------------------------------

        # Pivot Rotateを0へ

        # ----------------------------------------------------




        cmds.setAttr(

            PIVOT + ".rotate",

            0.0,

            0.0,

            0.0,

            type="double3"

        )




        cmds.refresh(

            force=True

        )




        # ----------------------------------------------------

        # ALLのWorld Poseを復元

        # ----------------------------------------------------




        _set_world_matrix(

            ALL,

            before_world

        )




        _ensure_scale()




        cmds.refresh(

            force=True

        )




        # ----------------------------------------------------

        # Validate

        # ----------------------------------------------------




        after_world = _world_matrix(

            ALL

        )




        error = _matrix_error(

            before_world,

            after_world

        )




        print(

            "[DIANA] Matrix Error:",

            error

        )




        if error > MATRIX_TOLERANCE:




            raise RuntimeError(

                "Pivot -> ALL matrix validation failed. "

                "Error = {}".format(

                    error

                )

            )




        # v10: RepeatBake cleanup.
        # diana_pivot_v3 synchronizes SYSTEM.rotatePivot with preserve=True.
        # When Pivot rotation is baked back to zero Maya can leave a temporary
        # translation in SYSTEM.rotatePivotTranslate.  If that compensation is
        # carried into the next transfer, the second and later cycles drift.
        #
        # ALL.rotatePivotTranslate is part of Diana's original rig and MUST NOT
        # be cleared.  We clear only SYSTEM.rpt, then immediately restore the
        # already-baked ALL world matrix so the visible/body pose does not move.
        rpt_plug = SYSTEM + ".rotatePivotTranslate"

        if cmds.listRelatives(SYSTEM, parent=True):
            raise RuntimeError("RepeatBake: SYSTEM must be world-root")
        if cmds.listConnections(rpt_plug, source=True, destination=False):
            raise RuntimeError("RepeatBake: SYSTEM.rpt has incoming connection")
        if any(cmds.getAttr(rpt_plug + axis, lock=True) for axis in "XYZ"):
            raise RuntimeError("RepeatBake: SYSTEM.rpt is locked")

        system_rot = cmds.getAttr(SYSTEM + ".rotate")[0]
        pivot_rot = cmds.getAttr(PIVOT + ".rotate")[0]
        if max(abs(v) for v in system_rot + pivot_rot) > 1e-5:
            raise RuntimeError(
                "RepeatBake requires neutral SYSTEM/PIVOT rotations: "
                "SYSTEM={}, PIVOT={}".format(system_rot, pivot_rot)
            )

        rpt_before = cmds.getAttr(rpt_plug)[0]
        baked_world = _world_matrix(ALL)
        foot_local_before = {
            n: (cmds.getAttr(n + ".translate")[0],
                cmds.getAttr(n + ".rotate")[0])
            for n in (LEFT_FOOT, RIGHT_FOOT)
        }

        if max(abs(v) for v in rpt_before) > 1e-10:
            cmds.setAttr(rpt_plug, 0.0, 0.0, 0.0, type="double3")
            cmds.refresh(force=True)

            # Bake the removed parent-space compensation into ALL itself.
            _set_world_matrix(ALL, baked_world)
            _ensure_scale()
            cmds.refresh(force=True)

        final_world = _world_matrix(ALL)
        repeat_error = _matrix_error(baked_world, final_world)
        local_error = max(
            abs(a - b)
            for n in (LEFT_FOOT, RIGHT_FOOT)
            for before, after in zip(
                foot_local_before[n],
                (cmds.getAttr(n + ".translate")[0],
                 cmds.getAttr(n + ".rotate")[0])
            )
            for a, b in zip(before, after)
        )
        rpt_after = cmds.getAttr(rpt_plug)[0]

        if repeat_error > MATRIX_TOLERANCE or local_error > MATRIX_TOLERANCE:
            raise RuntimeError(
                "RepeatBake validation failed: world={}, IK local={}".format(
                    repeat_error, local_error
                )
            )

        if max(abs(v) for v in rpt_after) > 1e-7:
            raise RuntimeError(
                "RepeatBake failed to clear SYSTEM.rpt: {}".format(rpt_after)
            )

        print("[DIANA RepeatBake v10] SYSTEM.rpt before:", rpt_before)
        print("[DIANA RepeatBake v10] SYSTEM.rpt after:", rpt_after)
        print("[DIANA RepeatBake v10] ALL world error:", repeat_error)
        print("[DIANA RepeatBake v10] Foot IK local channels unchanged")
        print("[DIANA RepeatBake v10] ALL.rotatePivotTranslate untouched")

        success = True




        print(

            "[DIANA] Pivot Rotate:",

            cmds.getAttr(

                PIVOT + ".rotate"

            )[0]

        )




        print(

            "[DIANA] ALL Translate:",

            cmds.getAttr(

                ALL + ".translate"

            )[0]

        )




        print(

            "[DIANA] ALL Rotate:",

            cmds.getAttr(

                ALL + ".rotate"

            )[0]

        )




        print(

            "[DIANA] ALL Scale:",

            cmds.getAttr(

                ALL + ".scale"

            )[0]

        )




        print(

            "\n[DIANA] Pivot -> ALL complete."

        )




    except Exception:




        cmds.undoInfo(

            closeChunk=True

        )




        cmds.undo()




        raise




    finally:




        if success:




            cmds.undoInfo(

                closeChunk=True

            )




# ============================================================

# ALL -> PIVOT

# ============================================================

def return_diana():




    """

    Pivot -> ALL Bake の逆処理。




    ALLへBakeされた変換をPivot側へ戻し、

    Animator ControlのPoseを保護しながら

    Dianaを通常状態へ復帰する。




    Pose Protection

    ----------------




    COG:

        Local Translate / Rotate を保存・復元する。




        COGには独自のrotatePivotが存在するため、

        World Matrixを直接書き戻してはいけない。




        cmds.xform(..., ws=True, matrix=...)

        をCOGに対して実行すると、

        MayaがrotatePivotTranslateを補償値として

        書き換える場合がある。




    Legs:

        L Foot

        R Foot




        World Matrixを保存・復元する。




    Arms:

        FKIK >= 0.5 の場合のみ




        Hand IK

        Elbow PV




        World Matrixを保存・復元する。




    Safety:

        COGの




            rotatePivot

            rotatePivotTranslate




        が処理前後で変化していないことを検証する。




    NOTE:

        ALL T/R = 0 の場合でも処理を中断しない。

    """




    # ========================================================

    # REQUIRED NODES

    # ========================================================




    for node in [

        ALL,

        PIVOT,

        SYSTEM,

        COG,

        LEFT_FOOT,

        RIGHT_FOOT,

    ]:




        _exists(

            node

        )




    print(

        "\n"

        + "=" * 70

    )




    print(

        "[DIANA] ALL -> PIVOT RETURN"

    )




    print(

        "=" * 70

    )




    # ========================================================

    # ALL STATE

    #

    # ALL T/R = 0 でも処理を続行する。

    # ここでは診断表示のみ。

    # ========================================================




    all_t = cmds.getAttr(

        ALL + ".translate"

    )[0]




    all_r = cmds.getAttr(

        ALL + ".rotate"

    )[0]




    print(

        "[DIANA] ALL Translate:",

        all_t

    )




    print(

        "[DIANA] ALL Rotate:",

        all_r

    )




    # ========================================================

    # WORLD PROTECTED CONTROLS

    #

    # IMPORTANT:

    # COGはここに含めない。

    #

    # COGへWorld Matrixを書き戻すと、

    # rotatePivotTranslateが変化する可能性がある。

    # ========================================================




    targets = _get_animator_targets()




    print(

        "\n[DIANA] World protected controls:"

    )




    for node in targets:




        print(

            "   ",

            node

        )




    # ========================================================

    # COG LOCAL POSE SAVE

    #

    # COGはWorld Matrixではなく

    # Animator ChannelのLocal T/Rを保存する。

    # ========================================================




    cog_local_t = cmds.getAttr(

        COG + ".translate"

    )[0]




    cog_local_r = cmds.getAttr(

        COG + ".rotate"

    )[0]




    print(

        "\n[DIANA] Saved COG Local T:",

        cog_local_t

    )




    print(

        "[DIANA] Saved COG Local R:",

        cog_local_r

    )




    # ========================================================

    # COG PIVOT STATE SAVE

    #

    # 処理によって内部Pivot補償値が

    # 変化していないことを後で検証する。

    # ========================================================




    cog_rotate_pivot = cmds.getAttr(

        COG + ".rotatePivot"

    )[0]




    cog_rotate_pivot_translate = cmds.getAttr(

        COG + ".rotatePivotTranslate"

    )[0]




    print(

        "[DIANA] Saved COG Rotate Pivot:",

        cog_rotate_pivot

    )




    print(

        "[DIANA] Saved COG Rotate Pivot Translate:",

        cog_rotate_pivot_translate

    )




    # ========================================================

    # WORLD POSE SAVE

    #

    # Foot / IK Hand / Elbow PV

    # ========================================================




    saved_world = {

        node: _world_matrix(node)

        for node in targets

    }




    # ========================================================

    # ALL WORLD MATRIX SAVE

    # ========================================================




    all_world = _world_matrix(

        ALL

    )




    # ========================================================

    # ALL WORLD ROTATION -> PIVOT ROTATION

    # ========================================================




    pivot_rotation = _rotation_from_matrix(

        all_world

    )




    print(

        "\n[DIANA] Reverse Pivot Rotation:",

        pivot_rotation

    )




    # ========================================================

    # UNDO

    # ========================================================




    cmds.undoInfo(

        openChunk=True,

        chunkName="Diana_ALL_To_Pivot"

    )




    success = False




    try:




        # ====================================================

        # 1. ALLを通常値へ

        # ====================================================




        cmds.setAttr(

            ALL + ".translate",

            0.0,

            0.0,

            0.0,

            type="double3"

        )




        cmds.setAttr(

            ALL + ".rotate",

            0.0,

            0.0,

            0.0,

            type="double3"

        )




        _ensure_scale()




        cmds.refresh(

            force=True

        )




        # ====================================================

        # 2. ALL RotationをPivotへ逆移管

        # ====================================================




        cmds.setAttr(

            PIVOT + ".rotate",

            pivot_rotation[0],

            pivot_rotation[1],

            pivot_rotation[2],

            type="double3"

        )




        cmds.refresh(

            force=True

        )




        # ====================================================

        # 3. WORLD PROTECTED CONTROLS RESTORE

        #

        # Foot / IK Hand / Elbow PV

        #

        # COGには絶対にWorld Matrixを書かない。

        # ====================================================




        for node in targets:




            _set_world_matrix(

                node,

                saved_world[node]

            )




        cmds.refresh(

            force=True

        )




        # ====================================================

        # 4. COG LOCAL POSE RESTORE

        #

        # World MatrixではなくLocal T/Rを戻す。

        #

        # rotatePivot

        # rotatePivotTranslate

        #

        # には触らない。

        # ====================================================




        cmds.setAttr(

            COG + ".translate",

            cog_local_t[0],

            cog_local_t[1],

            cog_local_t[2],

            type="double3"

        )




        cmds.setAttr(

            COG + ".rotate",

            cog_local_r[0],

            cog_local_r[1],

            cog_local_r[2],

            type="double3"

        )




        cmds.refresh(

            force=True

        )




        # ====================================================

        # 5. WORLD POSE VALIDATION

        # ====================================================




        worst_error = 0.0

        worst_node = None




        for node in targets:




            actual = _world_matrix(

                node

            )




            error = _matrix_error(

                saved_world[node],

                actual

            )




            print(

                "[DIANA] World Pose Error {}: {}".format(

                    node,

                    error

                )

            )




            if error > worst_error:




                worst_error = error

                worst_node = node




        print(

            "[DIANA] Reverse pose error:",

            worst_error

        )




        if worst_error > MATRIX_TOLERANCE:




            raise RuntimeError(

                "Reverse pose validation failed. "

                "{} error = {}".format(

                    worst_node,

                    worst_error

                )

            )




        # ====================================================

        # 6. COG LOCAL POSE VALIDATION

        # ====================================================




        after_cog_t = cmds.getAttr(

            COG + ".translate"

        )[0]




        after_cog_r = cmds.getAttr(

            COG + ".rotate"

        )[0]




        cog_t_error = max(

            abs(a - b)

            for a, b in zip(

                cog_local_t,

                after_cog_t

            )

        )




        cog_r_error = max(

            abs(a - b)

            for a, b in zip(

                cog_local_r,

                after_cog_r

            )

        )




        print(

            "[DIANA] COG Local T Error:",

            cog_t_error

        )




        print(

            "[DIANA] COG Local R Error:",

            cog_r_error

        )




        if (

            cog_t_error > 0.000001

            or

            cog_r_error > 0.000001

        ):




            raise RuntimeError(

                "COG local pose validation failed. "

                "T error = {}, R error = {}".format(

                    cog_t_error,

                    cog_r_error

                )

            )




        # ====================================================

        # 7. COG PIVOT STATE VALIDATION

        #

        # 今回の不具合に対するSafety。

        #

        # 正常値をハードコードするのではなく、

        # 「処理前後で変化していない」

        # ことを保証する。

        # ====================================================




        after_cog_rotate_pivot = cmds.getAttr(

            COG + ".rotatePivot"

        )[0]




        after_cog_rotate_pivot_translate = cmds.getAttr(

            COG + ".rotatePivotTranslate"

        )[0]




        cog_rp_error = max(

            abs(a - b)

            for a, b in zip(

                cog_rotate_pivot,

                after_cog_rotate_pivot

            )

        )




        cog_rpt_error = max(

            abs(a - b)

            for a, b in zip(

                cog_rotate_pivot_translate,

                after_cog_rotate_pivot_translate

            )

        )




        print(

            "[DIANA] COG Rotate Pivot Error:",

            cog_rp_error

        )




        print(

            "[DIANA] COG Rotate Pivot Translate Error:",

            cog_rpt_error

        )




        if (

            cog_rp_error > 0.000001

            or

            cog_rpt_error > 0.000001

        ):




            raise RuntimeError(

                "COG pivot state changed during ALL -> Pivot. "

                "RP error = {}, RPT error = {}".format(

                    cog_rp_error,

                    cog_rpt_error

                )

            )




        # ====================================================

        # 8. Pivotを通常回転へ

        #

        # ここは既存仕様を維持。

        # ====================================================




        cmds.setAttr(

            PIVOT + ".rotate",

            0.0,

            0.0,

            0.0,

            type="double3"

        )




        cmds.refresh(

            force=True

        )




        # ====================================================

        # 9. COG PIVOT FINAL CHECK

        #

        # Pivotを0へ戻した後にも、

        # COG内部Pivot値が変化していないことを確認。

        # ====================================================




        final_cog_rotate_pivot = cmds.getAttr(

            COG + ".rotatePivot"

        )[0]




        final_cog_rotate_pivot_translate = cmds.getAttr(

            COG + ".rotatePivotTranslate"

        )[0]




        final_cog_rp_error = max(

            abs(a - b)

            for a, b in zip(

                cog_rotate_pivot,

                final_cog_rotate_pivot

            )

        )




        final_cog_rpt_error = max(

            abs(a - b)

            for a, b in zip(

                cog_rotate_pivot_translate,

                final_cog_rotate_pivot_translate

            )

        )




        print(

            "[DIANA] Final COG Rotate Pivot Error:",

            final_cog_rp_error

        )




        print(

            "[DIANA] Final COG Rotate Pivot Translate Error:",

            final_cog_rpt_error

        )




        if (

            final_cog_rp_error > 0.000001

            or

            final_cog_rpt_error > 0.000001

        ):




            raise RuntimeError(

                "COG pivot state changed after Pivot reset. "

                "RP error = {}, RPT error = {}".format(

                    final_cog_rp_error,

                    final_cog_rpt_error

                )

            )




        # ====================================================

        # 10. SCALE GUARANTEE

        # ====================================================




        _ensure_scale()




        # ====================================================

        # FINAL STATUS

        # ====================================================




        print(

            "\n[DIANA] FINAL"

        )




        print(

            "[DIANA] ALL T:",

            cmds.getAttr(

                ALL + ".translate"

            )[0]

        )




        print(

            "[DIANA] ALL R:",

            cmds.getAttr(

                ALL + ".rotate"

            )[0]

        )




        print(

            "[DIANA] ALL Scale:",

            cmds.getAttr(

                ALL + ".scale"

            )[0]

        )




        print(

            "[DIANA] Pivot R:",

            cmds.getAttr(

                PIVOT + ".rotate"

            )[0]

        )




        print(

            "[DIANA] COG T:",

            cmds.getAttr(

                COG + ".translate"

            )[0]

        )




        print(

            "[DIANA] COG R:",

            cmds.getAttr(

                COG + ".rotate"

            )[0]

        )




        print(

            "[DIANA] COG Rotate Pivot:",

            cmds.getAttr(

                COG + ".rotatePivot"

            )[0]

        )




        print(

            "[DIANA] COG Rotate Pivot Translate:",

            cmds.getAttr(

                COG + ".rotatePivotTranslate"

            )[0]

        )




        print(

            "[DIANA] L Foot T:",

            cmds.getAttr(

                LEFT_FOOT + ".translate"

            )[0]

        )




        print(

            "[DIANA] R Foot T:",

            cmds.getAttr(

                RIGHT_FOOT + ".translate"

            )[0]

        )




        # ----------------------------------------------------
        # RepeatRestore v3: clear accumulated SYSTEM pivot compensation.
        # The original Diana scene has SYSTEM.rpt ~= (0,0,0),
        # whereas ALL_anim.rpt is non-zero by design: NEVER reset ALL.rpt.
        # This runs only after the existing pose validation and after
        # PIVOT rotation is zero. Keep IK local channels unchanged.
        # ----------------------------------------------------
        for node in (SYSTEM, ALL, PIVOT):
            rot = cmds.getAttr(node + ".rotate")[0]
            if max(abs(v) for v in rot) > 1e-5:
                raise RuntimeError(
                    "RepeatRestore requires neutral rotations: {} = {}".format(node, rot)
                )
        if cmds.listRelatives(SYSTEM, parent=True):
            raise RuntimeError("RepeatRestore: SYSTEM must be world-root")
        rpt_plug = SYSTEM + ".rotatePivotTranslate"
        if cmds.listConnections(rpt_plug, source=True, destination=False):
            raise RuntimeError("RepeatRestore: SYSTEM.rpt has incoming connection")
        if any(cmds.getAttr(rpt_plug + axis, lock=True) for axis in "XYZ"):
            raise RuntimeError("RepeatRestore: SYSTEM.rpt is locked")
        rpt_before = cmds.getAttr(rpt_plug)[0]
        all_before = _world_matrix(ALL)
        foot_local_before = {
            n: (cmds.getAttr(n + ".translate")[0],
                cmds.getAttr(n + ".rotate")[0])
            for n in (LEFT_FOOT, RIGHT_FOOT)
        }
        # At SYSTEM.rotate == 0, clearing rpt removes only the
        # unwanted accumulated parent-space translation.
        cmds.setAttr(rpt_plug, 0.0, 0.0, 0.0, type="double3")
        cmds.refresh(force=True)
        all_after = _world_matrix(ALL)
        linear_error = max(abs(a-b) for a,b in zip(all_before[:12], all_after[:12]))
        actual_delta = [all_after[i]-all_before[i] for i in (12,13,14)]
        delta_error = max(abs(actual_delta[i]+rpt_before[i]) for i in range(3))
        local_error = max(
            abs(a-b)
            for n in (LEFT_FOOT, RIGHT_FOOT)
            for before, after in zip(
                foot_local_before[n],
                (cmds.getAttr(n + ".translate")[0], cmds.getAttr(n + ".rotate")[0])
            )
            for a,b in zip(before,after)
        )
        if max(linear_error, delta_error, local_error) > MATRIX_TOLERANCE:
            raise RuntimeError(
                "RepeatRestore validation failed: linear={}, delta={}, IK local={}".format(
                    linear_error, delta_error, local_error
                )
            )
        print("[DIANA RepeatRestore v3] SYSTEM.rpt cleared:", rpt_before)
        print("[DIANA RepeatRestore v3] Body world correction:", actual_delta)
        print("[DIANA RepeatRestore v3] Foot IK local channels unchanged")

        success = True




        print(

            "\n[DIANA] ALL -> Pivot complete."

        )




    except Exception:




        cmds.undoInfo(

            closeChunk=True

        )




        cmds.undo()




        raise




    finally:




        if success:




            cmds.undoInfo(

                closeChunk=True

            )
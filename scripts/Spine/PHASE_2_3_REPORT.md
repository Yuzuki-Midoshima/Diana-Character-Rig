# Diana Spine Phase 2/3 implementation report

Date: 2026-11-03  
Scene: `Character_spine37.ma`  
Maya: 2026.3

## Result

The disposable Proxy network passed all 18 automated scenarios across HIP,
LOWER, MIDDLE, and SHOULDER. It was then removed. No production node or
production connection was replaced, disconnected, or driven by the Proxy.

| Metric | Maximum | Tolerance | Result |
| --- | ---: | ---: | --- |
| Matrix component absolute error | `5.6843418860808e-14` | `1.0e-4` | PASS |
| World-position error | `5.90221124448794e-14` | `1.0e-4` | PASS |
| World-scale-2 error | `1.11022302462516e-15` | `1.0e-5` | PASS |
| Rotation error, conservative upper bound | `< 7.0e-12 degrees` | `1.0e-5 degrees` | PASS |
| Production world-matrix restoration error | `0.0` | `1.0e-4` | PASS |

The rotation upper bound follows from the maximum 3x3 matrix component error:
the Frobenius error is at most three times the maximum component error and
`||R1-R2||F = 2*sqrt(2)*sin(theta/2)`. This is deliberately conservative. The
validator now also records a direct scale-normalized angular error on its next
run.

## Implemented Proxy topology

The Proxy uses the real FK order:

```text
HIP_PROXY
  LOWER_PROXY
    MIDDLE_PROXY
      SHOULDER_PROXY
        SHOULDER_PAD_PROXY
          SHOULDER_CTRL_PROXY (original rotate pivot copied)
```

For every part, the desired world matrix is converted back into its Proxy
parent space:

```text
desiredWorld * proxyParent.worldInverseMatrix -> proxy.offsetParentMatrix
```

This preserves a real parent hierarchy without accumulating the parent's IK
world transform a second time.

Mode behavior in the Proxy:

- Mode 0: production FK `worldMatrix` (read-only).
- Mode 1: MODE1 final matrix only; FK rotate values are ignored.
- Mode 2: `FK local delta * MODE1 final`.

The FK delta composeMatrix receives both the production rotate channels and the
production rotateOrder. MODE1 remains the only IK base, so MODE2 swing/twist is
not appended again. SHOULDER jointOrient is already represented in MODE1's
world basis and is stored as Proxy metadata rather than reapplied. Reapplying
the 90-degree jointOrient would double the fixed shoulder basis.

The original shoulder pad TRS and `shoulder_spine_anim` rotate pivot are copied
onto dedicated children below the shoulder Proxy. The pivot remained coherent
through IK translation, bend, twist, and FK additive tests.

## Test coverage

The saved JSON contains per-part matrix, position, scale, pivot, alternate-order,
mode-transition, restore, and cleanup data for:

- Initial IK pose.
- IK HIP X +5 and IK UPPER X +5.
- IK HIP rotation and IK UPPER rotation.
- Spine bend and twist.
- IK mode while a LOWER FK rotation is present (FK correctly ignored).
- LOWER, MIDDLE, and SHOULDER individual FK additions.
- Combined LOWER + MIDDLE FK additions.
- Simultaneous IK movement and FK additions.
- FK/IK/IK+FK mode transitions.

The opposite multiplication order (`MODE1 * FK delta`) differed from the
selected order by as much as `44.2481242738754` matrix units in the test poses.
It is therefore numerically distinguishable and is not interchangeable with
the selected local-delta-first order.

The Proxy's static internal dependency graph was acyclic. The JSON field
`proxy_graph_acyclic` is `true`.

## Mode switching

With zero FK rotation, measured Proxy world-matrix changes were:

| Transition | Maximum difference |
| --- | ---: |
| FK -> IK | `2.23164136059495e-6` |
| IK -> FK | `2.23164136059495e-6` |
| IK -> IK+FK | `3.814697265625e-5` |
| IK+FK -> IK | `3.814697265625e-5` |

All are below the `1.0e-4` tolerance. The residual is caused by switching
between separate production/choice/composeMatrix evaluation paths with the
scene's scale-2 float matrices. It is not consistent with a duplicated IK
rotation, which would produce a pose-sized difference. Automatic snapping was
not implemented.

## Restoration and cleanup

- All tested channel values restored: true.
- Selection restored: true.
- Current time restored: true.
- HIP/LOWER/MIDDLE/SHOULDER production world-matrix restore error: `0.0`.
- Proxy nodes removed: 30.
- Proxy root exists after cleanup: false.
- Remaining `DIANA_SPINE_P23_*` nodes: none.

The Maya scene was not saved.

## Phase 4 integration proposal (not implemented)

Recommended production integration:

1. Add a dedicated follow layer above or parallel to each FK control rather
   than connecting MODE1 directly to an animated FK control's
   `offsetParentMatrix`.
2. Drive that layer with MODE1 converted to the layer's parent space in modes
   1 and 2. Keep mode 0 on the untouched FK hierarchy.
3. Preserve existing FK rotate animation channels as local animator deltas.
4. Replace MODE2 choice inputs with the validated single composition
   `FK local delta * MODE1 final`. Disconnect the present FK-world + swing +
   twist MODE2 input only after recording every existing source/destination.
5. Preserve the existing shoulder joint/pad/control/pivot hierarchy so the
   neck, head, arm spaces, hair, inverseScale, and legacy constraints continue
   reading the same production transforms.

Expected existing connection changes in Phase 4 would be limited to the four
`DIANA_SPINE_DEFORM_{PART}_MODE_CHOICE.input[2]` sources and, if approved, the
new follow layers for visual FK-control following. MODE0 inputs and MODE1
networks should remain unchanged.

Rollback must be manifest-driven: restore the recorded original MODE_CHOICE
input[2] sources, remove only newly registered integration DG nodes/follow
layers, and verify production matrices and connection maps against a pre-build
snapshot. No Phase 4 production change has been made.

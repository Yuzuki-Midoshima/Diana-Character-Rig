# Diana Spine Phase 8 Method Comparison

## Quantitative DOF summary

24出力成分（4点 x 位置3 + Quaternion vector3）に対し、3つの代表姿勢で有限差分Jacobianを計測した。

| Mode | Operation parameters | Total rank | Position rank | Rotation rank | Unreachable components | Redundant parameters |
|---|---:|---:|---:|---:|---:|---:|
| MODE0 independent FK rotate | 12 | 12 | 0 | 12 | 12 | 0 |
| MODE1 IK HIP/UPPER + Twist | 12 | 12 | 11 | 6 | 12 | 0 |
| MODE2 IK + FK rotate | 24 | 23 | 11 | 12 | 1 | 1 |

ランクは直立、前屈、複合回転で同一だった。MODE0の位置ランク0は、Phase 5が `OP_FK_CTRL.rotate` だけを `composeMatrix` へ入力していることと一致する。

## Candidate comparison

| Candidate | Added DOF | Position accuracy | Rotation accuracy | Cycle risk | Animation compatibility | Cost / maintenance | Result |
|---|---:|---|---|---|---|---|---|
| A: MIDDLE position | 3 | Tested poses: about `3.23e-06`; does not cover arbitrary four-point translation | Up to 14 deg remains | Low | Good | Low | Insufficient |
| B: LOWER + MIDDLE position | 6 | Tested poses: about `3.23e-06`; endpoints remain constrained | Up to 14 deg remains | Low | Good | Medium | Insufficient |
| C: independent CV correction | 6 | Smooth internal-position fit; endpoint and rotation components unreachable | No direct rotation correction | Medium; must remain independent of old curve/stretch | Existing IK animation can be retained | High | Insufficient alone |
| D: snap-only per-part correction delta | 24 | Max `3.26e-14` | `0 deg` | Low when downstream-only | Does not rewrite existing IK keys; correction can be keyed separately | Medium | PASS |
| E: MODE2 hybrid FK rotate + position correction | 24 total correction channels | Max `3.26e-14` | `0 deg` | Low when downstream-only | Good for IK+FK, but exposes more animator state | Medium-high | PASS |

MODE2のJacobianランクは23/24なので、局所理論上は1スカラー自由度の追加でフルランクにできる。ただし特異ベクトルの方向は姿勢により変化するため、1軸固定補正は保守性が低い。Dは過剰だが姿勢依存の特異方向を確実に吸収できる。

## FK Translation Delta

実IK姿勢をMODE0 Proxyへ合わせたときのTranslation Delta量:

| Part | Delta magnitude |
|---|---:|
| HIP | 5.999999 |
| LOWER | 3.326757 |
| MIDDLE | 1.653579 |
| SHOULDER | 7.773924 |

4点すべてが非ゼロであり、IK -> FKの一般的な位置保持には4部位すべてのTranslation Deltaが必要である。Full TR Proxyの最大位置誤差は `1.42e-14`、回転誤差は `0 deg`。

## Six-direction residual with the selected proxy scheme

| Direction | Selected scheme | Max position | Max rotation |
|---|---|---:|---:|
| FK -> IK | D | `3.26e-14` | `0 deg` |
| IK -> FK | FK Full TR Delta | `1.42e-14` | `0 deg` |
| FK -> IK+FK | E | `3.26e-14` | `0 deg` |
| IK+FK -> FK | FK Full TR Delta | `1.42e-14` | `0 deg` |
| IK -> IK+FK | zero-delta direct switch | `3.05e-05` | `0 deg` |
| IK+FK -> IK | D bake correction | `3.26e-14` | `0 deg` |

これらはProxy出力の結果であり、production接続は行っていない。


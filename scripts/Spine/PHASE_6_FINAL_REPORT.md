# Diana Spine Phase 6 Final Report

## Status

**COMPLETE** — Maya 2026 Standaloneの別名検証シーンでPhase 5 / 5-Bを構築し、モード切替、操作性、72フレームのアニメーション、全身影響、再実行、保存・再読込、ロールバックに合格した。

`Character_spine37.ma`は変更していない。検証シーンは最終的にロールバック済みである。

## Mode switching and Snap decision

非ニュートラルなIK/FK入力を両方に与え、最終Spine変形ProxyのworldMatrixを比較した。

| Transition | Max matrix/position difference | Max rotation difference |
|---|---:|---:|
| FK -> IK | 182.446375 | 65.807589 deg |
| IK -> FK | 182.446375 | 65.807589 deg |
| FK -> IK+FK | 182.446375 | 65.174151 deg |
| IK -> IK+FK, FK delta present | 0.345356 | 9.999998 deg |
| IK+FK -> FK | 182.446375 | 65.174151 deg |
| IK+FK -> IK, FK delta present | 0.345356 | 9.999999 deg |

FK追加回転が0の場合、IK -> IK+FKとIK+FK -> IKの最大行列誤差はともに `3.0517578125e-05`で、許容値 `1e-4` 以内であった。

結論:

- FK <-> IK、FK <-> IK+FK: ポーズ維持Snapが必要
- IK <-> IK+FK: FK deltaが0ならSnap不要
- IK <-> IK+FK: FK deltaがある場合の姿勢変化は意図された追加回転

推奨Snap方式は、切替前のHIP/LOWER/MIDDLE/SHOULDER最終ワールド行列を保存し、切替先のIKコントローラーまたは独立操作FKローカルdeltaを解いてから `Terminal.Spine_Mode` を切り替えるコマンド型処理である。本Phaseでは本番Snapは実装していない。

## FK controls

- MODE0: FK操作による最終変形量 `0.4499021087`
- MODE1: FK追加回転の最終変形量 `0.0`
- MODE2: FK追加回転の最終変形量 `0.4499021054`
- FK追加回転を0へ戻した後のIK姿勢復元誤差: `0.0`

## Animation validation

1〜72フレームで以下をキー化した。

- IK HIP / IK UPPER移動とIK回転
- 実際のHip/Chest Twist入力
- 独立操作FK追加回転
- Spine Mode切替
- 左右腕FK回転
- 左右肘IK移動
- 手IK World / Body Space切替

結果:

- 検証フレーム: 72
- NaN / Inf / 無効行列: 0
- モード切替フレームを除く90度超の回転反転: 0
- 新規DG循環ノード: 0

## Full-body and data protection

- 左右鎖骨、腕FK、肘IK、手IK Space Switch: PASS
- 首、頭、髪の保護接続: 保存・再読込後も一致
- Head Space / Arm Space Switch接続: 一致
- Spine/Back関連skinCluster: geometry / influence一致
- 武器・装備関連Transform: 39ノードを監査、親子・接続一致
- 最終ロールバックworldMatrix最大誤差: `3.931787105670992e-05`
- Phase 5 / Phase 5-B残存ノード: 0

## DG-cycle interpretation

循環はプラグ文字列だけでなく、循環に新規参加したDGノードで比較した。保存・再読込により既存Bow/String循環ノード内で列挙プラグが増える場合は、「既存循環の列挙展開」として別記録した。最終実行ではこの展開も0、新規循環ノードも0であった。

## Save, reload, rollback

- Maya 2026保存・再読込: PASS
- Phase 6アニメーションキー削除: PASS
- Phase 5-B rollback: PASS
- Phase 5 rollback: PASS
- 元階層、接続、skinCluster、装備: PASS
- 元シーン変更: なし

## Scene warnings

元シーン由来の `nodeGraphEditorInfo`、Bow UI `intValue=None`、UUID重複警告は継続している。Phase 6の新規循環や検証失敗には結びついていない。


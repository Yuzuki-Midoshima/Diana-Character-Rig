# Diana Spine Phase 9 最終レポート

## 結果

**COMPLETE** — Maya 2026 Standalone上の別名検証シーンで、Phase 5 / 5-BとPhase 9を構築し、Snap、継続操作、73フレーム、保存・再読込、再実行安全性、ロールバックまで合格した。元の `Character_spine37.ma` は保存・変更していない。

## 実装

- HIP / LOWER / MIDDLE / SHOULDERの各MODE入力に、TR CorrectionをMODE_CHOICE直前で合成する。
- Matcherは切替前の4点worldMatrixを保存し、切替先Correctionをゼロ評価した後、`targetWorld * inverse(baseWorld)`を設定する。
- Correctionが既にキー接続されている場合、切替フレームにゼロキーを置いてから再計算する。古いCorrectionを乗算蓄積しない。
- MODE0のCorrectionはPhase 8のFull TR Deltaとして機能する。MODE1 / 2は既存MODE1、IKカーブ、Stretch、LIVE_DRIVERより下流に限定した。
- 腕FKルートは既存の腕MODE_CHOICE（MODE0 identity、MODE1/2 shoulder follow）でも切替差が出るため、同じ下流Correctionを左右腕choice入力へ追加した。腕FKのローカルアニメーションチャンネルは変更しない。
- active modeの非ゼロCorrectionは通常Resetを拒否する。inactive modeは安全にResetでき、force Resetは明示指定時のみ許可する。

## Maya数値検証

許容値は位置 `1e-3`、回転 `1e-3 degree`。2代表姿勢 × 6方向 = 12ケースを検証した。

- 最大位置誤差: `5.90221124448794e-14`
- 最大回転誤差: `1.70754729250319e-06 degree`
- 最大行列誤差: `1.81558881158803e-09`
- 全身Attachment最大行列誤差: `1.70530256582424e-13`
- IK World手コントローラー最大誤差: 許容値内
- 73フレーム、6方向Snap、Snap後操作、複数切替、キー補間: PASS
- 不正行列、90度超の予期しないフレーム間回転反転: 0
- 新規DG循環: 0
- skinCluster、装備接続、保護接続、animationLayer、既存キー: 維持
- 保存・再読込: PASS
- 同一シーン再実行: 重複作成せず安全停止、行列誤差0
- ロールバック: PASS、残存Phase 9ノード0、復元行列最大誤差 `3.93178710567099e-05`

## Correctionライフサイクル

- 初回Snap、Correction保持、Snap後のFK/IK操作、再Snap上書き: PASS
- active non-zero Correctionの非強制Reset拒否: PASS
- inactive Correction Reset: PASS
- Correctionとmodeのキー登録、保存・再読込: PASS

## 保護事項と実行メモ

検証コピーは書込み許可された一時領域の `Character_spine37_PHASE5B_PHASE9_VALIDATION.ma` を使用し、最終状態はロールバック済み。元シーン読込時には既存の `nodeGraphEditorInfo`、Bow UI、UUID警告が出力されたが、Phase 9ノード由来ではなく、検証処理と保存・再読込は完了した。

本番シーンへの反映は行っていない。


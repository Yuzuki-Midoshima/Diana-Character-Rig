# Diana Spine Phase 7 Auto Matcher Report

## Status

**INCOMPLETE** — Auto Matcherコマンド、Undo/失敗復元、キー保護、保存・再読込は実装・検証できたが、6方向すべての許容誤差を満たせないためPhase 7完了扱いにはしない。

`Character_spine37.ma`は変更していない。すべて別名検証シーンで実行し、最後にPhase 5 / 5-Bをロールバックした。

## Implementation

`diana_spine_phase7_matcher.match(target_mode)` は次を行う。

- 切替前の4つの最終Spine変形Proxy行列を保存
- FK側は4つの独立操作FK local rotateだけを操作
- IK側は既存IK HIP / UPPERのTRと実Twist入力だけを操作
- 位置とQuaternion回転残差を有限差分Jacobianで最小化
- 既存animCurveがある場合は現在フレームのキーだけを設定
- 単一Undoチャンク
- 許容誤差超過または例外時は属性、キー、モードを操作前へ復元
- 同一モード指定は処理せず成功する冪等パス

許容値は位置 `0.05`、回転 `0.1 degree` とした。

## Numeric result

2つの非ニュートラル姿勢に対し、6方向12ケースを検証した。

| Direction | Pose 0 max position / rotation | Pose 1 max position / rotation | Result |
|---|---:|---:|---|
| FK -> IK | 0.7157 / 6.9027 deg | 0.7642 / 8.1417 deg | FAIL |
| IK -> FK | 12.4293 / 0 deg | 8.0000 / 0 deg | FAIL |
| FK -> IK+FK | 0.7157 / 6.9027 deg | 0.7642 / 8.1417 deg | FAIL |
| IK+FK -> FK | 12.4293 / 0 deg | 8.0000 / 0 deg | FAIL |
| IK -> IK+FK, zero FK delta | < 0.0001 / 0 deg | < 0.0001 / 0 deg | PASS |
| IK+FK -> IK, non-zero FK delta bake | 0.7309 / 6.9010 deg | 0.7452 / 8.1190 deg | FAIL |

12ケース中2ケースが合格、10ケースが不合格である。不合格時はすべて操作前値へ自動復元した。

## Root causes

### IK -> FK / IK+FK -> FK

分類: **FK rotation-only freedom limitation**

Phase 5 MODE0は次の構成である。

```text
OP_FK_CTRL.rotate -> LOCAL_DELTA_CM.inputRotate
LOCAL_DELTA_CM.outputMatrix x production_FK.worldMatrix -> MODE0 final
```

操作FKのtranslateはMODE0行列に入力されていない。そのためIKで移動したHIP/LOWER/MIDDLE/SHOULDERの位置を、FK local rotateだけで再現できない。jointOrientや行列順序の誤りではなく、MODE0の表現自由度によるものである。

### FK -> IK / FK -> IK+FK / non-zero IK+FK -> IK

分類: **IK freedom limitation**

独立な4点FK回転が作る姿勢は、既存IK HIP/UPPERと2つのTwist入力の制約されたカーブ変形で完全には再現できない。24反復の数値最小化後も許容値を超えた。

## Passed safety checks

- 既存キーの現在フレーム以外を保護: PASS
- Undo / Redo: PASS
- 失敗時の属性・キー・モード復元: PASS
- 新規DG循環ノード: 0
- IK -> IK+FK zero deltaのAttachment最大行列誤差: `1.3627e-04` 以下
- 保存・再読込: PASS
- Phase 5 / 5-B rollback: PASS
- 元シーン変更: なし

## Required design change before completion

6方向完全Snapを必須とする場合、最小変更案は以下である。

1. MODE0操作行列に、専用のFK translation deltaを追加する。既存production FKを再親子化しない。
2. FK -> IKは近似Snapとして残差をUI表示するか、IKカーブ上にMIDDLE用の追加自由度を設ける。
3. IK+FK -> IKの非ゼロdeltaは、既存IKの可表現範囲に収まる場合のみベイクし、超過時は切替を中止する。

これらはPhase 5変形仕様の変更にあたるため、Phase 7内で無断実施していない。


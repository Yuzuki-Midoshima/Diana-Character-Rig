# Diana Character Rig

![Autodesk Maya 2026](https://img.shields.io/badge/Autodesk%20Maya-2026-0696D7?logo=autodesk&logoColor=white)

![Diana Character Rig](docs/images/main_visual.png)

Autodesk Maya 2026で制作した、オリジナルキャラクター **Diana** のキャラクターリグです。

キャラクター2D原案と、素体をベースとしたモデル制作・リギングを担当しました。

IK / FK、指のSDK制御、リバースフット、武器制御などを実装しています。

特に、操作量が多くなりやすい**手指と武器周辺の操作性**を重点的に設計しました。

手指では一括操作と個別調整を使い分けられる構成を採用し、武器では、Sword / Shield / Bow / Arrowそれぞれに専用のリグを構築し、持ち替えや追従先の切り替えにも対応しています。

また、実際にアニメーション制作で使用しながら操作性を検証し、そこで発生した反復作業や問題をMaya Toolとして切り出すことで**リグだけでなく制作工程そのものの改善**にも取り組みました。

## 目次

- [制作概要](#制作概要)
- [リグ全体・動作デモ](#リグ全体動作デモ)
- [主な機能](#主な機能)
  - [手指のリグ](#手指のリグ)
  - [腕のIK / FK](#腕のik--fk)
  - [Spine・Head・Custom Pivot](#spineスプラインik)
  - [脚のストレッチIK・リバースフット](#脚のストレッチik)
  - [武器リグ](#武器リグ)
- [技術的な設計と工夫](#技術的な設計と工夫)
- [リグからツール開発へ](#リグからツール開発へ)
- [関連ツール](#関連ツール)
- [制作環境・リポジトリ構成](#制作環境リポジトリ構成)
- [使用モデル・公開について](#使用モデル公開について)
- [Portfolio](#portfolio)
- [GitHub](#github)
- [License](#license)

## 制作概要

| 項目 | 内容 |
| --- | --- |
| 作品名 | Diana Character Rig |
| 担当 | キャラクター2D原案 / 素体をベースとしたモデル制作 / リギング / リグシステム設計 / Mayaツール開発 |
| 使用ソフト | Autodesk Maya 2026 |
| 制作目的 | TPSアクションゲームを想定したキャラクターアニメーション・ポージング |
| 使用モデル | Diana（オリジナルキャラクター） |
| 制作時期 | 2026年 |

**設計方針**：
①手指と武器周辺の操作性を重視する ②一括操作と個別調整を使い分ける ③ポーズを維持しながら操作を切り替える ④制作中の課題を再利用できるツールへ発展させる。

---

## リグ全体・動作デモ

![OVERVIEW](docs/images/overview.png)

MODEL/RIG ターンテーブル

![リグ全体](docs/gifs/rig_overview.gif)


![顔](docs/gifs/feicial_overview.gif)

全身のポージングに必要な基本コントローラーに加え、手指・武器などをより柔軟に操作できる仕組みを作成しました。

主な機能は以下の通りです。

* 腕のIK / FK切り替え

* IK / FKポーズマッチ（専用ツール）

* 脚のストレッチIK

* 足のスナップ機能

* Head Local / World Space切り替え

* Custom Pivot（任意回転軸）

* 背骨のスプラインIK

* 揺れ物（バスト・ヒップ）

* リバースフット

内部構造を直接操作しなくても、アニメーションを制作できる構成を目指しました。

---

## 主な機能

### ターミナル

全体の管理をするコントローラーです。

現在は武器・髪の毛のFKコントローラーの表示/非表示を設定できます。

![ターミナル](docs/gifs/terminal.gif)

今後追加する機能などもこちらに追加していく予定です。

---

### フェイシャルリグ | Eyes / Jaw / Tongue

![Facial Controls](docs/images/facial_controls.png)

![Facial Demo](docs/gifs/facial_demo.gif)

目・口・舌に専用のコントローラーを設け、キャラクターの表情や細かな動きを調整できるフェイシャルリグを実装しました。

目元には視線移動、瞬き、笑顔などの制御を用意し、両目の一括操作と左右それぞれの個別調整に対応しています。

口元にはJawコントローラーを設け、開閉や位置・角度の調整が可能です。舌にはFKコントローラーと伸縮制御を実装し、口内の細かな動きを手付けで調整できる構成にしました。

各コントローラーは必要に応じて表示を切り替えられるようにし、通常のボディアニメーション時の視認性にも配慮しています。

---

### 手指のリグ

![手](docs/images/hand.png)

チーム内のアニメーターにヒアリングをしながら進め、Diana Rigでは、特に**手指周辺の操作性**を重点的に設計しています。

ゲームアニメーションでは、手を握る・開くといった大きな動きだけでなく、武器の形状に合わせて指先を細かく調整する必要があります。

そこで、FK/IK切り替えやFKコントローラーとは別に

**「チャネルエディタによる一括操作」と「コントローラーによる一括操作」**

のSDK(セットドリブンキー)両方を用意しました。(詳細は以下に続きます)

どちらもFKコントローラーとの加算併用が可能です。

---

### setting_anim

![手指の操作切り替え](docs/gifs//finger_switch.gif)

手指には複数の操作方法があるため、各手の後ろに配置しているsetting_animというコントローラーから操作状態を切り替えられるようにしています。

内部では`choice`などのUtility Nodeを使用し、操作モードに応じてJointへ渡す値を切り替えています。

```text

SDKからの入力 ────┐

                  ├─ choice ─→ Finger Joint

個別操作からの入力 ─┘

                       ↑

                  操作モード

```

---

### SDKによる一括操作

### fingers_anim

![Finger_SDK](docs/gifs/finger_sdk.gif)

指にはSDKを使用し、複数の関節をまとめて操作できるようにしています。

親指には個別にON/OFF設定があり、OFFの場合はSDKの値が親指にのみ反映されません。これはどちらのSDKにも同様に入れ込んであります。

`Curl`、`Spread`、`Relax`、`Fist`、親指の操作など、使用頻度の高い動きをアトリビュートへまとめることで、各関節を一本ずつ操作する手間を減らしています。

```text

手指のAttribute

      ↓

Set Driven Key

      ↓

各指の回転

      ↓

Finger Joint

```

まずSDKから大まかな手の形を作り、必要な部分だけ個別に調整することを想定しています。

---

### hand_anim

![HAND_SDK](docs/gifs/hand_anim.gif)

finger_animよりも直感的に操作できるコントローラーを追加しました。アニメーターの好みによって使い分けや併用が可能なように選択肢を増やしました。

同一コントローラー内での加算にも対応しています。

上記と同じく、

**一括操作で大きな形を作る → 必要な指だけ細かく調整する**

という流れでポーズを作れるようにしました。

また、こちらも親指には個別にON/OFF設定があり、OFFの場合はSDKの値が親指にのみ反映されません。

---

### FKコントローラー

![FKコントローラー](docs/gifs/fk_ctrl.gif)

一般的な指用のコントローラーです。

各SDKの微調整用として併用も可能です。

重ならず掴みやすいという利点があったためPin型を採用しました。

---

### 腕のIK / FK

![腕のIK FK](docs/gifs/arm_ik_fk.gif)

腕は左右ともIK / FKの切り替えに対応しています。

FKでは肩・肘・手首を回転させてポーズを作成し、IKではHand ControllerとPole Vector Controllerから腕を操作します。

ポーズ合わせには専用マッチャ―を製作しました。

### IK / FKポーズマッチ

![IK FKポーズマッチ](docs/gifs/ik_fk_matching.gif)

IK / FK切り替え時に発生するポーズのズレを減らすため、Controllerの位置・回転を自動的に合わせる**FK / IK Auto Matcher**を制作しました。

```text

現在のポーズ

      ↓

Jointの位置・回転を取得

      ↓

切り替え先Controllerへ反映

      ↓

IK / FK切り替え

```

Diana Rigで使用するためのポーズ合わせから始まり、その後、より汎用的に使用できる独立した**Auto-Macher**へ発展させました。

---

### Spine(スプラインIK)

![Spine](docs/gifs/spine.gif)

背骨にはスプラインIKを使用し、腰から胸部までのシルエットをしなやかに調整できる構成にしています。

---

### Head World Space

![Head World Space](docs/gifs/head_world_space.gif)

頭部の回転にLocal / World Space切り替えを追加しました。

Local Spaceでは首や上半身の回転に頭部が追従し、World Spaceでは上半身を回転させても頭の向きを維持できるようにしています。

これにより、身体を大きくひねる動作や、特定の方向を見続けるモーションでも、頭部の向きを個別に調整する手間を軽減できます。

頭部の位置は身体への追従を維持しながら、回転の基準のみを切り替える構成です。

---

### Custom Pivot

![Custom Pivot Structure](docs/gifs/custom_pivot_structure.gif)

キャラクター全体の回転中心を任意の位置に設定できるCustom Pivot機能を追加しました。

通常のRoot操作では、あらかじめ設定された回転軸を基準にキャラクターが回転します。

しかし、アクション中には接地点や任意の位置を中心として身体を回転させたい場合があります。

そこで、専用コントローラーでPivot位置を指定し、その位置を基準としてキャラクターを回転させられる仕組みを設けました。

これにより、固定された回転軸だけでは表現しにくい動きにも対応でき、アニメーション制作時の操作自由度を高めています。

---

### Pivot Transfer Tool

![UI](docs/images/ui.png)

ALL → Pivot

![ALL→Pivot](docs/gifs/ALL-Pivot.gif)

Pivot → ALL

![Pivot→ALL](docs/gifs/Pivot-ALL.gif)

Custom Pivotと通常のALLコントローラー間で、キャラクターのポーズを維持しながら操作を切り替えるための**Pivot Transfer Tool**を制作しました。

任意Pivotによる回転操作では、通常のALL操作と異なる回転中心を使用するため、操作を戻す際にコントローラーのTransformを単純に初期化すると、キャラクターのポーズが崩れる問題がありました。

そこで、現在のワールド空間上の位置・回転を取得し、切り替え先のコントローラーへ必要なTransformを再計算して反映する仕組みを実装しました。

ツールには以下の2つの機能を用意しています。

- **ALL → Pivot**：通常のALL操作から任意Pivot操作へ移行

- **Pivot → ALL**：任意Pivot操作から通常のALL操作へ復帰

特に、PivotからALLへ戻す際には、COGや脚IKなどの操作状態を考慮し、キャラクターのポーズが崩れないようにしています。

これにより、アニメーション制作中でも必要に応じて回転中心を切り替え、通常の操作へ戻すことができます。

任意Pivotの自由度だけでなく、**操作の切り替えによって既存のポーズが失われないこと**を重視して設計しました。

---

### 揺れ物

![Ｂust/Ｈip](docs/gifs/bust_hip.gif)

コントローラーの可動範囲に制限を設けることで、極端な操作を行っても形状が破綻しにくい構成にしています。

柔らかい表現ができるようにウェイト調整には時間をかけて何度も動かしながら確認しました。

手付けでも自然な揺れを表現できるよう、バスト・ヒップにはそれぞれ2本のJointを配置しています。

---

### 脚のストレッチIK

左 → 適用前 / 右 → 適用後

![Leg Stretch IK](docs/gifs/leg_stretch_ik.gif)

左右の脚に、IKコントローラーとの距離に応じて関節を伸長させるストレッチIKを実装しました。

通常のIKでは脚の長さが固定されているため、IKコントローラーを可動範囲の外へ移動すると、足先がコントローラーに届かなくなります。

そこで、distanceBetweenで股関節側の参照位置と足IKターゲット間の距離を取得し、脚の初期長との比率から伸長倍率を計算する構成にしました。

内部では以下のUtility Nodeを使用しています。

distanceBetween：股関節からIKターゲットまでの距離を計測

multiplyDivide：Global Scaleの補正と伸長倍率の計算

condition：通常の脚長を超えた場合のみ伸長

clamp：最大伸長倍率を制限

blendColors：通常の脚長とストレッチ結果をブレンド

Hip REF ────────┐

                ├─ distanceBetween

Foot Target REF ┘

                       ↓

              Global Scale補正

                       ↓

                 初期長と比較

                       ↓

                   condition

                       ↓

              MaxStretch / clamp

                       ↓

             Stretch / blendColors

                       ↓

                multiplyDivide

                  ↙        ↘

             Knee Joint  Ankle Joint

足IKコントローラーにはStretchとMaxStretchを用意しています。

Stretchは0〜1の連続値で伸長の有効度を調整でき、MaxStretchでは最大伸長倍率を設定できます。

これにより、通常のIK操作とストレッチを使い分けながら、大きく脚を伸ばすポージングにも対応できるようにしました。

---

### 足のスナップ機能

![Foot IK Snap](docs/gifs/foot_snap.gif)

足IKコントローラーを現在の足首位置へ自動的に合わせる**スナップ機能**を追加しました。

勿論、オフにして通常のIKコントローラーのように使用も可能です。

通常、足IKコントローラーと実際の足首位置が離れている場合、コントローラーを手動で移動・調整する必要があります。

そこで、現在の足首の位置を基準に、IKコントローラーを自動配置する仕組みを実装しました。

左右の足IKコントローラーには、それぞれ`SnapToFoot`属性を用意しています。

```text

現在の足首位置

      ↓

足首のTransformを取得

      ↓

IKコントローラーの位置を調整

      ↓

足首とIKコントローラーの位置合わせ

```

これにより、足のポーズを調整する際の手動操作を減らし、アニメーション制作時の作業効率を高めています。

特に、脚のポーズを大きく変更した後や、IKコントローラーの位置を再調整する場面での使用を想定しています。

---

### リバースフット

![Reverse Foot](docs/gifs/reverse_foot.gif)

足には**リバースフット**を実装しています。

踵・つま先などを基準とした回転を操作でき、歩行・走行・踏み込みなどのアニメーションを作りやすい構成にしています。

TPSアクションゲームのためモーションの自由度を上げたいと思い取り入れました。

---

### 武器リグ

Dianaが使用する

**Sword / Shield / Bow & Arrow**

には、それぞれ専用のリグを構築しています。

単純に武器を手へ固定するのではなく、アニメーション中の**持ち替え・追従先の変更・位置調整**まで想定した構成です。

---

### 武器の追従構造

左右の手には武器を追従させるためのSocketを配置しています。

武器をHand Jointへ直接接続するのではなく、武器側にFollow Groupを設け、そのGroupを左右のSocketへ追従させています。

```text

右手Socket ───┐

              ├─ Parent Constraint

左手Socket ───┘

                     ↓

               Follow Group

                     ↓

                  武器Rig

```

これにより、武器自体のリグ構造を変更せずに追従先を切り替えられます。

---

### 剣のリグ

剣には専用のコントローラーとFollow Groupを用意しています。

キャラクターの手へ直接固定するのではなく、左右の手に配置したSocketを介して追従させています。

---

### 剣の持ち替え

![剣の持ち替え](docs/gifs/sword_switch.gif)

Swordでは`weaponSpace` Attributeから現在の持ち手を変更します。

内部では`condition` Nodeを使用し、アトリビュートの値に応じてParent Constraintのウェイトを切り替えています。

```text

weaponSpace

     ↓

 condition

   ↙      ↘

右手Weight  左手Weight

   ↘      ↙

Parent Constraint

      ↓

Sword Follow Group

```

**「Attributeを変更するだけで左右の追従先が切り替わる」**

という操作の裏側を、ノードとコンストレインによって構成しています。

---

### 盾のリグ

![盾](docs/images/shield.png)

Shieldにも専用のControllerとFollow Groupを用意しています。

Swordと同様に左右の手への追従を切り替えられる構成とし、装備状態やアニメーションに応じて持ち手を変更できます。

剣と盾で共通した考え方を使用することで、武器ごとに大きく異なる操作方法にならないようにしています。

---

### 弓・矢のリグ

BowはSwordやShieldと比較して操作対象が多いため、**弓本体・矢を分けて制御**しています。

弓本体には持ち手を切り替える仕組みを持たせ、StringとArrowにはそれぞれ専用のControllerや追従構造を用意しています。

![弓](docs/images/bow.png)

弓本体もFollow Groupを介して左右の手へ追従させることで、リグ自体のHierarchyを変更せずに持ち手を切り替えられるようにしています。

### Equipment Manager

![Equipment Manager](docs/gifs/equipment_manager.gif)

武器リグを実際にアニメーションで使用すると、持ち替えや追従先の変更に伴って複数の操作が発生します。

そこで、武器操作で繰り返し発生する処理を専用の**Equipment Manager**としてツール化しました。

Sword / Shield / Bowなどの持ち替えやFollow操作をまとめ、アニメーション時の装備制御を効率化しています。

リグそのものを置き換えるのではなく、Diana Rigに構築したAttributeやConstraintを利用しながら、アニメーターが行う操作手順をまとめるためのツールとして制作しています。

詳細は以下をご覧ください。

![EM](docs/images/EM.png)

【 https://github.com/Yuzuki-Midoshima/Equipment-Manager 】

【 https://www.vivivit.com/works/1158926 】

---

## 技術的な設計と工夫

### ツール制作

Diana Rigの制作で発生したController作成・調整作業を、他のリグでも再利用できる形へ発展させています。

---

## リグからツール開発へ

Diana Rigは、リグを完成させて終わりではなく、実際にアニメーションで使用しながら改善を続けました。

```text

キャラクターリグ制作

        ↓

アニメーションで検証

        ↓

問題・反復作業を発見

        ↓

リグ構造を改善

        ↓

必要な処理をツール化

        ↓

再度アニメーションで検証

```

この制作から、

* Equipment Manager

* Controller Shape Library

* Rig-Ctrl-Shape-Tool

* Finger SDK Tool

* FK / IK Auto Matcher

* FK-Builder

などのMayaツールへ発展させています。

一体のキャラクターを動かすためのリグだけでなく、**制作中に見つけた課題を、次の制作でも再利用できる仕組みに変えること**を意識して制作しました。

---

## 関連ツール

### Equipment Manager

![Equipment Manager](docs/gifs/equipment_manager.gif)

武器の装備制御を補助するDiana専用のアニメーション補助ツールです。

[GitHub](https://github.com/Yuzuki-Midoshima/Equipment-Manager)

### Rig-Ctrl-Shape-Tool

![Rig-Ctrl-Shape-Tool](docs/gifs/Rig-Ctrl-Shape-Tool.gif)

コントローラーの接続を変えず見た目だけを変更するツールです。形・色の変更やコントローラーのコピー＆ペーストができます。

[GitHub](https://github.com/Yuzuki-Midoshima/Rig-Ctrl-Shape-Tool)

### Finger SDK Tool

![Finger SDK Tool](docs/gifs/finger_sdk_tool.gif)

Finger SDKの保存・再構築・修正を補助するツールです。JSONで管理しているためSDKの新規登録や編集にも対応しています。

[GitHub](https://github.com/Yuzuki-Midoshima/Finger-SDK-Tool)

### FK-Builder

![FK-Builder](docs/gifs/fk_builder.gif)

FKコントローラーを自動生成するツールです。色や形状はもちろん、初期値やロックの調整も可能です。ON/OFFの管理コントローラーの設定もできます。

[GitHub](https://github.com/Yuzuki-Midoshima/FK-Builder)

### FK / IK Auto Matcher

![FK IK Auto Matcher](docs/gifs/auto_matcher.gif)

IK / FK切り替え時のポーズマッチを自動化するツールです。オーソドックスな仕組みの物であればどのリグでも使用可能です。

[GitHub](https://github.com/Yuzuki-Midoshima/FK-IK-AutoMatcher)

### Controller Shape Library

![Controller Shape Library](docs/images/controller_shape_library.png)

Controller Shapeの作成・管理・編集を効率化するツールです。他のツールに組み込むことを前提にした設計になっています。

[GitHub](https://github.com/Yuzuki-Midoshima/Controller-Shape-Library)

---

## 制作環境・リポジトリ構成

```text

Autodesk Maya 2026

Python

Windows

```

---

## 使用モデル・公開について

- **Character:** Diana（オリジナルキャラクター）
- **2D原案・素体をベースとしたモデル制作・リギング:** Yuzuki Midoshima
- **公開情報:** リグの動作デモ・画像・技術解説、および関連ツールのGitHubリンク

---

## Portfolio

デザイン・技術解説はポートフォリオとしてViViViTにも掲載しています。

宜しければ併せてご覧ください！

[ViViViT](https://vivivit.com/yuzuki_midoshima)

---

## GitHub

制作したツールやテクニカルアート関連プロジェクトを公開しています。

[GitHub - Yuzuki Midoshima](https://github.com/Yuzuki-Midoshima)

---

## License

MIT License

Copyright (c) 2026 Yuzuki Midoshima

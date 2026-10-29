# Diana Character Rig | Pivot Transfer

Diana専用のMaya 2026起動・任意Pivot・ALL/Pivot復元ツールです。Horseのモジュールは読み込みません。

## 構成
- `scripts/Pivot_Transfer/diana_pivot_v3.py`: Pivot同期コールバック
- `scripts/Pivot_Transfer/diana_pivot_to_all.py`: ALL/Pivot間の復元処理
- `scripts/Pivot_Transfer/diana_pivot_transfer_ui.py`: 復元UI
- `scripts/Pivot_Transfer/Shelf.py`: Shelfボタン用の既存コード
- `scripts/diana_pivot_autostart.py`: Dianaシーンを開いたときの監視登録
- `scripts/startup/userSetup.py`: Maya起動時の入口

## 導入
1. `Diana-Character-Rig` リポジトリに本ZIPのファイルを配置します。既存ファイルは比較・バックアップしてから反映してください。
2. `scripts/startup/userSetup.py` を、実際にMayaが読む `userSetup.py` の場所にコピーします。既存のファイルはバックアップしてください。
3. リポジトリの場所が標準と違う場合は、環境変数 `DIANA_RIG_REPO` にリポジトリの絶対パスを設定します。
4. Mayaを再起動し、Dianaのシーンを開き、Script Editorに `[DIANA] Pivot callback active` と表示されるか確認してください。
5. UIは `scripts/Pivot_Transfer/Shelf.py` の内容をShelfボタンに設定して起動できます。

## 注意
- 既存の `diana_pivot_v3.py` は、SYSTEMがワールド直下にあり、必要な接続が設定されたリグを前提とします。
- 新規シーンや別のシーンではPivot監視を停止します。
- Maya実機での動作は未検証です。バックアップしたシーンで確認してください。
- 同時にHorseのuserSetupを導入する構成ではありません。

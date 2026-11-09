# Diana Character Rig scripts

Maya 2026用のPivot Transferツールです。リポジトリ直下の
`drag_drop_install.py` がMaya moduleを登録するため、このフォルダーを別の
場所へコピーする必要はありません。既存の `userSetup.py` も上書きしません。

## 構成

- `userSetup.py`: Maya moduleから実行される起動入口
- `diana_pivot_autostart.py`: シーン切り替え監視とPivot callbackの登録
- `Pivot_Transfer/diana_pivot_v3.py`: Pivot同期callback
- `Pivot_Transfer/diana_pivot_to_all.py`: ALL / Pivot間の移管処理
- `Pivot_Transfer/diana_pivot_transfer_ui.py`: 操作用UI
- `Pivot_Transfer/Shelf.py`: Shelfボタン用の起動入口
- `equipment_manager/`: Diana用Equipment Managerランタイム
- `launch_equipment_manager.py`: Equipment Managerの起動入口
- `startup/userSetup.py`: 旧インストールとの互換用（新規導入では不使用）

Shelfボタンを作る場合、Pythonコマンドは次の2行です。

```python
from Pivot_Transfer import Shelf
Shelf.show()
```

インストールとアンインストールの手順はリポジトリ直下のREADMEを参照してください。
インストーラーはPivot TransferとEquipment Managerを `Diana Rig` Shelfへ登録します。

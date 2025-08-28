cards/README (plain text)

目的:
  役割カード（未署名）の保管庫。署名は scripts/sign_card.py でローカル実行。
  署名済みはコミット禁止（.gitignore で cards/*.signed.json を無視）。

ファイル:
  - my_card.json（未署名テンプレ。これだけコミットOK）
  - my_card.signed.json（署名後。コミット禁止）

カードの基本構造:
  {
    "meta": {
      "name": "be_kind",
      "version": "1.0",
      "namespace": "behavior",
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_to":   "2026-01-01T00:00:00Z",
      "alg": "HMAC-SHA256",
      "sig": ""
    },
    "caps": { "net_allowed": false },
    "policy": { "priority": 10 }
  }

署名のポイント（strict時は必須/ fail-closed）:
  - alg = HMAC-SHA256 のみ許可（未知algは拒否）
  - secret 必須、sig 非空、検証成功が条件
  - device_lock（端末ID一致）がある（外部流出防止）
  - valid_from/valid_to の期間外は無効

やってはいけない:
  - 鍵や署名済みカードをコミットすること
  - CIで鍵を生成/保持すること（デモ用YAMLを置かない運用推奨）

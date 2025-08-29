SECURITY (minimal)

- 完全ローカル: ネットワーク接続や外部DBアクセスの実装は同梱しない。
- 秘密情報: 署名鍵・署名済みカードはリポに入れない（.gitignoreで遮断）。
- fail-closed: 署名/期限/device_lock/アルゴ不一致は起動拒否。
- 監査性: METRICS コメントとトレースで挙動を後から確認可能。

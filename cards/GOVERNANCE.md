CARDS GOVERNANCE — 運用ミニルール（ネットなし前提）

- 命名: <namespace>/<name>@<version>
- 同一namespaceは同時装着1枚（mutex）。研究モードのみ複数試験可。
- 署名: HMAC-SHA256 / secret / 期限 / device_lock を満たさないカードは起動拒否（fail-closed）。

注記（ネット権限について）:
- 本コアはネットワーク機能を実装していないため、カード側の net_allowed フラグは無視される。
- 外部接続を前提にしたカードの配布は推奨しない。

INTEGRATIONS — 外部連携について

前提:
- 本コアは完全ローカル駆動（既定でネット/外部APIなし）。
- ここに書くのは将来の展望と、ローカルI/Oでの実践的な連携アイデア。

1) API経由の外部サービス連携（例: Slack / Discord / Webアプリ / OpenAI API など）
- 今のコードには実装していません。
- ただし UnifiedAgent は自己完結なので、別のPythonスクリプトから agent.generate()（= respond相当）の出力を返すだけで、任意のAPIハンドラに差し込めます。
- つまり「このコアを思考エンジンとして使い、周辺を自由に差し替える」構成が可能。

2) ローカルでの外部プログラム・データ連携
- 状態の保存/読み込み（JSON）は既に実装済み（export_state / import_state）。
- これで別プロセスや別プログラムと手軽にやり取りできます。

例: ローカルでの状態保存/復元
    # 保存
    with open("agent_state.json", "w", encoding="utf-8") as f:
        f.write(agent.export_state())

    # 復元
    with open("agent_state.json", "r", encoding="utf-8") as f:
        agent.import_state(f.read())

活用例:
- ゲーム: セーブデータにAIの状態を含め、ロード時に前回の会話を覚えているNPCを実現
- Webサーバー: ユーザーごとにAI状態(JSON)を保存し、「いつものAI」を復元
- IoT: デバイス設定をJSONでバックアップ/ロールバック

まとめ:
- ネット経由の外部API連携 → 今は未実装だが、構造的に差し込みは容易
- ローカルファイルや他プログラムとの連携 → すでに対応済み（JSONで往復）

補足（方針メモ）:
- 本リポは完全ローカル方針。ネット接続を伴う実装・運用は各自の判断と責任で。
- ここでは手順やコードは提供しません（ビジョンの共有のみ）。

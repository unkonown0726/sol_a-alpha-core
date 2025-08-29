DESIGN PRINCIPLES

1) 基盤中立（Dynamic Substrate Neutrality）
   - 思考ダイナミクス𝒢は実装基盤に依存しない。制約はCで受ける。

2) 三権分立（core + SLM + role-cards）
   - core: 意味生成と𝒢。SLM: 入出力の自然化。cards: 役割・権限境界。

3) fail-closed / 署名必須
   - strictはHMAC-SHA256 + secret + device_lock + 期限を満たさなければ起動しない。

4) ローカル優先
   - 既定でネット/LTMはOFF。必要なら自己責任で外付け。

5) 可視性と被服
   - 開発者は思考トレース可視。エンドユーザーには被服（出力整形）で安全表示。

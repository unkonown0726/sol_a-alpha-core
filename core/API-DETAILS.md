API DETAILS (plain text, v5.2.2)

目的:
  ライブラリとして使う人向けの「最小で確実に動かす」ための公開APIガイド。
  覚えるのはクラス3つ＋関数2つ。細かい哲学は SPEC.md 参照。

モジュール構成:
  core/wise_partner_core_v52_plus.py   ← 本体（Agent, GeometryS, Profile）
  core/reward_bridge.py                ← 外部KPI→𝒢の薄い橋（任意）
  GEOM/geometry_strict.py              ← strict 距離（研究用）
  adapters/io_if.py                    ← I/Oの雛形（任意）

主要型:
  Enum Profile:
    - MOBILE     : 軽量。strict不可。ネット/LTM禁止（既定）
    - DESKTOP    : 同上。少し重め機能を許容
    - LAB_STRICT : 研究用。strict許可（本番禁止）

  Class WisePartnerAgent(profile: Profile = DESKTOP)
    役割: 統合理論v5.2の「解釈関数 F_t」と「進化法則 𝒢」をカプセル化した思考エンジン。

  Class GeometryS
    役割: 意味空間 S(4軸) の距離計算。mode= line / geo / strict

公開API（最短で覚えるやつ）:
  from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile, GeometryS

  a = WisePartnerAgent(profile=Profile.DESKTOP)

  # 1) 応答を取る
  text = a.respond("こんにちは。今日の計画を立てたい。", explain=False)
    - 戻り値: 文字列（本文のどこかに HTMLコメントの METRICS タグを含む）
      例: <!--METRICS success=0.55 trust=0.60 stress=0.45 reality=0.70-->
    - explain=True で「内部の推論ステップ（可視化用）」を含める
    - 不確実/危険な入力のときは clarify/refuse系の安全返答に自動で落ちる

  # 2) 状態の保存/復元（永続人格）
  s = a.export_state()                  # canonical JSON（"hash" 付き）
  a.import_state(s)                     # 同じ内容を戻せばバイト等価に復元

  # 3) プロファイル切替（実行モード）
  a.set_profile(Profile.MOBILE | DESKTOP | LAB_STRICT)

  # 4) 研究用：人格連成のON/OFF（通常はOFF）
  a.enable_persona_bleed(True/False)

  # 5) 距離関数（外部評価などに使いたい人向け）
  d, d_norm, info = GeometryS.dist(q1, q2, mode="geo")
    - q は dict: {
        "project_success_prob": float(0..1),
        "trust_level": float(0..1),
        "stress_level": float(0..1),
        "reality": float(0..1)
      }
    - d_norm は「参照遷移で正規化した距離」（学習スケールに使う）

  # 6) 外部KPIで学習させたい（任意）
  from core.reward_bridge import RewardBridge
  rb = RewardBridge(a)
  rb.report("todo_plan", before_q, after_q)
    - 内部で GeometryS.dist を計算し、𝒢へ反映
    - reality<0.55 のデータは学習ゲートで自動スキップ（安全側）

METRICS タグ（契約）:
  形式: <!--METRICS success=0.55 trust=0.60 stress=0.45 reality=0.70-->
  役割: エンドユーザー表示は自由だが、ロガーや可視化が機械抽出できること。
  注意: 値域は 0..1。stress は「高いほどストレスが高い」。内部では inv_stress = 1 - stress を使う。

状態スキーマ（抜粋／export_state の構造イメージ）:
  {
    "version":"v5.2.2",
    "personality":{"openness":0,"agreeableness":0,"conscientiousness":0},
    "state":{
      "user_wellbeing":{
        "project_success_prob":0.50,"trust_level":0.50,"stress_level":0.50,"reality":0.50
      },
      "world_model":{"links":{ /* 𝒢が学習する影響マップ */ }}
    },
    "coupling":{"enabled":false},
    "cards":[ /* 実行時に装着中のカードメタ（安全のため詳細は省略） */ ],
    "profile":"desktop",
    "hash":"<sha256 of canonical payload>"
  }

進化法則 𝒢（実装の要点だけ）:
  - impact パラメタを Adam で更新（L2 正則化）
  - reality < 0.55 のデータは学習しない（noise/幻感の遮断）
  - 更新スケールは d_norm（距離の正規化）を採用
  - 近似距離は geo を基準、検証では strict と整合（MAPE ≤ 8%）

距離モードの使い分け:
  - line : 速いが粗い。ざっくり評価
  - geo  : 既定。速度/精度のバランス
  - strict: 研究用。LAB_STRICTでのみ有効。RK4射撃 + Γ再評価。重い

カード（役割）と署名（概要）:
  - 未署名テンプレ: cards/my_card.json（コミットしてOK）
  - 署名済み出力  : cards/my_card.signed.json（コミット禁止）
  - strictでは必須条件（fail-closed）:
      alg=HMAC-SHA256、secret設定済み、sig非空、検証成功、期限内、device_lock一致
  - 署名/ランチャは scripts/README を参照（ローカル限定）

例: 10行クイックスタート（Python）
  from core.wise_partner_core_v52_plus import WisePartnerAgent, Profile
  a = WisePartnerAgent(profile=Profile.DESKTOP)
  print(a.respond("タスクを3分割して明日と来週の計画を出して。", explain=False))
  s = a.export_state()
  # 再起動後
  b = WisePartnerAgent(profile=Profile.DESKTOP)
  b.import_state(s)
  print(b.respond("さっきの続き。次の一手は？", explain=False))

エラーと落ち方（ざっくり）:
  - import_state の hash 不一致        : ValueError（改ざん検出）
  - LAB_STRICT以外で strict 要求      : RuntimeError（拒否）
  - 署名検証失敗 / secret未設定       : RuntimeError（fail-closed）
  - 入力が無意味（空/極小）          : 安全側の clarify/refuse にフォールバック
  - 例外は基本 raise せず安全返答に変換（ログに記録される）

スレッド/プロセス:
  - スレッド安全は「呼び出し側で排他」前提。並列はプロセス分離推奨（状態があるため）
  - export_state()/import_state() でプロセス間移送は容易

性能ノブ（調整ポイント）:
  - GeometryS.dist(mode="geo") を既定に（対話TAT）
  - strict の steps/iters は bench/ を見て調整
  - 𝒢の学習レート/クリップは定数化済み。安定志向。変更は上級者のみ

拡張ポイント:
  - adapters/io_if.py を差し替えて STT/TTS/GUI/センサーを実装
  - RewardBridge で外部KPIから 𝒢 を更新
  - 役割カードを名前空間ごとに追加（例: behavior, tutor, counselor）

互換とバージョン:
  - SPEC 準拠: v5.2.2（Export/Import互換、距離精度条件、Realityゲート）
  - 破壊的変更は minor を上げる（例: v5.3.*）。export_state の version で判定可能

最低限の作法（本番の心得）:
  - ネット/LTMは既定でOFF。必要でも“明示スイッチ＋READMEに手順”で。
  - 署名鍵と署名済みカードはリポに入れない（.gitignoreで遮断済み）
  - LAB_STRICTは研究専用。ユーザー配布は DESKTOP/MOBILE 限定で。

以上。これだけ覚えれば “呼ぶ→返る→学ぶ” が成立する。残りは README と SPEC に書いてある。

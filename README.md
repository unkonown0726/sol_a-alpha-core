sol-α core v5.2.2 — Local AI core
三本柱: 思考の可視化 / 完全ローカル駆動 / 三権分立（core・SLM・cards）


[1] これ何 / Three pillars
- 思考の可視化（Auditability）:
  応答に機械可読の METRICS コメントを埋め込み、必要に応じて内部トレースを開示できる。
- 完全ローカル駆動（Security/Privacy by design）:
  既定でネットワーク・外部DB・外部APIを使わない。外部送信なし。
- 三権分立（責任分離）:
  core: 意味生成と更新則（G）。SLM: 入出力の自然化。cards: 役割と権限の枠。責任の所在を分離。


[2] 特徴（できること）
- ローカルのみで対話を生成（状態を保持するステートフル設計）
- 意味空間S(4軸)の距離: line / geo / strict（geoが既定）
- 進化法則G: 安定志向の更新（実装済み）
- METRICS埋め込み + トレース（開発者向け）
- 役割カード（署名必須 / fail-closed）。研究モードでの複数装着に対応

[3] クイックスタート（最短）
前提: Python 3.11

  PYTHONPATH=. pytest -q
  python core/wise_partner_core_v52_plus.py

（動けば METRICS コメントと簡易出力が見える）

[4] プロファイル
- MOBILE / DESKTOP : 既定。研究向け機能は一部無効化（完全ローカル）
- LAB_STRICT       : 研究専用。strict距離などの重い機能を許可（外部通信はそもそも未実装）

[5] 思考の可視化（METRICS / トレース）
- 応答文字列のどこかに:
    <!--METRICS success=0.55 trust=0.60 stress=0.45 reality=0.70-->
- 監査ログ/直近イベント/滲みの表示（実装がある場合）:
    例: examples/audit_demo.py を参照
  環境変数で監査ON（任意）:
    macOS/Linux:  export WPCORE_AUDIT=1
    Windows PS:   $env:WPCORE_AUDIT=1

[6] 永続人格（stateの保存/復元）
- 保存（canonical JSON + hash）:
    s = agent.export_state()  → state.json
- 復元:
    agent.import_state(open("state.json", encoding="utf-8").read())
- 往復でバイト等価になる（hash不一致は例外）

[7] 距離（GEOM）
- モード:
    line  : とても速い / 粗い
    geo   : 既定。速度と精度のバランス
    strict: 研究専用（RK4 + Γ再評価）。重い
- 正規化距離 d_norm = d / d(ref)。学習スケールと閾値は d_norm を使用
- 詳細: GEOM/README を参照

[8] 役割カード（strictは研究専用 / fail-closed）
- 未署名のテンプレは cards/ に置く。署名済み（*.signed.json）はコミット禁止（.gitignoreで遮断）
- 起動条件（満たさなければ拒否 / fail-closed）:
    HMAC-SHA256 / secret必須 / sig非空 / 期限内 / device_lock一致
- 複数装着:
    同一namespaceは基本1枚（mutex）。LAB_STRICTでのみ実験的緩和。優先度で排他
- 詳細: cards/README を参照

[9] セキュリティ（完全ローカル / 鍵・署名）
- 本リポはネット/外部DB/外部APIを実装しない
- 署名鍵や署名済みカードはリポに含めない（.sola/ や *.signed.json は .gitignore 済み）
- 失効（任意運用）: cards/REVOKED.txt に列挙 → 実行前チェックで拒否

[10] ディレクトリ構成<br>

  core/       本体（Agent / GeometryS / Profile）<br>
  GEOM/       距離モジュール（strictは研究専用）<br>
  adapters/   I/O雛形（外部通信は未実装）<br>
  scripts/    署名・実行のローカル手順（研究用途）<br>
  cards/      未署名カード（テンプレのみコミット）<br>
  examples/   簡易サンプル（監査デモ等）<br>
  bench/      速度/精度ベンチ<br>
  tests/      仕様テスト（pytest）<br>
  docs/       理論・設計・運用文書・今後の展望など（FOUNDING-PRINCIPLES 等）<br>
  SPEC.md     互換仕様<br>

[11] 付録（ベンチ/テスト/例）
- 速度:
    PYTHONPATH=. python bench/speed_strict.py
- 近似誤差（geo vs strict, 目標 MAPE ≤ 8%）:
    PYTHONPATH=. python bench/acc_geo_vs_strict.py
- 仕様テスト:
    PYTHONPATH=. pytest -q
- 監査デモ:
    python examples/audit_demo.py   （必要なら WPCORE_AUDIT=1）

[12] ドキュメント索引 / ライセンス
- docs/FOUNDING-PRINCIPLES.md  … 三本柱の詳細
- GEOM/README                   … 距離モードの使い分け
- core/API-DETAILS.md           … 公開APIの詳細
- cards/README                  … 署名/起動の実務
- POLICY.md                   … 最小の安全方針

カード方式の意図:
 - 将来のアンドロイド実装と完全ローカル駆動を見据え、役割・知識・権限をカードとして外部化しています。
いまのうちからカードの署名・失効・互換テストを回し、市場と安全運用を成熟させる狙いです。
詳しくは /docs/CARDS-VISION.txt と /cards/GOVERNANCE.txt を参照してください。


拡張（研究者向け・自己責任）
- 既定ではネット接続/LTMは無効です。本稿は「差し込み口」の告知のみで、実装は同梱しません。
- 研究目的で LAB_STRICT でも有効化したい場合は環境変数を使います。

  ・ネット許可（LAB_STRICT時のみ上書き可）
      SOLA_STRICT_ALLOW_NET=1
    または（どのプロファイルでも読む共通フラグ）
      SOLA_NET=1

  ・長期記憶許可（LAB_STRICT時のみ上書き可）
      SOLA_STRICT_ALLOW_LTM=1
    または共通フラグ
      SOLA_LTM=1

  ・非常停止（常に無効）
      SOLA_HARD_BLOCK=1

- 外部ストアやHTTPクライアント等の実装は各自の責任で別途用意してください。
- セキュリティ・プライバシー・権利関係の確認は各自で行ってください。

ポリシー:
- 既定で「ネット接続なし」「長期記憶（LTM）なし」。本リポは差し込み口のみを公開し、実装は同梱しません。
- 作者は「LTMを含めることで初めて実用上の永続人格が成立し得る」という見解を持ちますが、
  本リポでは当該機能の具体実装・設定手順・回避策等はいっさい提供しません。

利用者への注意:
- 拡張を行う場合は各自の責任で実装し、適用法令・契約・特許・第三者権利・社内規程・データ保護規制に適合させてください。
- このREADMEは技術的指南・法律助言を目的としません。必要に応じて専門家に相談してください。

FAQ<br>

Q. ネットや長期記憶を使いたい<br>
A. 本リポは完全ローカル前提で、実装や入口は同梱していません。<br>

Q. 三権分立の内訳は？<br>
A. core（意味生成/𝒢）、SLM（入出力の自然化）、cards（役割と権限の枠）。責任を分けるための設計です。<br>

Q. 思考の可視化はどう見る？<br>
A. 返答中の( !--METRICS ... --)と、開発者向けのトレース出力を参照してください。<br>

適正利用（要約）:
- 本プロジェクトおよび派生物を、違法行為、他者への危害、差別/嫌がらせ、プライバシー侵害・監視、サイバー不正（マルウェア/不正アクセス等）、誤情報/なりすまし、高リスク領域での無責任運用（医療/法務/金融/重要インフラ等）、安全機構の回避（署名/期限/端末ロックの無効化）に使用しないでください。**軍事・防衛・情報機関での利用（兵器開発、標的選定/誘導、戦闘・作戦支援、広域監視を含む）を禁止**します。  
本プロジェクトの細則は各自の責任で遵守してください。

License: Apache-2.0


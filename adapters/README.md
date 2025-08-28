adapters/README (plain text)

目的:
  目・耳・手足に相当する I/O インタフェースの置き場。io_if.py は最小の雛形。
  将来のモバイル展開や外部ツール接続はここから生やす。

方針:
  - core（思考）と adapters（入出力）を分離。コアは常にローカル/ステートフル。
  - 役割カード（専門知識）は core 側で解釈し、I/Oは adapters が運ぶだけ。

最低限の契約:
  - from adapters.io_if import InputAdapter, OutputAdapter（雛形クラス）
  - InputAdapter.encode(text|sensor) -> 内部表現（コアへ渡せる形ならOK）
  - OutputAdapter.realize(plan|speech_act) -> 表示文字列 or 音声など

セキュリティ:
  - ネット通信は既定で無し。追加するなら「明示的に」ONにし、READMEに手順を記載。
  - OS機能（TTS/STT）を使う場合でも、個人情報や鍵は外に送らない設計を維持。

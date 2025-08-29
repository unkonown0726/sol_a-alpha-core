tests/README (plain text)

目的:
  最低限の互換・安全性チェックを pytest で回す。

中身:
  - test_conformance.py
      * SPD正定の確認（GeometryS.metric）
      * 進化法則𝒢の reality ゲート（reality<0.55 で更新しない）
  - test_uncertainty.py
      * 不確実時に安全側の返答（clarify/refuse/要点返し 等のマーカー）

実行:
  ローカル:
    PYTHONPATH=. pytest -q
  1件だけ:
    PYTHONPATH=. pytest tests/test_uncertainty.py::test_uncertain_handles_safely -q
  出力を見たい:
    PYTHONPATH=. pytest -q -s -k uncertain

CI:
  .github/workflows/ci.yml が push/PR で自動実行（鍵操作は一切しない構成推奨）<br>

  Manual probes (optional):<br>

  macOS / Linux:<br>

  export WPCORE_AUDIT=1
python examples/audit_demo.pyexport WPCORE_AUDIT=1<br>
※OFFに戻す: unset WPCORE_AUDIT<br>

Windows (PowerShell):<br>

$env:WPCORE_AUDIT=1
python examples\audit_demo.py$env:WPCORE_AUDIT=1<br>
※OFFに戻す: Remove-Item Env:WPCORE_AUDIT


  

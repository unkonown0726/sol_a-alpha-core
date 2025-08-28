bench/README (plain text)

目的:
  strictモードの重さと、geoの近似精度を数値で把握するための軽いベンチ。

スクリプト:
  - bench/speed_strict.py
      * ランダム100対くらいで strict の1対計算コストを計測
  - bench/acc_geo_vs_strict.py
      * geo と strict の距離の MAPE（平均絶対百分率誤差）を算出
      * SPEC要件: MAPE ≤ 8%

実行:
  PYTHONPATH=. python bench/speed_strict.py
  PYTHONPATH=. python bench/acc_geo_vs_strict.py

注意:
  CIで回す必要はない（重い）。ローカルで環境差を掴むためのもの。

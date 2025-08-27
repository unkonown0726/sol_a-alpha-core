\# Unified Agent SPEC v1.0



\## 0. Scope

本SPECは「統合理論v5.2」を実装する最小互換レイヤー。互換の判定対象は：

\- 状態スキーマ（Export/Import）

\- 計量幾何Sの距離関数（`line|geo|strict`）

\- Realizer/Validator/𝒢(進化法則) の相互作用

\- カード（署名・期限・device\_lock）とプロファイル制御



\## 1. Terms

P=身体, M=意識, F\_t=解釈関数, 𝒢=進化法則, S=意味空間, g=計量, q\_reality=現実感。



\## 2. State Schema (canonical JSON)

```json

{

&nbsp; "version": "v5.2.1",

&nbsp; "personality": {"openness":0,"agreeableness":0,"conscientiousness":0},

&nbsp; "state": {

&nbsp;   "user\_wellbeing": {

&nbsp;     "project\_success\_prob": 0.50,

&nbsp;     "trust\_level": 0.50,

&nbsp;     "stress\_level": 0.50,

&nbsp;     "reality": 0.50

&nbsp;   },

&nbsp;   "world\_model": {

&nbsp;     "links": {

&nbsp;       "respond\_helpfully|be\_kind":{

&nbsp;         "project\_success\_prob":\[0.06,0.9],

&nbsp;         "trust\_level":\[0.10,0.85],

&nbsp;         "stress\_level":\[-0.04,0.8],

&nbsp;         "reality":\[0.03,0.8]

&nbsp;       }

&nbsp;     }

&nbsp;   }

&nbsp; },

&nbsp; "coupling": {"enabled": false},

&nbsp; "cards": \[],

&nbsp; "profile": "mobile",

&nbsp; "hash": "<sha256 of canonical payload>"

}




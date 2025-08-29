cards / README (plain)

目的:
  役割カード（未署名）を置く場所。署名はローカルで行う。
  署名済みカードや鍵はリポに入れない（.gitignoreで無視）。

置くもの（コミットOK）:
  - cards/my_card.json        ← 未署名テンプレ（これだけコミットする）

置かないもの（コミット禁止）:
  - cards/my_card.signed.json ← 署名後のファイル
  - ~/.sola/card_secret.hex   ← カード署名キー（各OSのホーム配下）
  - ~/.sola/ck_secret.hex     ← チェックポイント署名キー
  - *.key / *.pem / *.p12 / *.crt / .sola/ ディレクトリ など

サンプル（未署名テンプレ: cards/my_card.json）:

  {
    "meta": {
      "name": "be_kind",
      "version": "1.0",
      "namespace": "behavior",
      "valid_from": "2025-01-01T00:00:00Z",
      "valid_to":   "2026-01-01T00:00:00Z",
      "alg": "HMAC-SHA256",
      "sig": ""
    },
    "caps":   { "net_allowed": false },
    "policy": { "priority": 10 }
  }

使い方（ローカル専用・4手で終わる）:

[1] 鍵を作る（初回だけ）<br>

  macOS / Linux:<br>
    mkdir -p ~/.sola
    openssl rand -hex 32 > ~/.sola/card_secret.hex
    openssl rand -hex 32 > ~/.sola/ck_secret.hex

  Windows (PowerShell):<br>
    New-Item -ItemType Directory "$env:USERPROFILE\.sola" -Force | Out-Null
    $r=[System.Security.Cryptography.RandomNumberGenerator]::Create()
    function New-HexKey($p){$b=New-Object byte[] 32;$r.GetBytes($b);($b|%{ $_.ToString('x2') }) -join ''|Out-File -NoNewline $p}
    New-HexKey "$env:USERPROFILE\.sola\card_secret.hex"
    New-HexKey "$env:USERPROFILE\.sola\ck_secret.hex"

[2] DEVICE_ID を環境変数へ（端末バインド）<br>

  macOS / Linux:<br>
    export DEVICE_ID="$(cat /etc/machine-id 2>/dev/null || ioreg -rd1 -c IOPlatformExpertDevice | awk -F'\"' '/IOPlatformUUID/{print $4}')"
    
  Windows (PowerShell):<br>
    $env:DEVICE_ID=(Get-CimInstance Win32_ComputerSystemProduct).UUID

[3] カードに署名（入力→出力パスは固定）<br>

  入力:  cards/my_card.json<br>
  出力:  cards/my_card.signed.json   ← コミット禁止

  macOS / Linux:<br>
    python scripts/sign_card.py --secret ~/.sola/card_secret.hex \
      --in cards/my_card.json --out cards/my_card.signed.json \
      --device-lock "$DEVICE_ID"

  Windows (PowerShell):<br>
    python scripts\sign_card.py --secret $env:USERPROFILE\.sola\card_secret.hex `
      --in cards\my_card.json --out cards\my_card.signed.json `
      --device-lock "$env:DEVICE_ID"

[4] ネット遮断で実行（Docker推奨）<br>

  macOS / Linux:<br>
    docker run --rm --network=none \
      -e DEVICE_ID="$DEVICE_ID" -e SOLA_HOME="/secrets" \
      -v "$HOME/.sola":/secrets:ro -v "$PWD":/app -w /app python:3.11 \
      python scripts/run_strict.py cards/my_card.signed.json

  Windows (PowerShell):<br>
    docker run --rm --network=none `
      -e DEVICE_ID="$env:DEVICE_ID" -e SOLA_HOME="/secrets" `
      -v "$env:USERPROFILE\.sola":/secrets:ro `
      -v "$PWD":/app -w /app python:3.11 `
      python scripts/run_strict.py cards/my_card.signed.json

  成功サイン（ログに出る文字）:<br>
  
    card strict-activate: True
    checkpoint signed: True

注意（strictは fail-closed）:
  - alg が HMAC-SHA256 以外／secret 未設定／署名不一致／期限外／device_lock 不一致 → 起動拒否
  - LAB_STRICT 以外のプロファイルで strict を使うと拒否される（仕様）

セルフチェック（安全のため任意）:

  A) 現在ステージに危険物が無いか（OK が出れば安全）<br>
  
    macOS/Linux/Git Bash:
      git status --porcelain | grep -E "(\.sola|\.signed\.json|card_secret\.hex|ck_secret\.hex)" || echo "OK: nothing sensitive staged"
      
    Windows PowerShell:
      $m = git status --porcelain | Select-String -Pattern '\.sola|\.signed\.json|card_secret\.hex|ck_secret\.hex'
      if ($m) { $m; 'WARNING: sensitive staged' } else { 'OK: nothing sensitive staged' }

  B) .gitignore が効いているか（ルールが表示されればOK）<br>
  
    git check-ignore -v .sola/ cards/my_card.signed.json card_secret.hex ck_secret.hex

もし鍵や .signed.json をコミットしてしまったら:
  1) 追跡から外す:
       git rm --cached -r .sola cards/*.signed.json card_secret.hex ck_secret.hex
       git commit -m "purge secrets"
  2) 鍵を作り直す（上の [1] をやり直し）

FAQ（短縮）:<br>

  Q. 署名無しで strict を動かせる？ <br> A. 無理（安全のため起動拒否）<br>
  
  Q. 署名したのに動かない？ <br>        A. DEVICE_ID が一致していない/期限切れ/alg不一致を確認<br>
  
  Q. 署名済みカードはどこに置く？ <br>  A. cards/ に置いてOK。ただしコミット禁止（.gitignore が無視）<br>
  

終わり。分からなければ scripts/README を読む。

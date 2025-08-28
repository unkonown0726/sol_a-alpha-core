scripts/README (plain text)

目的:
  ローカル専用で「鍵を作る → カードに署名 → ネット遮断で実行」する最短手順。
  署名済みカードや鍵はリポに入れない（.gitignoreが弾く想定）。

このフォルダの中身:
  - run_strict.py : 署名済みカードで strict 実行するランチャ
  - sign_card.py  : 未署名カードに署名する（鍵は読み込むだけ。生成はしない）

前提:
  - Python 3.11
  - Docker Desktop（推奨。ネット遮断に使う）
  - 未署名カード: cards/my_card.json（このファイルだけコミットしてOK）

────────────────────────────────────────────────────────
[ 1 ] 初回だけ “鍵” を作る（ローカルに保存）
────────────────────────────────────────────────────────

macOS / Linux:
  mkdir -p ~/.sola
  openssl rand -hex 32 > ~/.sola/card_secret.hex    # カード署名用
  openssl rand -hex 32 > ~/.sola/ck_secret.hex      # チェックポイント署名用

Windows (PowerShell):
  New-Item -ItemType Directory "$env:USERPROFILE\.sola" -Force | Out-Null
  $r=[System.Security.Cryptography.RandomNumberGenerator]::Create()
  function New-HexKey($p){$b=New-Object byte[] 32;$r.GetBytes($b);($b|%{ $_.ToString('x2') }) -join ''|Out-File -NoNewline $p}
  New-HexKey "$env:USERPROFILE\.sola\card_secret.hex"
  New-HexKey "$env:USERPROFILE\.sola\ck_secret.hex"

※ これらの鍵は “あなたのPC内” にだけ置く。リポに入れない。

────────────────────────────────────────────────────────
[ 2 ] DEVICE_ID をセット（端末バインド）
────────────────────────────────────────────────────────

macOS / Linux:
  export DEVICE_ID="$(cat /etc/machine-id 2>/dev/null || ioreg -rd1 -c IOPlatformExpertDevice | awk -F'\"' '/IOPlatformUUID/{print $4}')"

Windows (PowerShell):
  $env:DEVICE_ID=(Get-CimInstance Win32_ComputerSystemProduct).UUID

────────────────────────────────────────────────────────
[ 3 ] カードに署名（入力→出力のパスは固定）
────────────────────────────────────────────────────────

入力:  cards/my_card.json           ← 未署名テンプレ（コミットしてよいのはコレだけ）
出力:  cards/my_card.signed.json    ← 署名済み（コミット禁止）

macOS / Linux:
  python scripts/sign_card.py --secret ~/.sola/card_secret.hex \
    --in cards/my_card.json --out cards/my_card.signed.json \
    --device-lock "$DEVICE_ID"

Windows (PowerShell):
  python scripts\sign_card.py --secret $env:USERPROFILE\.sola\card_secret.hex `
    --in cards\my_card.json --out cards\my_card.signed.json `
    --device-lock "$env:DEVICE_ID"

────────────────────────────────────────────────────────
[ 4 ] ネット遮断で実行（Docker --network=none）
────────────────────────────────────────────────────────

macOS / Linux:
  docker run --rm --network=none \
    -e DEVICE_ID="$DEVICE_ID" -e SOLA_HOME="/secrets" \
    -v "$HOME/.sola":/secrets:ro -v "$PWD":/app -w /app python:3.11 \
    python scripts/run_strict.py cards/my_card.signed.json

Windows (PowerShell):
  docker run --rm --network=none `
    -e DEVICE_ID="$env:DEVICE_ID" -e SOLA_HOME="/secrets" `
    -v "$env:USERPROFILE\.sola":/secrets:ro `
    -v "$PWD":/app -w /app python:3.11 `
    python scripts/run_strict.py cards/my_card.signed.json

成功サイン（ログに出る文字）:
  card strict-activate: True
  checkpoint signed: True

※ Dockerが無い場合（Windowsだけの応急処置）:
  $py=(Get-Command python).Source
  netsh advfirewall firewall add rule name="Block Python Out" dir=out action=block program="$py" enable=yes | Out-Null
  netsh advfirewall firewall add rule name="Block Python In"  dir=in  action=block program="$py" enable=yes | Out-Null
  python scripts\run_strict.py cards\my_card.signed.json
  # 解除:
  # netsh advfirewall firewall delete rule name="Block Python Out"
  # netsh advfirewall firewall delete rule name="Block Python In"

────────────────────────────────────────────────────────
[ 安全チェック（任意。貼って実行するだけ） ]
────────────────────────────────────────────────────────

A) いまステージに危ない物が無いか（OKが出れば安全）
  macOS/Linux/Git Bash:
    git status --porcelain | grep -E "(\.sola|\.signed\.json|card_secret\.hex|ck_secret\.hex)" || echo "OK: nothing sensitive staged"
  Windows PowerShell:
    $m = git status --porcelain | Select-String -Pattern '\.sola|\.signed\.json|card_secret\.hex|ck_secret\.hex'
    if ($m) { $m; 'WARNING: sensitive staged' } else { 'OK: nothing sensitive staged' }

B) .gitignore が効いてるか（無視ルールが表示されればOK）
  git check-ignore -v .sola/ cards/my_card.signed.json card_secret.hex ck_secret.hex

────────────────────────────────────────────────────────
FAQ（雑だけど役に立つ）
────────────────────────────────────────────────────────
Q. 鍵を作ってないのに動かない。
A. 正しい。鍵が無いと署名できない→strictは起動しない（安全側）。[1]から。

Q. 署名済みファイルや鍵をコミットしちゃった。
A. すぐ外す:
     git rm --cached -r .sola cards/*.signed.json card_secret.hex ck_secret.hex
     git commit -m "purge secrets"
   その後で鍵を作り直す（[1]）。

Q. 何をコミットして良いの？
A. cards/my_card.json（未署名）だけ。あとはコードとREADME。以上。

作者へのお願い（雑に重要）:
  ・鍵と署名済みカードはリポに絶対入れない
  ・Dockerの --network=none を使う（なければFWブロック）
  ・困ったらこのREADMEをそのまま貼り直す（だいたい治る）

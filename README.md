# HRMOS勤怠 自動入力ツール

HRMOS勤怠システムの月次勤務時間を自動入力するPythonツールです。

## 機能

- HRMOS勤怠システムへの自動ログイン
- 月次の勤務時間を一括自動入力（平日のみ）
- 既に入力済みの日付は自動でスキップ
- 設定ファイルによる柔軟な勤務パターン管理

## 必要要件

- Python 3.13（推奨）
- Playwright

**注意**: このツールはPython 3.13で動作確認済みです。

## 事前準備

### Pythonのインストール（未インストールの場合）

#### Windows
1. [Python公式サイト](https://www.python.org/downloads/)からダウンロード
2. インストーラーを実行時に**「Add Python to PATH」に必ずチェック**
3. インストール後、新しいPowerShellを開いて確認：
   ```powershell
   python --version
   ```

#### Mac(Homebrew使える前提)
```bash
brew install python3
```

#### バージョン指定
```bash
brew install python@3.13
```

## セットアップ

1. 依存パッケージのインストール

```bash
# Windowsの場合
python -m pip install -r requirements.txt

# Macの場合
pip install -r requirements.txt
```

2. Playwrightブラウザのインストール

```bash
# Windowsの場合
python -m playwright install chromium

# Macの場合
playwright install chromium
```

3. 環境変数の設定

`.env.example`をコピーして`.env`を作成し、ログイン情報と勤務時間を設定してください。

```bash
# Windowsの場合
copy .env.example .env

# Macの場合
cp .env.example .env
```

`.env`ファイルの内容を編集：

```env
# HRMOS勤怠 ログイン情報
LOGIN_URL=https://p.ieyasu.co/会社名/login
LOGIN_EMAIL=your_email@example.com
LOGIN_PASSWORD=your_password

# 勤務時間設定
WORK_START_TIME=09:00
WORK_END_TIME=17:30
BREAK_START_TIME=12:00
BREAK_END_TIME=13:00

# ブラウザ設定
BROWSER_HEADLESS=false
BROWSER_SLOW_MO=100
```

## 使用方法

```bash
# 通常の実行
python hrmos_auto_input.py

# 特定の年月を指定して自動入力
python hrmos_auto_input.py --year-month 2026-07
```

## 注意事項

- このツールは平日のみ勤務時間を入力します（土日祝日はスキップ）
- 既に入力済みの日付は自動でスキップされます（上書きしません）
- 実行前に必ず`.env`ファイルを確認してください
- 認証情報は安全に管理してください（`.env`は.gitignoreに追加済み）
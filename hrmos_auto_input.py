#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HRMOS勤怠 自動入力ツール

月次の勤務時間を自動入力するスクリプト
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError


class HRMOSAutoInput:
    """HRMOS勤怠自動入力クラス"""

    def __init__(self):
        """初期化"""
        self._load_env()
        self.page = None

    def _load_env(self):
        """環境変数を読み込む"""
        # .envファイルを読み込む
        env_path = Path('.env')
        if not env_path.exists():
            print("エラー: .envファイルが見つかりません")
            print("  .env.exampleをコピーして .env を作成し、設定を入力してください")
            sys.exit(1)

        load_dotenv()

        # 必須の環境変数をチェック
        required_vars = [
            'LOGIN_URL', 'LOGIN_EMAIL', 'LOGIN_PASSWORD',
            'WORK_START_TIME', 'WORK_END_TIME',
            'BREAK_START_TIME', 'BREAK_END_TIME'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            print(f"エラー: 以下の環境変数が設定されていません:")
            for var in missing_vars:
                print(f"  - {var}")
            sys.exit(1)

    def login(self, page: Page) -> bool:
        """
        HRMOS勤怠にログインする
        
        Args:
            page: Playwrightのページオブジェクト
            
        Returns:
            ログイン成功時True、失敗時False
        """
        try:
            login_url = os.getenv('LOGIN_URL')
            login_email = os.getenv('LOGIN_EMAIL')
            login_password = os.getenv('LOGIN_PASSWORD')
            
            print("ログインページにアクセスしています...")
            page.goto(login_url)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(1000)  # ページの完全な読み込みを待つ

            print("認証情報を入力しています...")
            
            # ログインID入力欄を待機して入力
            try:
                print("  ログインID入力欄を探しています...")
                login_id_input = page.locator('#user_login_id, input[name="user[login_id]"]').first
                login_id_input.wait_for(state='visible', timeout=10000)
                login_id_input.click()  # フォーカスを当てる
                page.wait_for_timeout(300)
                login_id_input.fill(login_email)
                print(f"  ✓ ログインIDを入力しました: {login_email}")
            except Exception as e:
                print(f"  ✗ ログインID入力欄が見つかりません: {e}")
                # デバッグ用: ページ内の全input要素を表示
                inputs = page.locator('input').all()
                print(f"  ページ内のinput要素数: {len(inputs)}")
                for i, inp in enumerate(inputs):
                    input_type = inp.get_attribute('type') or 'なし'
                    input_name = inp.get_attribute('name') or 'なし'
                    input_id = inp.get_attribute('id') or 'なし'
                    print(f"    input[{i}]: type={input_type}, name={input_name}, id={input_id}")
                raise

            # パスワード入力欄を待機して入力
            try:
                print("  パスワード入力欄を探しています...")
                password_input = page.locator('#user_password, input[name="user[password]"]').first
                password_input.wait_for(state='visible', timeout=10000)
                password_input.click()  # フォーカスを当てる
                page.wait_for_timeout(300)
                password_input.fill(login_password)
                print("  ✓ パスワードを入力しました")
            except Exception as e:
                print(f"  ✗ パスワード入力欄が見つかりません: {e}")
                raise

            print("ログインボタンをクリックしています...")
            # ログインボタンをクリック
            try:
                login_button = page.locator('button[type="submit"], input[type="submit"], button:has-text("ログイン")').first
                login_button.wait_for(state='visible', timeout=5000)
                login_button.click()
                print("  ✓ ログインボタンをクリックしました")
            except Exception as e:
                print(f"  ✗ ログインボタンが見つかりません: {e}")
                raise

            # ログイン後のページ遷移を待つ
            print("ログイン処理を待機しています...")
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            
            # ログイン成功の確認（URLが変わったかチェック）
            if '/works' in page.url or page.url != login_url:
                print("✓ ログインに成功しました")
                return True
            else:
                print("✗ ログインに失敗しました")
                print(f"  現在のURL: {page.url}")
                return False

        except Exception as e:
            print(f"✗ ログイン中にエラーが発生しました: {e}")
            return False

    def navigate_to_month(self, page: Page, year_month: str) -> bool:
        """
        指定された年月の勤怠ページに遷移する
        
        Args:
            page: Playwrightのページオブジェクト
            year_month: 年月 (YYYY-MM形式)
            
        Returns:
            遷移成功時True、失敗時False
        """
        try:
            url = f"https://p.ieyasu.co/works?date={year_month}"
            print(f"{year_month}の勤怠ページに遷移しています...")
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_load_state('networkidle')
            
            # ページが完全に読み込まれるまで少し待機
            page.wait_for_timeout(2000)
            
            # テーブルが読み込まれるまで待つ（DOMに存在すればOK）
            page.wait_for_selector('table.workTable', state='attached', timeout=30000)
            print(f"✓ {year_month}の勤怠ページを開きました")
            
            # テーブルが実際に表示されるまで追加で待機
            page.wait_for_timeout(1000)
            return True

        except Exception as e:
            print(f"✗ ページ遷移中にエラーが発生しました: {e}")
            return False

    def is_weekday_row(self, row) -> bool:
        """
        平日の行かどうかを判定する
        
        Args:
            row: テーブル行要素
            
        Returns:
            平日の場合True、土日祝日の場合False
        """
        try:
            class_attr = row.get_attribute('class') or ''
            # dayBlue（土曜）またはdayRed（日曜・祝日）が含まれていない場合は平日
            return 'dayBlue' not in class_attr and 'dayRed' not in class_attr
        except:
            return False

    def is_already_filled(self, row) -> bool:
        """
        既に勤務時間が入力済みかどうかを判定する
        
        Args:
            row: テーブル行要素
            
        Returns:
            入力済みの場合True、未入力の場合False
        """
        try:
            # 出勤時間が入力されているかチェック (cellTime01)
            start_cell = row.locator('td.cellTime01.view_work')
            if start_cell.count() > 0:
                # セル内のテキストを取得（spanやdiv内の値）
                cell_text = start_cell.inner_text().strip()
                # 時刻が入力されている（例: "09:00"）場合は入力済みと判定
                if cell_text and cell_text != '--:--' and ':' in cell_text:
                    return True
            
            return False
        except:
            return False

    def input_work_time(self, page: Page, row, day: int) -> bool:
        """
        1日分の勤務時間を入力する（編集ページに遷移して入力）
        
        Args:
            page: Playwrightのページオブジェクト
            row: 対象日の行要素
            day: 日付
            
        Returns:
            入力成功時True、失敗時False
        """
        try:
            work_start_time = os.getenv('WORK_START_TIME')
            work_end_time = os.getenv('WORK_END_TIME')
            break_start_time = os.getenv('BREAK_START_TIME')
            break_end_time = os.getenv('BREAK_END_TIME')
            
            print(f"  {day}日: 勤務時間を入力中...", end='')
            
            # 編集リンクを探してクリック
            edit_link = row.locator('a[href*="/works/"][href*="/edit"]').first
            if edit_link.count() == 0:
                print(" ✗ 編集リンクが見つかりません")
                return False
            
            # 編集ページに遷移
            edit_link.click()
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(1000)
            
            # 出勤時間を入力
            start_input = page.locator('#work_start_at_str, input[name="work[start_at_str]"]').first
            if start_input.count() > 0:
                start_input.fill(work_start_time)
                page.wait_for_timeout(200)

            # 退勤時間を入力
            end_input = page.locator('#work_end_at_str, input[name="work[end_at_str]"]').first
            if end_input.count() > 0:
                end_input.fill(work_end_time)
                page.wait_for_timeout(200)

            # 休憩開始時間を入力
            break_start_input = page.locator('#work_break_1_start_at_str, input[name="work[break_1_start_at_str]"]').first
            if break_start_input.count() > 0:
                break_start_input.fill(break_start_time)
                page.wait_for_timeout(200)

            # 休憩終了時間を入力
            break_end_input = page.locator('#work_break_1_end_at_str, input[name="work[break_1_end_at_str]"]').first
            if break_end_input.count() > 0:
                break_end_input.fill(break_end_time)
                page.wait_for_timeout(200)

            # 登録するボタンをクリック
            save_button = page.locator('input[type="submit"][value="登録する"], input[name="commit"][value="登録する"]').first
            if save_button.count() > 0:
                save_button.click()
                # 登録後、一覧ページに自動的に戻るのを待つ
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(1000)
            else:
                print(" ✗ 登録ボタンが見つかりません")
                # 一覧ページに戻る
                page.go_back()
                page.wait_for_load_state('networkidle')
                return False
            
            print(" ✓")
            return True

        except Exception as e:
            print(f" ✗ エラー: {e}")
            # エラー時は一覧ページに戻る
            try:
                page.go_back()
                page.wait_for_load_state('networkidle')
            except:
                pass
            return False

    def process_month(self, page: Page, year_month: str) -> bool:
        """
        1か月分の勤怠データを処理する
        
        Args:
            page: Playwrightのページオブジェクト
            year_month: 年月 (YYYY-MM形式)
            
        Returns:
            処理成功時True、失敗時False
        """
        try:
            print(f"\n{year_month}の勤怠入力を開始します")
            print("=" * 50)

            # テーブルの全行を取得
            rows = page.locator('table.workTable tbody tr')
            total_rows = rows.count()
            
            if total_rows == 0:
                print("✗ 勤怠データが見つかりません")
                return False

            print(f"  全{total_rows}日分のデータが見つかりました")
            print()

            success_count = 0
            skip_weekend_count = 0
            skip_filled_count = 0

            # 各行（各日）を処理
            for i in range(total_rows):
                # ページ遷移後に毎回行を再取得
                rows = page.locator('table.workTable tbody tr')
                row = rows.nth(i)
                
                # 平日かどうか判定
                if not self.is_weekday_row(row):
                    skip_weekend_count += 1
                    continue

                # 日付セルから日付を取得
                day_cell = row.locator('td.cellDate span.date').first
                if day_cell.count() > 0:
                    day_text = day_cell.inner_text().strip()
                    if day_text:
                        day = int(day_text)
                        
                        # 既に入力済みかチェック
                        if self.is_already_filled(row):
                            print(f"  {day}日: 既に入力済み（スキップ）")
                            skip_filled_count += 1
                            continue
                        
                        if self.input_work_time(page, row, day):
                            success_count += 1

            print()
            print("=" * 50)
            print(f"✓ 入力完了: {success_count}日")
            print(f"  入力済みスキップ: {skip_filled_count}日")
            print(f"  土日祝日スキップ: {skip_weekend_count}日")
            return True

        except Exception as e:
            print(f"✗ 処理中にエラーが発生しました: {e}")
            return False

    def run(self, year_month: str = None):
        """
        メイン処理を実行する
        
        Args:
            year_month: 年月 (YYYY-MM形式)、Noneの場合は当月
        """
        # 年月が指定されていない場合は当月を使用
        if not year_month:
            year_month = datetime.now().strftime('%Y-%m')

        # ブラウザ設定を環境変数から取得
        headless = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
        slow_mo = int(os.getenv('BROWSER_SLOW_MO', '100'))

        with sync_playwright() as p:
            # ブラウザを起動
            print("ブラウザを起動しています...")
            browser = p.chromium.launch(
                headless=headless,
                slow_mo=slow_mo
            )
            context = browser.new_context()
            page = context.new_page()

            # ログイン
            if not self.login(page):
                print("ログインに失敗したため、処理を中止します")
                return

            # 対象月のページに遷移
            if not self.navigate_to_month(page, year_month):
                print("ページ遷移に失敗したため、処理を中止します")
                return

            # 勤怠データを処理
            self.process_month(page, year_month)

            print("\n処理が完了しました")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description='HRMOS勤怠の月次勤務時間を自動入力するツール'
    )
    parser.add_argument(
        '--year-month',
        type=str,
        help='対象年月 (YYYY-MM形式)。指定しない場合は当月'
    )

    args = parser.parse_args()

    # 自動入力を実行
    auto_input = HRMOSAutoInput()
    auto_input.run(args.year_month)


if __name__ == '__main__':
    main()

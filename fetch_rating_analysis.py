import time
import math
import pandas as pd
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from generate_b50_image import generate_b50_image
import sys
# ==========================================
# 1. R 值計算邏輯 (保持不變)
# ==========================================
def calculate_r(achievement_val, constant):
    calc_ach = min(achievement_val, 100.5)
    if achievement_val >= 100.5: coeff = 22.4
    elif achievement_val >= 100.0: coeff = 21.6
    elif achievement_val >= 99.5:  coeff = 21.1
    elif achievement_val >= 99.0:  coeff = 20.8
    elif achievement_val >= 98.0:  coeff = 20.3
    elif achievement_val >= 97.0:  coeff = 20.0
    elif achievement_val >= 94.0:  coeff = 16.8
    elif achievement_val >= 90.0:  coeff = 15.2
    elif achievement_val >= 80.0:  coeff = 13.6
    elif achievement_val >= 75.0:  coeff = 12.0
    elif achievement_val >= 70.0:  coeff = 11.2
    elif achievement_val >= 60.0:  coeff = 9.6
    elif achievement_val >= 50.0:  coeff = 8.0
    elif achievement_val >= 40.0:  coeff = 6.4
    elif achievement_val >= 30.0:  coeff = 4.8
    elif achievement_val >= 20.0:  coeff = 3.2
    elif achievement_val >= 10.0:  coeff = 1.6
    else: coeff = 0.0
    return math.floor(constant * coeff * (calc_ach / 100))

# ==========================================
# 2. 獲取新版本歌曲白名單 (精確修正版)
# ==========================================
def get_new_songs_whitelist(driver):
    wait = WebDriverWait(driver, 15)
    whitelist = set()
    
    driver.get("https://maimaidx-eng.com/maimai-mobile/record/musicVersion/search/")
    # 確保下拉選單存在
    select_element = wait.until(EC.presence_of_element_located((By.NAME, "version")))
    options = select_element.find_elements(By.TAG_NAME, "option")
    version_ids = sorted([int(o.get_attribute("value")) for o in options if o.get_attribute("value").isdigit()])
    latest_two = version_ids[-2:]
    
    for vid in latest_two:
        target_url = f"https://maimaidx-eng.com/maimai-mobile/record/musicVersion/search/?version={vid}"
        driver.get(target_url)
        try:
            # ⭐ 核心修正：使用廣泛匹配，抓取包含 _score_back 的所有容器
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='_score_back']")))
            time.sleep(2) 
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            # 同時支援不同難度的方塊底色
            blocks = soup.select("div[class*='_score_back']") 
            
            v_count = 0
            for b in blocks:
                name_div = b.find("div", class_="music_name_block")
                if not name_div: continue
                
                name = name_div.text.strip()
                kind_img = b.find("img", class_="music_kind_icon")
                # 依據圖片檔案路徑判斷是否為 Standard 譜面
                kind = "STD" if kind_img and "music_standard.png" in kind_img.get("src") else "DX"
                
                whitelist.add((name, kind))
                v_count += 1
            print(f"📡 版本 {vid}: 成功抓取 {v_count} 首歌",flush=True)
        except:
            print(f"⚠️ 版本 {vid} 抓取超時或頁面無內容",flush=True)
            
    return whitelist

# ==========================================
# 3. 核心抓取與分析 (保持你的邏輯，優化穩定性)
# ==========================================
# ==========================================
# 3. 核心抓取與分析 (針對對戰表格結構優化)
# ==========================================
def fetch_friend_b50_analysis(driver, friend_idx):
    print("📋 正在建立新版本歌曲白名單...",flush=True)
    new_songs_whitelist = get_new_songs_whitelist(driver)
    
    if not new_songs_whitelist:
        print("❌ 白名單為空，請檢查網路或登入狀態。",flush=True)
        return

    all_results = []
    diff_names = {2: "Expert", 3: "Master", 4: "Re:Master"}
    wait = WebDriverWait(driver, 15)
    
    for diff_id, diff_label in diff_names.items():
        # 1. 進入跳轉頁面
        try:
            url = f"https://maimaidx-eng.com/maimai-mobile/friend/friendGenreVs/battleStart/?scoreType=2&genre=99&diff={diff_id}&idx={friend_idx}"
            driver.get(url)
            if "An error has occurred" in driver.page_source or "Friend not found" in driver.page_source:
                print("ERROR: 找不到該玩家，請檢查好友代碼是否正確。", flush=True)
                driver.quit()
                sys.exit(1)
        except Exception as e:
            print("ERROR: 找不到該玩家，請檢查好友代碼是否正確。", flush=True)
            driver.quit()
            sys.exit(1) # 以代碼 1 結束，代表執行出錯

        try:
            # 2. 點擊「START THE BATTLE」進入結果頁
            try:
                start_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.f_0"))
                )
            except Exception:
                # 如果連第一個難度都找不到按鈕，高機率是 ID 錯誤
                print("ERROR: 無法開始對戰。請確認好友代碼是否正確，或對方是否開啟了成績公開。", flush=True)
                driver.quit()
                sys.exit(1)
            driver.execute_script("arguments[0].click();", start_btn)
            
            # 3. 等待結果頁載入
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='_score_back']")))

            # 4. 每次跳轉難度都要重新注入腳本以獲取定數
            driver.execute_script("""
                (function(d){
                    var s=d.createElement('script');
                    s.src='https://myjian.github.io/mai-tools/scripts/all-in-one.js?t=' + Math.floor(Date.now()/60000);
                    d.body.append(s);
                })(document);
            """)
            time.sleep(8) 
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            blocks = soup.select("div[class*='_score_back']") 
            
            valid_count = 0
            for b in blocks:
                try:
                    name = b.find("div", class_="music_name_block").text.strip()
                    kind_img = b.find("img", class_="music_kind_icon")
                    kind = "STD" if kind_img and "music_standard.png" in kind_img.get("src") else "DX"
                    
                    # 5. ⭐ 精確定位好友成績 (右側欄位)
                    # 對戰表格的第一個 tr 包含：[我的成績, 判定圖, 好友成績]
                    first_tr = b.find("table", class_="f_14").find("tr")
                    all_tds = first_tr.find_all("td", recursive=False)
                    
                    # 好友成績是該列最後一個 td
                    friend_ach_td = all_tds[-1]
                    ach_text = friend_ach_td.text.strip().replace('%','')
                    
                    # 排除未遊玩狀態
                    if ach_text == "-" or not ach_text:
                        continue
                        
                    achievement = float(ach_text)
                    if achievement == 0: continue
                    
                    # 6. 抓取注入後的定數
                    constant = float(b.find("div", class_="music_lv_block").text.strip())
                    
                    r_score = calculate_r(achievement, constant)
                    category = "New" if (name, kind) in new_songs_whitelist else "Old"
                    
                    all_results.append({
                        "分類": category, "歌曲": name, "類型": kind, "難度": diff_label,
                        "定數": constant, "達成率": achievement, "R值": r_score
                    })
                    valid_count += 1
                except Exception:
                    continue
            print(f"✅ {diff_label} 解析完成，共 {valid_count} 筆有效數據",flush=True)

        except Exception as e:
            print(f"⚠️ {diff_label} 處理失敗: 請加機器人好友",flush=True)
            driver.quit()
            sys.exit(1)
            continue

    # (存檔與排序邏輯...)
    # (後續存檔邏輯保持不變)
    df_all = pd.DataFrame(all_results)
    if df_all.empty:
        print("❌ 未抓取到任何有效成績，請確認該好友是否有遊玩紀錄。",flush=True)
        return

    # 排序與篩選
    df_new = df_all[df_all["分類"] == "New"].sort_values("R值", ascending=False).head(15)
    df_old = df_all[df_all["分類"] == "Old"].sort_values("R值", ascending=False).head(35)
    final_df = pd.concat([df_new, df_old])

    try:
        # 呼叫產圖函式 (傳回圖片路徑)
        image_path = generate_b50_image(final_df, friend_idx, driver)
        return image_path
        # ⭐ 重要：印出這個標記，讓 Node.js 讀取
    except Exception as e:
        print(f"❌ 圖片生成失敗: {str(e)}", file=sys.stderr,flush=True)
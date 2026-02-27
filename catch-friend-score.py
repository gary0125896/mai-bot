import time
import json
import os
import sys
from fetch_rating_analysis import fetch_friend_b50_analysis
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 設定區域 ---
USER_ID = os.getenv("MAI_USER")
USER_PW = os.getenv("MAI_PASS")
if len(sys.argv) > 1:
    TARGET_FRIEND_ID = sys.argv[1]
else:
    # 如果沒傳參數的預設值（或是報錯）
    TARGET_FRIEND_ID = ""

def run_full_process():
    print("機器人登入中",flush=True)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--remote-allow-origins=*')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 20)

    # 🛡️ 隱藏 WebDriver 屬性，防止被偵測
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        # 1. 執行登入頁面動作
        driver.get("https://maimaidx-eng.com/maimai-mobile/")
        
        #print("🖱️ 點擊 SEGA ID 入口...")
        sega_id_entry = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "c-button--openid--segaId")))
        driver.execute_script("arguments[0].click();", sega_id_entry)
        
        #print("✅ 勾選同意條款...")
        agree_checkbox = wait.until(EC.presence_of_element_located((By.ID, "agree")))
        driver.execute_script("arguments[0].click();", agree_checkbox)
        
        #print("📝 填寫帳密 (使用腳本注入)...")
        # 直接使用 JS 設定值，避開 SendKeys 可能產生的 Interactable 錯誤
        wait.until(EC.presence_of_element_located((By.ID, "sid")))
        driver.execute_script(f"document.getElementById('sid').value = '{USER_ID}';")
        driver.execute_script(f"document.getElementById('password').value = '{USER_PW}';")
        
        #print("📤 送出登入...")
        login_btn = driver.find_element(By.ID, "btnSubmit")
        driver.execute_script("arguments[0].click();", login_btn)

        # 2. 等待跳轉至首頁
        wait.until(EC.url_contains("home"))
        print("🎉 登入成功！",flush=True)

        # # 3. 前往好友頁面
        # print("🏃 前往好友頁面...",flush=True)
        # driver.get("https://maimaidx-eng.com/maimai-mobile/friend/")
        
        # 4. 處理 200002 錯誤與腳本注入
        if "200002" in driver.page_source:
            driver.refresh()
            time.sleep(2)

        # 5. 執行分析
        final_image_path = fetch_friend_b50_analysis(driver, TARGET_FRIEND_ID)
        
        if final_image_path:
            print(f"OUTPUT_FILE:{final_image_path}",flush=True)
            
        else:
            print("OUTPUT_FILE:ERROR_PATH",flush=True)

    except Exception as e:
        driver.save_screenshot("debug_error.png")
        print(f"❌ 流程中斷: {e}" ,flush=True)
    finally:
        driver.quit()

if __name__ == "__main__":
    run_full_process()
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import json
import re
import shutil
import subprocess
import sys
import requests

def fix_chromedriver_issues():
    """Fix common ChromeDriver issues"""
    print("🔧 Checking and fixing ChromeDriver issues...")
    
    # Clear ChromeDriver cache
    try:
        cache_path = os.path.join(os.path.expanduser("~"), ".wdm")
        if os.path.exists(cache_path):
            print("🗑️ Clearing ChromeDriver cache...")
            import shutil
            shutil.rmtree(cache_path)
            print("✅ Cache cleared successfully")
    except Exception as e:
        print(f"⚠️ Could not clear cache: {e}")

def get_optimized_chrome_options():
    """Get optimized Chrome options for WhatsApp Web"""
    options = Options()
    
    # Essential options for stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    
    # User data directory for login persistence
    user_data_dir = os.path.join(os.getcwd(), "chrome-data")
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    # Disable automation detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Preferences
    prefs = {
        "profile.default_content_setting_values": {
            "notifications": 2,
            "geolocation": 2,
            "media_stream": 2,
        }
    }
    options.add_experimental_option("prefs", prefs)
    
    return options

def create_chrome_driver():
    """Create Chrome driver with multiple fallback methods"""
    print("🔧 Creating Chrome driver...")
    
    # Method 1: Try with ChromeDriverManager
    try:
        print("🔄 Trying ChromeDriverManager...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_optimized_chrome_options())
        print("✅ ChromeDriverManager method successful")
        return driver
    except Exception as e:
        print(f"❌ ChromeDriverManager failed: {e}")
    
    # Method 2: Try with explicit ChromeDriver path
    try:
        print("🔄 Trying with manual ChromeDriver download...")
        chromedriver_path = ChromeDriverManager().install()
        
        if os.path.exists(chromedriver_path):
            print(f"📂 ChromeDriver found at: {chromedriver_path}")
            
            try:
                os.chmod(chromedriver_path, 0o755)
            except:
                pass
            
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=get_optimized_chrome_options())
            print("✅ Manual ChromeDriver method successful")
            return driver
        else:
            print("❌ ChromeDriver file not found")
            
    except Exception as e:
        print(f"❌ Manual ChromeDriver failed: {e}")
    
    # Method 3: Try with system PATH ChromeDriver
    try:
        print("🔄 Trying ChromeDriver from system PATH...")
        driver = webdriver.Chrome(options=get_optimized_chrome_options())
        print("✅ System PATH ChromeDriver method successful")
        return driver
    except Exception as e:
        print(f"❌ System PATH ChromeDriver failed: {e}")
    
    print("❌ All ChromeDriver methods failed")
    return None

def wait_for_whatsapp_load(driver, timeout=60):
    """Wait for WhatsApp Web to load completely"""
    print("⏳ Waiting for WhatsApp Web to load...")
    
    wait = WebDriverWait(driver, timeout)
    
    # Check for QR code first
    try:
        qr_code = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='qr-code']"))
        )
        print("📱 QR Code detected - please scan with your phone")
        
        # Wait for QR code to disappear
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='qr-code']"))
        )
        print("✅ Authentication successful!")
    except TimeoutException:
        print("ℹ️ No QR code found - may already be logged in")
    
    # Wait for chat list to load
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list']")))
        print("✅ WhatsApp Web loaded successfully")
        time.sleep(3)  # Additional wait for stability
        return True
    except TimeoutException:
        # Fallback check
        try:
            wait.until(EC.presence_of_element_located((By.ID, "side")))
            print("✅ WhatsApp Web loaded successfully (fallback)")
            time.sleep(3)
            return True
        except TimeoutException:
            print("❌ WhatsApp Web failed to load")
            return False

def find_and_click_chat_improved(driver, contact_name, timeout=30):
    """Improved function to find and click on a specific chat"""
    print(f"🔎 Looking for chat with '{contact_name}'...")
    
    wait = WebDriverWait(driver, timeout)
    
    # Wait for chat list to be fully loaded
    time.sleep(5)
    
    # Multiple selector strategies to find chats
    chat_selectors = [
        "div[aria-label='Chat list'] > div > div",
        "#pane-side div[role='listitem']",
        "div[data-testid='chat-list'] div[role='listitem']",
        "div#pane-side > div > div > div > div",
        "div[role='row']"
    ]
    
    for selector in chat_selectors:
        try:
            print(f"🔍 Trying selector: {selector}")
            
            # Wait for elements to be present
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            
            # Get all chat items
            chat_items = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"📋 Found {len(chat_items)} potential chat items")
            
            if len(chat_items) == 0:
                continue
            
            # Search through each chat
            for i, chat in enumerate(chat_items):
                try:
                    # Get all text content from the chat element
                    chat_text = chat.text
                    
                    # Remove line breaks and extra spaces for matching
                    chat_text_normalized = " ".join(chat_text.split())
                    
                    # Debug: print first few chats
                    if i < 5:
                        print(f"  Chat {i}: {chat_text[:50]}...")
                    
                    # Check if contact name matches (case-insensitive, normalized)
                    contact_name_normalized = " ".join(contact_name.split())
                    if contact_name_normalized.lower() in chat_text_normalized.lower():
                        print(f"✅ MATCH FOUND at index {i}!")
                        print(f"   Full text: {chat_text}")
                        
                        # Scroll element into view
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chat)
                        time.sleep(1)
                        
                        # Try multiple click methods
                        click_successful = False
                        
                        # Method 1: Regular click
                        try:
                            chat.click()
                            click_successful = True
                            print("👆 Chat clicked (regular click)")
                        except Exception as e:
                            print(f"⚠️ Regular click failed: {e}")
                        
                        # Method 2: JavaScript click
                        if not click_successful:
                            try:
                                driver.execute_script("arguments[0].click();", chat)
                                click_successful = True
                                print("👆 Chat clicked (JavaScript click)")
                            except Exception as e:
                                print(f"⚠️ JavaScript click failed: {e}")
                        
                        # Method 3: ActionChains click
                        if not click_successful:
                            try:
                                ActionChains(driver).move_to_element(chat).click().perform()
                                click_successful = True
                                print("👆 Chat clicked (ActionChains click)")
                            except Exception as e:
                                print(f"⚠️ ActionChains click failed: {e}")
                        
                        if click_successful:
                            # Wait for conversation to load
                            time.sleep(3)
                            return wait_for_conversation_load(driver)
                        else:
                            print("❌ All click methods failed")
                            return False
                        
                except Exception as e:
                    print(f"⚠️ Error processing chat {i}: {e}")
                    continue
            
        except TimeoutException:
            print(f"⚠️ Selector timeout: {selector}")
            continue
        except Exception as e:
            print(f"⚠️ Error with selector {selector}: {e}")
            continue
    
    # If not found, try scrolling and searching again
    print("🔄 Chat not found in visible area, trying to scroll...")
    return scroll_and_find_chat(driver, contact_name)

def scroll_and_find_chat(driver, contact_name):
    """Scroll through chat list and search for contact"""
    print("📜 Scrolling through chat list...")
    
    try:
        # Find the chat list container
        chat_list_container = None
        container_selectors = [
            "#pane-side",
            "div[aria-label='Chat list']",
            "div[data-testid='chat-list']"
        ]
        
        for selector in container_selectors:
            try:
                chat_list_container = driver.find_element(By.CSS_SELECTOR, selector)
                if chat_list_container:
                    break
            except:
                continue
        
        if not chat_list_container:
            print("❌ Could not find chat list container")
            return False
        
        # Scroll and search
        last_height = driver.execute_script("return arguments[0].scrollHeight", chat_list_container)
        scroll_attempts = 0
        max_scrolls = 10
        
        while scroll_attempts < max_scrolls:
            # Scroll down
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", chat_list_container)
            time.sleep(2)
            
            # Try to find chat again
            chat_items = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
            
            for chat in chat_items:
                try:
                    chat_text_normalized = " ".join(chat.text.split())
                    contact_name_normalized = " ".join(contact_name.split())
                    
                    if contact_name_normalized.lower() in chat_text_normalized.lower():
                        print(f"✅ Found chat after scrolling!")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chat)
                        time.sleep(1)
                        chat.click()
                        time.sleep(3)
                        return wait_for_conversation_load(driver)
                except:
                    continue
            
            # Check if we've reached the end
            new_height = driver.execute_script("return arguments[0].scrollHeight", chat_list_container)
            if new_height == last_height:
                break
            
            last_height = new_height
            scroll_attempts += 1
        
        print("❌ Chat not found even after scrolling")
        return False
        
    except Exception as e:
        print(f"❌ Error during scrolling: {e}")
        return False

def wait_for_conversation_load(driver, timeout=30):
    """Wait for conversation panel to load"""
    print("⏳ Waiting for conversation to load...")
    
    wait = WebDriverWait(driver, timeout)
    
    conversation_indicators = [
        "div[data-testid='conversation-panel-body']",
        "div[data-testid='msg-container']",
        "div#main",
        "footer[data-testid='compose-panel']"
    ]
    
    for indicator in conversation_indicators:
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, indicator)))
            print(f"✅ Conversation loaded - found: {indicator}")
            time.sleep(3)
            return True
        except TimeoutException:
            continue
    
    print("❌ Could not confirm conversation loading")
    return False

def extract_contact_info(driver):
    """Extract contact name and phone number"""
    print("🔎 Extracting contact information...")
    
    contact_info = {"name": "Unknown", "phone": "Unknown"}
    
    try:
        # Get contact name from header
        name_selectors = [
            "header span[title]",
            "header div[title]",
            "div[data-testid='conversation-info-header'] span",
        ]
        
        for selector in name_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    name = element.get_attribute("title") or element.text
                    if name and len(name) > 0 and name not in ["", " ", "Type a message"]:
                        contact_info["name"] = name.strip()
                        print(f"✅ Contact name: {contact_info['name']}")
                        break
                if contact_info["name"] != "Unknown":
                    break
            except:
                continue
        
    except Exception as e:
        print(f"⚠️ Error extracting contact info: {e}")
    
    return contact_info

def extract_latest_message(driver):
    """Extract the latest message"""
    print("🔎 Extracting latest message...")
    
    time.sleep(3)
    
    message_selectors = [
        "div[data-testid='msg-container']",
        "div.message-in, div.message-out",
        "div[role='row']"
    ]
    
    for selector in message_selectors:
        try:
            containers = driver.find_elements(By.CSS_SELECTOR, selector)
            if containers:
                print(f"📋 Found {len(containers)} messages with: {selector}")
                
                # Get last message
                for container in reversed(containers):
                    try:
                        # Try to find text spans
                        text_spans = container.find_elements(By.CSS_SELECTOR, "span.selectable-text")
                        if text_spans:
                            message = " ".join([span.text for span in text_spans if span.text.strip()])
                            if message and len(message) > 5:
                                print(f"✅ Latest message: {message[:100]}...")
                                return message
                        
                        # Fallback: get all text
                        text = container.text.strip()
                        if text and len(text) > 5:
                            print(f"✅ Latest message (fallback): {text[:100]}...")
                            return text
                    except:
                        continue
        except:
            continue
    
    print("❌ Could not extract message")
    return "No message found"

def save_data_to_files(contact_info, latest_message):
    """Save extracted data"""
    try:
        with open("lastMessage.txt", "w", encoding="utf-8") as f:
            f.write(latest_message)
        print("✅ Message saved")
        
        with open("contactInfo.txt", "w", encoding="utf-8") as f:
            f.write(f"Name: {contact_info['name']}\nPhone: {contact_info['phone']}")
        print("✅ Contact info saved")
        
        data = {
            "contact_name": contact_info['name'],
            "phone_number": contact_info['phone'],
            "latest_message": latest_message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open("chatData.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ JSON saved")
        
        return True
    except Exception as e:
        print(f"❌ Error saving: {e}")
        return False

def submit_to_google_form(contact_info, latest_message):
    """Submit extracted data to Google Form"""
    print("\n" + "="*50)
    print("📤 SUBMITTING TO GOOGLE FORM")
    print("="*50)
    
    try:
        # Google Form URL and field IDs
        form_url = #add
        
        # Prepare form data
        #add your section ids and names
        payload = {
            : contact_info['name'],#add you id of section before colon
            : contact_info['phone'],#add you id of section before colon
            : latest_message#add you id of section before colon
        }
        
        print(f"📋 Submitting data:")
        print(f"   Name: {contact_info['name']}")
        print(f"   Phone: {contact_info['phone']}")
        print(f"   Message: {latest_message[:50]}...")
        
        # Create session with headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Submit to Google Form
        response = session.post(form_url, data=payload, timeout=30)
        
        if response.status_code == 200:
            print("✅ Form submitted successfully!")
            return True
        else:
            print(f"❌ Form submission failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during form submission: {e}")
        return False

def main():
    driver = None
    
    try:
        print("🚀 Starting enhanced WhatsApp scraper with ChromeDriver fixes...")
        
        # Fix ChromeDriver issues first
        fix_chromedriver_issues()
        
        # Create driver with multiple fallback methods
        driver = create_chrome_driver()
        
        if not driver:
            print("❌ Could not create Chrome driver with any method")
            print("\n🔧 Manual fix suggestions:")
            print("1. Update Chrome browser to latest version")
            print("2. Run: pip install --upgrade selenium webdriver-manager")
            print("3. Clear ChromeDriver cache: Delete ~/.wdm folder")
            print("4. Download ChromeDriver manually from https://chromedriver.chromium.org/")
            print("5. Restart your terminal/command prompt")
            return
        
        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)
        
        print("🌐 Opening WhatsApp Web...")
        driver.get("https://web.whatsapp.com")
        
        if not wait_for_whatsapp_load(driver):
            print("❌ Failed to load WhatsApp Web")
            return
        
        contact_name =   # CHANGE THIS to name you want
        
        if not find_and_click_chat_improved(driver, contact_name):
            print(f"❌ Could not find/click chat: '{contact_name}'")
            
            # Debug: Save screenshot
            driver.save_screenshot("debug_screenshot.png")
            print("📸 Screenshot saved as debug_screenshot.png")
            
            # Keep browser open for manual inspection
            input("❓ Press Enter to close browser (check it manually first)...")
            return
        
        contact_info = extract_contact_info(driver)
        latest_message = extract_latest_message(driver)
        
        save_data_to_files(contact_info, latest_message)
        
        # NEW: Submit to Google Form
        form_success = submit_to_google_form(contact_info, latest_message)
        
        print("\n" + "="*50)
        print("📊 EXTRACTION SUMMARY")
        print("="*50)
        print(f"Contact: {contact_info['name']}")
        print(f"Phone: {contact_info['phone']}")
        print(f"Message: {latest_message[:100]}...")
        print(f"Google Form: {'SUBMITTED ✅' if form_success else 'FAILED ❌'}")
        print("="*50)
        
        print("✅ Done!")
        
        # Optional: keep browser open
        input("Press Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n🔧 Additional troubleshooting steps:")
        print("1. Check if Chrome is running in the background and close it")
        print("2. Try running the script as administrator")
        print("3. Check Windows Defender/Antivirus - it might be blocking ChromeDriver")
        print("4. Try: pip uninstall selenium webdriver-manager && pip install selenium webdriver-manager")
        
    finally:
        if driver:
            try:
                print("🔄 Closing browser...")
                driver.quit()
                print("✅ Browser closed successfully")
            except Exception as e:
                print(f"⚠️ Error closing browser: {e}")

if __name__ == "__main__":
    main()

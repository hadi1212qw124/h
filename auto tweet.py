import random
import string
import time
import telebot
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# توكن البوت
TOKEN = ""
bot = telebot.TeleBot(TOKEN)

# بيانات المستخدمين وحالة النشر
user_data = {}
stopped_users = set()
ACCOUNTS_FILE = "accounts.json"

# تحميل البيانات من الملف
try:
    with open(ACCOUNTS_FILE, "r") as f:
        user_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    user_data = {}

# حفظ البيانات في الملف
def save_accounts():
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(user_data, f, indent=4)

# توليد رمز عشوائي
def generate_random_symbol():
    symbols = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/"
    return random.choice(symbols)

# التقاط لقطة شاشة وإرسالها إلى المستخدم
def send_screenshot(driver, chat_id, message):
    screenshot_path = f"screenshot_{chat_id}.png"
    driver.save_screenshot(screenshot_path)
    with open(screenshot_path, "rb") as screenshot:
        bot.send_photo(chat_id, screenshot, caption=message)

# استقبال البريد الإلكتروني من المستخدم
@bot.message_handler(commands=['tweet'])
def start_tweet_process(message):
    chat_id = message.chat.id
    if chat_id in stopped_users:
        stopped_users.remove(chat_id)  # إزالة المستخدم من قائمة الإيقاف عند إعادة التشغيل
    user_data[chat_id] = {}
    bot.send_message(chat_id, "يرجى إدخال البريد الإلكتروني:")

@bot.message_handler(commands=['stop'])
def stop_tweeting(message):
    chat_id = message.chat.id
    stopped_users.add(chat_id)
    bot.send_message(chat_id, "تم إيقاف النشر.")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'email' not in user_data[message.chat.id])
def handle_email(message):
    chat_id = message.chat.id
    user_data[chat_id]['email'] = message.text
    bot.send_message(chat_id, "تم حفظ البريد الإلكتروني، الرجاء إدخال اسم المستخدم:")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'username' not in user_data[message.chat.id])
def handle_username(message):
    chat_id = message.chat.id
    user_data[chat_id]['username'] = message.text
    bot.send_message(chat_id, "تم حفظ اسم المستخدم، الرجاء إدخال كلمة المرور:")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'password' not in user_data[message.chat.id])
def handle_password(message):
    chat_id = message.chat.id
    user_data[chat_id]['password'] = message.text
    bot.send_message(chat_id, "تم حفظ كلمة المرور، الرجاء إدخال عدد مرات التكرار:")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'repeat_count' not in user_data[message.chat.id])
def handle_repeat_count(message):
    chat_id = message.chat.id
    try:
        user_data[chat_id]['repeat_count'] = int(message.text)
        bot.send_message(chat_id, "تم حفظ عدد التكرارات، الرجاء إدخال نص التغريدة:")
    except ValueError:
        bot.send_message(chat_id, "يرجى إدخال رقم صحيح لعدد مرات التكرار.")

@bot.message_handler(func=lambda message: message.chat.id in user_data and 'message' not in user_data[message.chat.id])
def handle_tweet_message(message):
    chat_id = message.chat.id
    user_data[chat_id]['message'] = message.text
    save_accounts()
    bot.send_message(chat_id, "تم حفظ البيانات، سيتم البدء في نشر التغريدات.")
    post_tweets(chat_id)

# تنفيذ النشر على تويتر
def post_tweets(chat_id):
    if chat_id in stopped_users:
        bot.send_message(chat_id, "تم إيقاف النشر لهذه الجلسة.")
        return

    data = user_data.get(chat_id)
    if not data:
        bot.send_message(chat_id, "لم يتم العثور على بيانات. يرجى بدء العملية من جديد.")
        return

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://twitter.com/login")
    wait = WebDriverWait(driver, 20)
    
    try:
        bot.send_message(chat_id, "جاري محاولة تسجيل الدخول...")
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        email_input.send_keys(data['email'])
        email_input.send_keys(Keys.RETURN)
        time.sleep(5)
        
        try:
            username_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
            username_input.send_keys(data['username'])
            username_input.send_keys(Keys.RETURN)
            time.sleep(5)
        except:
            pass
        
        password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_input.send_keys(data['password'])
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
        
        if "home" in driver.current_url:
            bot.send_message(chat_id, "تم تسجيل الدخول بنجاح! جاري بدء النشر...")
        else:
            bot.send_message(chat_id, "فشل تسجيل الدخول. الرجاء التحقق من البيانات وإعادة المحاولة.")
            send_screenshot(driver, chat_id, "هذه لقطة شاشة للمشكلة، يرجى التحقق من البيانات المدخلة.")
            driver.quit()
            return
        
        for i in range(1, data['repeat_count'] + 1):
            if chat_id in stopped_users:
                bot.send_message(chat_id, "تم إيقاف النشر.")
                driver.quit()
                return

            tweet = f"{data['message']} {i}{generate_random_symbol()}"
            
            try:
                tweet_box = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Tweet text' or @role='textbox']")))
                tweet_box.send_keys(tweet)
                time.sleep(2)
                
                tweet_box.send_keys(Keys.CONTROL, Keys.ENTER)
                bot.send_message(chat_id, f"تم نشر التغريدة: {tweet}")
                time.sleep(3)
            except Exception as e:
                bot.send_message(chat_id, f"خطأ أثناء النشر: {str(e)}")
                send_screenshot(driver, chat_id, "تعذر نشر التغريدة، تحقق من المشكلة في لقطة الشاشة.")
                driver.quit()
                return
        
        bot.send_message(chat_id, "تم الانتهاء من نشر جميع التغريدات.")
    finally:
        driver.quit()

bot.polling(none_stop=True)

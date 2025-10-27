import io
import os
import re
import sys
import time
import logging
import requests
import traceback
from functools import wraps
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service 
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.common.action_chains import ActionChains

service = Service()
options = webdriver.ChromeOptions() 
options.add_argument('--headless') 
options.add_argument('--window-size=1366,764')
options.add_argument('--disable-gpu')
options.add_argument("--no-sandbox")
options.add_argument("--disable-extensions")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10, poll_frequency=1)
wait_min = WebDriverWait(driver, 2, poll_frequency=0.5)

bot_token = os.getenv('BOT_TOKEN')
chat_id = os.getenv('CHAT_ID')

logging.basicConfig(
    level=logging.INFO, 
    filename="reserve_log.txt",
    filemode="a",
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S'
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def send_telegram_message(bot_token, chat_id, message):
    try:
            
        # Удаляем все HTML теги
        text_message = re.sub(r'<[^>]+>', '', message)
                
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text_message
        }
        
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()
        
        #print(f"✅ Ответ от Telegram: {result}")
        logging.info('Сообщение успешно отправлено в Телеграм')
        return result
        
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")
        logging.warning(f"Ошибка отправки в Telegram: {e}")
        return {"error": str(e)}

def extract_traceback_only(error_traceback):
    lines = error_traceback.split('\n')
    traceback_lines = []
    
    for line in lines:
        if 'Stacktrace:' in line or 'GetHandleVerifier' in line:
            break
        traceback_lines.append(line)
    
    return '\n'.join(traceback_lines).strip()


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logging.info(f"Start")
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(f"Finish ({execution_time:.2f} sec)")
        
        return result
    return wrapper


@timer
def reserve():

    driver.get('https://my.ordage.com/')

    email = wait.until(EC.element_to_be_clickable((By.NAME, "login")))
    email.send_keys(os.getenv('EMAIL'))

    password = wait.until(EC.element_to_be_clickable((By.NAME, "password")))
    password.send_keys(os.getenv('PASSWORD'))

    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn-login"))).click()
    time.sleep(1)

    driver.get('https://my.ordage.com/55f67cd753a10ad5.6167.036bad/orders')

    # Клик на выбор склада
    #//label[text()='Склад']/following-sibling::div[@class='name'] резервный XPATH
    warehouse = (By.XPATH, "(//div[@class='name'])[2]")
    warehouse_trigger = wait.until(EC.element_to_be_clickable(warehouse))
    warehouse_trigger.click()
        
    # Выбор склада
    slct_warehouse_xpath = (By.XPATH, "//li[text()='Основний склад']")
    slct_warehouse = wait.until(EC.element_to_be_clickable(slct_warehouse_xpath))
    slct_warehouse.click()

    # ждем пока прогрузится страница
    wait.until(EC.element_to_be_clickable((By.NAME, "datatable-orders_length")))

    # меню фильтра
    wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "filter-name"))).click()

    # выбираем фильтр "ЗАРЕЗЕРВУВАТИ"
    filter_check = (By.XPATH, "//span[@class='name' and text()='ЗАРЕЗЕРВУВАТИ']")
    wait.until(EC.element_to_be_clickable(filter_check)).click()
    time.sleep(2)

    # открываем количество заказов
    #wait.until(EC.element_to_be_clickable((By.NAME, "datatable-orders_length"))).click()

    # выбираем 50 
    #wait.until(EC.element_to_be_clickable((By.XPATH, "//option[@value='50']"))).click()
    #time.sleep(3)

    # сортировка по дате
    #wait.until(EC.element_to_be_clickable((By.XPATH, "//th[@data-key='order_date']"))).click()

    # выделяем все заказы на странице
    #actions = ActionChains(driver)
    all_orders = (By.CSS_SELECTOR, "label.checkbox")
    all_orders_element = wait.until(EC.element_to_be_clickable(all_orders))
    #actions.move_to_element(all_orders_element).perform()
    all_orders_element.click()
    time.sleep(1)   

    # Кликаем на "груповые действия"
    menu_group_act = (By.XPATH, "//a[@data-original-title='Групові дії …']")
    wait.until(EC.element_to_be_clickable(menu_group_act)).click()
    time.sleep(1)

    # Выбрать "Зарезервувати"
    #//a[contains(@class, 'buttons-html5')] //li[text()='Зарезервувати']
    shipping_option_xpath = (By.XPATH, "//li[text()='Зарезервувати']")  
    shipping_option = wait.until(EC.element_to_be_clickable(shipping_option_xpath))
    shipping_option.click()
    time.sleep(1)

    try: # проверяем появилось ли окно алерта
        alert = (By.XPATH,"//div[@class='ui-pnotify-text']")
        wait_min.until(EC.visibility_of_element_located(alert))
        logging.info('Нет товаров для резервирования')
        print('Нет товаров для резервирования')
    except TimeoutException: 
        try: # проверяем на красные галочки
           not_enough = (By.XPATH, '//i[contains (@class, "not_enough_btn btn")]')
           wait_min.until(EC.visibility_of_element_located(not_enough))
           message = f"❌Autoreserve ERROR: Недостатня кількість товару на складі"
           send_telegram_message(bot_token, chat_id, message)
           logging.warning('Недостатня кількість товару на складі')
           print('Недостатня кількість товару на складі')
        except TimeoutException: # Нажимаем кнопку зарезервувати 
            driver.find_element(By.XPATH, "(//button[@data-action='add'])[15]").click()
            logging.info('Товары успешно зарезервированы')
            print('Товары успешно зарезервированы')
    finally: 
        driver.quit
    

try:
    reserve() 
except Exception as e: 
    error_traceback = traceback.format_exc()
    clean_traceback = extract_traceback_only(error_traceback)
    message = f"❌ Autoreserve ERROR:\n{clean_traceback}"
    success = send_telegram_message(bot_token, chat_id, message)  
    logging.warning(e)
    logging.warning(clean_traceback)
    print(clean_traceback)  

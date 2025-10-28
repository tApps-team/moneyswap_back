import random
import requests
import json

from time import sleep

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC

from config import SELENIUM_DRIVER

from .queries import add_to_json_dict



field_name_set = {
    'Курсов обмена',
    'Сумма резервов',
    'Возраст',
    'Страна',
 }                


def exchange_info_generator():
    info = {}
    
    field_model_names = (
        'course_count',
        'reserve_amount',
        'age',
        'country',
    )

    for field in field_model_names:
        value = yield
        info[field] = value
    
    # wait call next() to return data
    yield

    yield info

    # course_count = yield

    # # print('1 value done')
    # info['course_count'] = course_count

    # reserve_amount = yield

    # # print('2 value done')
    # info['reserve_amount'] = reserve_amount

    # age = yield

    # # print('3 value done')
    # info['age'] = age

    # country = yield

    # # print('4 value done')
    # info['country'] = country

    # wait to return data 
    # yield

    # print('ready to return')
    # yield info

    # print('get it')


# def parse_exchange_info(exchange_list: list[tuple[int, str, str]]):
#     # exchange_name = en_name.lower()

#     options = Options()
#     try:
#         driver = webdriver.Remote(f'http://{SELENIUM_DRIVER}:4444', options=options)

#         for exchange in exchange_list:
#             _id, en_name, exchange_marker = exchange
#             url = f'https://www.bestchange.ru/{en_name.lower()}-exchanger.html'
#             try:
#                 driver.get(url)
#                 sign_in_wait = WebDriverWait(driver, timeout=40)\
#                                             .until(EC.presence_of_element_located((By.CLASS_NAME,
#                                                                                    'exch_info_table')))

#                 rows = sign_in_wait.find_elements(By.TAG_NAME, 'tr')

#                 # rows = sign_in_wait.find_element(By.CLASS_NAME, 'exch_info_table')\
#                 #                 .find_elements(By.TAG_NAME, 'tr')
                
#                 # print(rows)
            
#             # initialize and run generator
#                 exchange_info_gen = exchange_info_generator()
#                 next(exchange_info_gen)

#                 for row in rows:
#                     start_text = row.find_elements(By.TAG_NAME,'td')[0].text

#                     # print(start_text)

#                     if start_text.startswith(tuple(field_name_set)):
#                         td_list = row.find_elements(By.TAG_NAME, 'td')
#                         idx = 2 if start_text.startswith('Страна') else 1
#                         value = td_list[idx].text
#                         exchange_info_gen.send(value)
#                 # get data from generator
#                 exchange_info = next(exchange_info_gen)
#                 exchange_info_gen.close()

#                 update_exchange_to_db(_id,
#                                       exchange_marker,
#                                       exchange_info)
                
#             except Exception as ex:
#                 print(ex)
#                 continue
#                         # .find_elements(By.XPATH, '//div[starts-with(@class, "review_block")]')  
#         # parse_reviews(driver, exchange_name, marker)

#     except Exception as ex:
#         print(ex)
#     finally:
#         driver.quit()


def parse_exchange_info(exchange_list: list[tuple[int, str]]):
    # exchange_name = en_name.lower()

    options = Options()
    filename = './new_age.json'

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    exchange_names = set(data.keys())

    try:
        driver = webdriver.Remote(f'http://{SELENIUM_DRIVER}:4444', options=options)

        for exchange in exchange_list:
            _id, en_name = exchange
            
            if en_name in exchange_names:
                print(f'{en_name} skipped')
                continue

            url = f'https://www.bestchange.ru/{en_name.lower()}-exchanger.html'
            try:
                driver.get(url)
                sign_in_wait = WebDriverWait(driver, timeout=40)\
                                            .until(EC.presence_of_element_located((By.CLASS_NAME,
                                                                                   'exch_info_table')))

                rows = sign_in_wait.find_elements(By.TAG_NAME, 'tr')

                # rows = sign_in_wait.find_element(By.CLASS_NAME, 'exch_info_table')\
                #                 .find_elements(By.TAG_NAME, 'tr')
                
                # print(rows)
            
            # initialize and run generator
                exchange_info_gen = exchange_info_generator()
                next(exchange_info_gen)

                for row in rows:
                    start_text = row.find_elements(By.TAG_NAME,'td')[0].text

                    # print(start_text)

                    if start_text.startswith(tuple(field_name_set)):
                        td_list = row.find_elements(By.TAG_NAME, 'td')
                        idx = 2 if start_text.startswith('Страна') else 1
                        value = td_list[idx].text
                        exchange_info_gen.send(value)
                # get data from generator
                exchange_info = next(exchange_info_gen)
                exchange_info_gen.close()

                add_to_json_dict(filename,
                                 en_name,
                                 exchange_info['age'])
                
            except Exception as ex:
                print(ex)
                continue
                        # .find_elements(By.XPATH, '//div[starts-with(@class, "review_block")]')  
        # parse_reviews(driver, exchange_name, marker)

    except Exception as ex:
        print(ex)
    finally:
        driver.quit()



# def parse_exchange_info(exchange: tuple[int, str, str]):
#     _id, en_name, exchange_marker = exchange
#     url = f'https://www.bestchange.ru/{en_name.lower()}-exchanger.html'

#     try:
#         resp = requests.get(url=url,
#                             timeout=5)
#     except Exception as ex:
#         print('PARSE EXCHANGE INFO ERROR', ex)
#         pass
    
#     else:
#         soup = BeautifulSoup(resp.text, 'lxml')

#         info_table = soup.find('div',
#                                class_='intro')\
#                             .find('table',
#                                   class_='exch_info_table')
        
#         # initialize and run generator
#         exchange_info_gen = exchange_info_generator()
#         next(exchange_info_gen)

#         if info_table:
#             try:
#                 rows = info_table.find_all('tr')
                
#                 for row in rows:
#                     row_text: str = row.find('td').text[:-1]

#                     if row_text.startswith(tuple(field_name_set)):
#                         td_list = row.find_all('td')
#                         idx = 2 if row_text.startswith('Страна') else 1
#                         value = td_list[idx].text
#                         exchange_info_gen.send(value)
#                     # else:
#                     #     print('noooo')
#                 # get data from generator
#                 exchange_info = next(exchange_info_gen)
#                 exchange_info_gen.close()

#                 # print('exchange_info', exchange_info)
#                 # print(en_name)
#                 update_exchange_to_db(_id,
#                                     exchange_marker,
#                                     exchange_info)
#             except Exception as ex:
#                 print(ex)
#                 pass
#     finally:
#         rnd_count = random.randint(3, 6)
#         sleep(rnd_count)

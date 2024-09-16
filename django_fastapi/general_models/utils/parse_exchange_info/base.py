import random
import requests

from time import sleep

from bs4 import BeautifulSoup

from .queries import update_exchange_to_db



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



def parse_exchange_info(exchange: tuple[int, str, str]):
    _id, en_name, exchange_marker = exchange
    url = f'https://www.bestchange.ru/{en_name.lower()}-exchanger.html'

    try:
        resp = requests.get(url=url,
                            timeout=5)
    except Exception as ex:
        print('PARSE EXCHANGE INFO ERROR', ex)
        pass
    
    else:
        soup = BeautifulSoup(resp.text, 'lxml')

        info_table = soup.find('div',
                               class_='intro')\
                            .find('table',
                                  class_='exch_info_table')
        
        # initialize and run generator
        exchange_info_gen = exchange_info_generator()
        next(exchange_info_gen)

        if info_table:
            try:
                rows = info_table.find_all('tr')
                
                for row in rows:
                    row_text: str = row.find('td').text[:-1]

                    if row_text.startswith(tuple(field_name_set)):
                        td_list = row.find_all('td')
                        idx = 2 if row_text.startswith('Страна') else 1
                        value = td_list[idx].text
                        exchange_info_gen.send(value)
                    # else:
                    #     print('noooo')
                # get data from generator
                exchange_info = next(exchange_info_gen)
                exchange_info_gen.close()

                # print('exchange_info', exchange_info)
                # print(en_name)
                update_exchange_to_db(_id,
                                    exchange_marker,
                                    exchange_info)
            except Exception as ex:
                print(ex)
                pass
    finally:
        rnd_count = random.randint(3, 6)
        sleep(rnd_count)

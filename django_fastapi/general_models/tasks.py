import asyncio

from time import time

from celery import shared_task
from celery_once import QueueOnce

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from django.db.models import Value, CharField, Q

from django.db import connection

from cash import models as cash_models
from no_cash import models as no_cash_models
from partners import models as partner_models

from cash.utils.cache import get_or_set_cash_directions_cache, new_get_or_set_cash_directions_cache
from no_cash.utils.cache import get_or_set_no_cash_directions_cache, new_get_or_set_no_cash_directions_cache

from config import SELENIUM_DRIVER

from .models import NewBaseReview, Exchanger, Review
from .utils.periodic_tasks import try_get_xml_file

from .utils.parse_reviews.selenium import parse_reviews
from .utils.parse_exchange_info.base import parse_exchange_info
from .utils.tasks import (new_try_update_courses,
                          try_update_courses,
                          generate_cash_direction_dict,
                          generate_no_cash_direction_dict)
from .utils.endpoints import (new_send_review_notifitation_to_exchange_admin,
                              new_send_comment_notifitation_to_exchange_admin,
                              new_send_comment_notifitation_to_review_owner)
from .utils.parsers import parse_xml_and_create_or_update_directions


#Задача для периодического удаления отзывов и комментариев
#со статусом "Отклонён" из БД
@shared_task(name='delete_cancel_reviews')
def delete_cancel_reviews():
    # NewBaseReview.objects.filter(status='Отклонён').delete()
    # new
    Review.objects.filter(status='Отклонён').delete()



#WITH SELENIUM
#Фоновая задача парсинга отзывов и комментариев
#для всех обменников из БД при запуске сервиса
@shared_task
def parse_reviews_with_start_service():
    # driver = webdriver.Remote(f'http://localhost:4444', options=options)
    # print('DRIVER', driver)
    try:
        # driver = webdriver.Firefox()
        options = Options()
        driver = webdriver.Remote(f'http://{SELENIUM_DRIVER}:4444', options=options)

        for marker in ('no_cash', 'cash'):
            model = no_cash_models if marker == 'no_cash' else cash_models
            exchanges = model.Exchange.objects.values('en_name').all()
            exchange_name_list = [exchange['en_name'].lower() for exchange in exchanges]
            for exchange_name in exchange_name_list:
                parse_reviews(driver,
                              exchange_name,
                              marker)
    except (Exception, BaseException) as ex:
        print('SELENIUM ERROR', ex)
    finally:
        driver.quit()


#Фоновая задача парсинга отзывов и комментариев обменника
#при добавлении обменника через админ панель
@shared_task(acks_late=True, task_reject_on_worker_lost=True)
def parse_reviews_for_exchange(exchange_name: str, marker: str):
    exchange_name = exchange_name.lower()

    options = Options()
    try:
        driver = webdriver.Remote(f'http://{SELENIUM_DRIVER}:4444', options=options)
        parse_reviews(driver, exchange_name, marker)
    except Exception as ex:
        print(ex)
    finally:
        driver.quit()


@shared_task(name='update_popular_count_direction_time')
def update_popular_count_direction():
    # cash_direction = cash_models.Direction.objects
    # no_cash_directions = no_cash_models.Direction.objects
    
    #new
    cash_direction = cash_models.NewDirection.objects
    no_cash_directions = no_cash_models.NewDirection.objects


    cash_direction.update(popular_count=0)
    no_cash_directions.update(popular_count=0)


################
@shared_task(name='parse_actual_courses')
def parse_actual_courses():
    # print(len(connection.queries))

    # no_cash_direction_model = no_cash_models.Direction
    # no_cash_exchange_direction_model = no_cash_models.ExchangeDirection
    # try_update_courses(no_cash_direction_model,
    #                    no_cash_exchange_direction_model)
    #new
    no_cash_direction_model = no_cash_models.NewDirection
    no_cash_exchange_direction_model = no_cash_models.NewExchangeDirection
    new_try_update_courses(no_cash_direction_model,
                           no_cash_exchange_direction_model)

    # cash_direction_model = cash_models.Direction
    # cash_exchange_direction_model = cash_models.ExchangeDirection
    # try_update_courses(cash_direction_model,
    #                    cash_exchange_direction_model)
    #new
    cash_direction_model = cash_models.NewDirection
    cash_exchange_direction_model = cash_models.NewExchangeDirection
    new_try_update_courses(cash_direction_model,
                           cash_exchange_direction_model)

    # print(connection.queries[-5:])
    # print(len(connection.queries))


# parse_actual_exchanges_info

@shared_task(name='parse_actual_exchanges_info')
def parse_actual_exchanges_info():

    def annotate_field(exchange_marker):
        return Value(exchange_marker,
                     output_field=CharField())

    no_cash_exchanges = no_cash_models.Exchange.objects\
                                                .annotate(exchange_marker=annotate_field('no_cash'))\
                                                .values_list('pk',
                                                             'en_name',
                                                             'exchange_marker')\
                                                .all()
    cash_exchanges = cash_models.Exchange.objects\
                                            .annotate(exchange_marker=annotate_field('cash'))\
                                            .values_list('pk',
                                                         'en_name',
                                                         'exchange_marker')\
                                            .all()
    exchange_list = no_cash_exchanges.union(cash_exchanges)

    parse_exchange_info(exchange_list)
    # for exchange in exchange_list:
    #     parse_exchange_info(exchange)


@shared_task(name='periodic_delete_unlinked_exchange_records')
def periodic_delete_unlinked_exchange_records():
    batch_size = 1000

    exchangedirection_delete_filter = Q(exchange_id__isnull=True)

    # deleted_tuples_list = [
    #     ('no_cash', no_cash_models.ExchangeDirection),
    #     ('cash', cash_models.ExchangeDirection),
    #     ('partner', partner_models.Direction),
    #     ('partner', partner_models.CountryDirection),
    #     ('partner', partner_models.NonCashDirection),
    #     ('partner', partner_models.DirectionRate),
    #     ('partner', partner_models.CountryDirectionRate),
    #     ('partner', partner_models.NonCashDirectionRate),
    # ]

    # new
    deleted_tuples_list = [
        ('no_cash', no_cash_models.NewExchangeDirection),
        ('cash', cash_models.NewExchangeDirection),
        ('partner', partner_models.NewDirection),
        ('partner', partner_models.NewCountryDirection),
        ('partner', partner_models.NewNonCashDirection),
        ('partner', partner_models.NewDirectionRate),
        ('partner', partner_models.NewCountryDirectionRate),
        ('partner', partner_models.NewNonCashDirectionRate),
    ]


    for marker, _model in deleted_tuples_list:
        _model: cash_models.NewExchangeDirection # как пример для аннотации

        if batch_size <= 0:
            print(f'end with RETURN {batch_size}')
            return
        
        record_pks_on_delete = _model.objects.filter(exchangedirection_delete_filter)\
                                                .values_list('pk',
                                                             flat=True)[:batch_size]

        len_records_on_delete = len(record_pks_on_delete)

        if batch_size < len_records_on_delete:
            batch_size = 0
        else:
            batch_size -= len_records_on_delete

        print(f'{marker} {_model}')
        print(f'len queryset {len_records_on_delete}')
        print(f'batch size {batch_size}')
        _model.objects.filter(pk__in=record_pks_on_delete).delete()

    else:
        print(f'end with ELSE {batch_size}')



#new (одна задача на добавление и обновление направлений)
@shared_task(base=QueueOnce,
             once={'graceful': True},
             name='create_update_directions_for_exchanger')
def create_update_directions_for_exchanger(exchange_id: int):
    try:
        exchange = Exchanger.objects.get(pk=exchange_id)

        if exchange.active_status in ('disabled', 'scam', 'skip'):
            return
        
        start_cache_time = time()

        all_cash_directions = new_get_or_set_cash_directions_cache()

        all_no_cash_directions = new_get_or_set_no_cash_directions_cache()

        print(f'время получения направлений из кэша - {time() - start_cache_time} sec')

        if all_cash_directions or all_no_cash_directions:
            # print(f'request to exchanger {exchange.name}')
            start_time = time()
            xml_file = try_get_xml_file(exchange)
            print(f'Задача для Exchanger {exchange.name}! время получения xml {time() - start_time} sec')
            # print('get xml file', time() - start_time)
        
            if xml_file is not None and exchange.is_active:
                start_generate_time = time()
                direction_dict = {}

                if all_cash_directions:
                    generate_cash_direction_dict(direction_dict,
                                                 all_cash_directions[-1])
                if all_no_cash_directions:
                    generate_no_cash_direction_dict(direction_dict,
                                                    all_no_cash_directions)

                print(f'время генерации словаря направлений - {time() - start_generate_time} sec')
                if direction_dict:
                    parse_xml_and_create_or_update_directions(exchange,
                                                              xml_file,
                                                              direction_dict)

    except Exception as ex:
        print(ex, exchange_id)


        # all_no_cash_directions = get_or_set_no_cash_directions_cache()
        
        # if all_no_cash_directions:
        #     # direction_list = get_no_cash_direction_set_for_creating(all_no_cash_directions,
        #     #                                                         exchange)
                    
        #     # if direction_list:
        #         print(f'no cash {exchange.name}')
        #         start_time = time()
        #         xml_file = try_get_xml_file(exchange)
        #         print(f'безнал время на получения xml файла {time() - start_time} sec')

        #         if xml_file is not None and exchange.is_active:
        #             #
        #             # if exchange.name == 'Bixter':
        #             #     print('Bixter', xml_file)
        #             #
        #             direction_dict = generate_direction_dict(all_no_cash_directions)
        #             new_run_no_cash_background_tasks(exchange,
        #                                              direction_dict,
        #                                              xml_file)



@shared_task
def send_review_notification_to_exchange_admin_task(user_id, exchange_id, review_id):
    asyncio.run(new_send_review_notifitation_to_exchange_admin(user_id, exchange_id, review_id))


@shared_task
def send_comment_notification_to_exchange_admin_task(user_id, exchange_id, review_id):
    asyncio.run(new_send_comment_notifitation_to_exchange_admin(user_id, exchange_id, review_id))


@shared_task
def send_comment_notification_to_review_owner_task(user_id, exchange_id, review_id):
    asyncio.run(new_send_comment_notifitation_to_review_owner(user_id, exchange_id, review_id))
from celery import shared_task, current_task
from celery.app.task import Task

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from django.db.models import Value, CharField

from django.db import connection

from cash import models as cash_models
from no_cash import models as no_cash_models
from partners import models as partner_models

from config import SELENIUM_DRIVER

from .utils.parse_reviews.selenium import parse_reviews
from .utils.parse_exchange_info.base import parse_exchange_info
from .utils.tasks import try_update_courses


#Задача для периодического удаления отзывов и комментариев
#со статусом "Отклонён" из БД
@shared_task(name='delete_cancel_reviews')
def delete_cancel_reviews():
    cash_models.Review.objects.filter(status='Отклонён').delete()
    no_cash_models.Review.objects.filter(status='Отклонён').delete()
    partner_models.Review.objects.filter(status='Отклонён').delete()

    cash_models.Comment.objects.filter(status='Отклонён').delete()
    no_cash_models.Comment.objects.filter(status='Отклонён').delete()
    partner_models.Comment.objects.filter(status='Отклонён').delete()


#WITH SELENIUM
#Фоновая задача парсинга отзывов и комментариев
#для всех обменников из БД при запуске сервиса
@shared_task(acks_late=True, task_reject_on_worker_lost=True)
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
    cash_direction = cash_models.Direction.objects.all()
    no_cash_directions = no_cash_models.Direction.objects.all()

    cash_direction.update(popular_count=0)
    no_cash_directions.update(popular_count=0)



# @shared_task(name='parse_no_cash_courses')
# def parse_no_cash_courses():
#     no_cash_directions = no_cash_models.Direction.objects.all()
#     #
#     cash_directions = cash_models.Direction.objects.all()
#     #

#     for direction in no_cash_directions:
#         best_course = no_cash_models.ExchangeDirection.objects.filter(direction_id=direction.pk)\
#                                                                 .order_by('-out_count',
#                                                                           '-in_count')\
#                                                                 .values_list('in_count',
#                                                                              'out_count')\
#                                                                 .first()
#         if best_course:
#             in_count, out_count = best_course

#             if out_count == 1:
#                 actual_course = out_count / in_count
#             else:
#                 actual_course = out_count
#             direction.actual_course = actual_course
#         else:
#             direction.actual_course = None
            
#         direction.save()

#     for direction in cash_directions:
#         best_course = cash_models.ExchangeDirection.objects.filter(direction_id=direction.pk)\
#                                                                 .order_by('-out_count',
#                                                                           '-in_count')\
#                                                                 .values_list('in_count',
#                                                                              'out_count')\
#                                                                 .first()
#         if best_course:
#             in_count, out_count = best_course

#             if out_count == 1:
#                 actual_course = out_count / in_count
#             else:
#                 actual_course = out_count
#             direction.actual_course = actual_course
#         else:
#             direction.actual_course = None
            
#         direction.save()



################
@shared_task(name='parse_actual_courses')
def parse_actual_courses():
    # print(len(connection.queries))

    no_cash_direction_model = no_cash_models.Direction
    no_cash_exchange_direction_model = no_cash_models.ExchangeDirection
    try_update_courses(no_cash_direction_model,
                       no_cash_exchange_direction_model)

    cash_direction_model = cash_models.Direction
    cash_exchange_direction_model = cash_models.ExchangeDirection
    try_update_courses(cash_direction_model,
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
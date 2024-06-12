from typing import List
from collections import defaultdict
from datetime import timedelta, datetime

from django.conf import settings
from django.db import connection
from django.db.models import Count, Q

from fastapi import HTTPException

import no_cash.models as no_cash_models
import cash.models as cash_models
import partners.models as partner_models

from cash.models import ExchangeDirection as CashExDir, City, Country, Direction as CashDirection
from no_cash.models import ExchangeDirection as NoCashExDir, Direction as NoCashDirection

from general_models.models import Valute, en_type_valute_dict
from general_models.schemas import ValuteModel, EnValuteModel, MultipleName, ReviewCountSchema
from general_models.utils.http_exc import review_exception_json


round_valute_dict = {
    'BTC': 5,
    'ETH': 3,
    'Криптовалюта': 2,
}


positive_review_count_filter = filter=Q(exchange__reviews__moderation=True) \
                                        & Q(exchange__reviews__grade='1')
neutral_review_count_filter = filter=Q(exchange__reviews__moderation=True) \
                                        & Q(exchange__reviews__grade='0')
negative_review_count_filter = filter=Q(exchange__reviews__moderation=True) \
                                        & Q(exchange__reviews__grade='-1')
# neutral_review_count_filter = Count('exchange__reviews',
#                                         filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='0'))
# negative_review_count_filter = Count('exchange__reviews',
#                                         filter=Q(exchange__reviews__moderation=True) & Q(exchange__reviews__grade='-1'))


def round_valute_values(exchange_direction_dict: dict):

    '''
    Округляет значения "min_amount" и "max_amount"
    '''

    try:
        valute_from = exchange_direction_dict['valute_from']
        type_valute_from = exchange_direction_dict['type_valute_from']
        
        min_amount = float(exchange_direction_dict['min_amount'].split()[0])
        max_amount = float(exchange_direction_dict['max_amount'].split()[0])

        if valute_from in round_valute_dict:
            min_amount = round(min_amount, round_valute_dict[valute_from])
            max_amount = round(max_amount, round_valute_dict[valute_from])
        elif type_valute_from in round_valute_dict:
            min_amount = round(min_amount, round_valute_dict[type_valute_from])
            max_amount = round(max_amount, round_valute_dict[type_valute_from])
        else:
            min_amount = int(min_amount)
            max_amount = int(max_amount)
        
        exchange_direction_dict['min_amount'] = f'{min_amount}'
        exchange_direction_dict['max_amount'] = f'{max_amount}'
    except Exception:
        pass


def try_generate_icon_url(obj: Country | Valute) -> str | None:
    '''
    Генерирует путь до иконки переданного объекта.
    '''
    
    icon_url = None

    if obj.icon_url.name:
        icon_url = settings.PROTOCOL + settings.SITE_DOMAIN\
                                            + obj.icon_url.url
    return icon_url


def generate_image_icon(icon_url: str):
    return settings.PROTOCOL + settings.SITE_DOMAIN\
                                + icon_url.url


def get_exchange_direction_list(queries: List[NoCashExDir | CashExDir],
                                valute_from: str,
                                valute_to: str,
                                city: str = None):
    '''
    Возвращает список готовых направлений с необходимыми данными
    '''
    
    valute_from_obj = valute_to_obj = None

    direction_list = []

    exchange_marker = 'no_cash'

    partner_link_pattern = f'&cur_from={valute_from}&cur_to={valute_to}'
    
    if city:
        partner_link_pattern += f'&city={city}'
        exchange_marker = 'cash'

    for _id, query in enumerate(queries, start=1):
        if query.exchange.__dict__.get('partner_link') and query.exchange.__dict__.get('period_for_create'):
            query.exchange.__dict__['partner_link'] += partner_link_pattern

        if valute_from_obj is None:
            valute_from_obj = query.direction.valute_from

        icon_url_valute_from = try_generate_icon_url(valute_from_obj)
        type_valute_from = valute_from_obj.type_valute

        if valute_to_obj is None:
            valute_to_obj = query.direction.valute_to

        icon_url_valute_to = try_generate_icon_url(valute_to_obj)
        type_valute_to = valute_to_obj.type_valute

        exchange_direction = query.__dict__ | query.exchange.__dict__
        exchange_direction['id'] = _id
        exchange_direction['exchange_id'] = query.exchange.id
        exchange_direction['review_count'] = ReviewCountSchema(
            positive=query.positive_review_count,
            neutral=query.neutral_review_count,
            negative=query.negative_review_count,
            )
        
        if not hasattr(query,'exchange_marker'):
            exchange_direction['exchange_marker'] = exchange_marker

        exchange_direction['name'] = MultipleName(name=exchange_direction['name'],
                                                  en_name=exchange_direction['en_name'])
        exchange_direction['valute_from'] = valute_from
        exchange_direction['icon_valute_from'] = icon_url_valute_from
        exchange_direction['type_valute_from'] = type_valute_from

        exchange_direction['valute_to'] = valute_to
        exchange_direction['icon_valute_to'] = icon_url_valute_to
        exchange_direction['type_valute_to'] = type_valute_to

        round_valute_values(exchange_direction)
        direction_list.append(exchange_direction)

    # print(len(connection.queries))
    # for query in connection.queries:
    #     print(query)
    return direction_list


def get_valute_json(queries: List[NoCashExDir | CashExDir]):
    
    '''
    Возвращает словарь валют с необходимыми данными 
    '''

    valute_name_list = set(map(lambda query: query[0], queries))
    valutes = Valute.objects.filter(code_name__in=valute_name_list).all()
    
    default_dict_keys = {'ru': dict(), 'en': dict()}
    json_dict = defaultdict(dict)

    json_dict.fromkeys(default_dict_keys)

    for id, valute in enumerate(valutes, start=1):
        icon_url = try_generate_icon_url(valute)
        valute.icon_url = icon_url
        valute.id = id

        json_dict['ru'][valute.type_valute] = json_dict['ru'].get(valute.type_valute, [])\
                                                 + [ValuteModel(**valute.__dict__)]
        
        en_type_valute = en_type_valute_dict[valute.type_valute]
        json_dict['en'][en_type_valute] = json_dict['en'].get(en_type_valute, [])\
                                                 + [EnValuteModel(**valute.__dict__)]

    return json_dict


def increase_popular_count_direction(**kwargs):
    direction = CashDirection if kwargs.get('city') else NoCashDirection
    valute_from, valute_to = kwargs['valute_from'], kwargs['valute_to']
    direction = direction.objects.get(valute_from=valute_from,
                                      valute_to=valute_to)
    direction.popular_count += 1
    direction.save()


def check_exchage_marker(exchange_marker: str):
    if exchange_marker not in {'no_cash', 'cash', 'partner'}:
        raise HTTPException(status_code=400,
                            detail='Параметр "exchange_marker" должен быть одним из следующих: no_cash, cash, partner')
    

def check_perms_for_adding_review(exchange_id: int,
                                  exchange_marker: str,
                                  tg_id: int):
    time_delta = timedelta(days=1)

    check_exchage_marker(exchange_marker)

    match exchange_marker:
        case 'no_cash':
            review_model = no_cash_models.Review
        case 'cash':
            review_model = cash_models.Review
        case 'partner':
            review_model = partner_models.Review

    check_time = datetime.now() - time_delta

    review = review_model.objects.select_related('guest')\
                                    .filter(exchange_id=exchange_id,
                                            guest_id=tg_id,
                                            time_create__gt=check_time)\
                                    .first()

    if review:
        next_time_review = review.time_create.astimezone() + time_delta
        review_exception_json(status_code=423,
                              param=next_time_review.strftime('%d.%m.%Y %H:%M'))

    
    return {'status': 'success'}
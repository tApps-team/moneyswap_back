from time import time
import aiohttp
import requests
import copy

from collections import defaultdict
from typing import Literal

from django.db.models import Count, Q, Prefetch, F
from django.db import connection, transaction

from fastapi.exceptions import HTTPException

# from general_models.utils.endpoints import (new_get_reviews_count_filters,
#                                             try_generate_icon_url,
#                                             get_reviews_count_filters)
from general_models.utils.base import annotate_string_field, try_generate_icon_url

from general_models.schemas import MultipleName, MultipleName2

from general_models.models import Valute, NewValute

from cash.models import Direction as CashDirection, City, NewExchangeDirection

from partners.models import (Direction,
                             PartnerCity,
                             CountryDirection,
                             PartnerCountry,
                             QRValutePartner,
                             Bankomat,
                             DirectionRate,
                             CountryDirectionRate,
                             NonCashDirection,
                             NonCashDirectionRate,
                             NewNonCashDirection,
                             NewNonCashDirectionRate,
                             NewDirection,
                             NewDirectionRate,
                             NewCountryDirection,
                             NewCountryDirectionRate,
                             NewBankomat,
                             NewQRValutePartner)

from partners.schemas import (PartnerCityInfoSchema,
                              PartnerCityInfoWithAmlSchema,
                              UpdatedTimeByPartnerCitySchema,
                              PartnerCitySchema2,
                              WeekDaySchema,
                              PartnerCityInfoSchema2)


WORKING_DAYS_DICT = {
     'Пн': False,
     'Вт': False,
     'Ср': False,
     'Чт': False,
     'Пт': False,
     'Сб': False,
     'Вс': False,
}


def get_course_count(direction):
        if direction is None:
            return 0
        actual_course = direction.direction.actual_course
        return actual_course if actual_course is not None else 0


def get_partner_in_out_count(actual_course: float | None):
    if actual_course is None:
        return None
    
    if actual_course < 1:
        in_count = 1 / actual_course
        out_count = 1
    else:
         in_count = 1
         out_count = actual_course

    return (
         in_count,
         out_count,
    )


async def request_to_bot_exchange_admin_direction_notification(user_id: int,
                                                               _text: str):
    # user_id = data.get('user_id')
    # order_id = data.get('order_id')
    payload = {
        'user_id': user_id,
        'text': _text,
    }
    # _url = f'https://api.moneyswap.online/exchange_admin_direction_notification?user_id={user_id}&text={_text}'
    _url = f'https://api.moneyswap.online/exchange_admin_direction_notification'
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        # requests.post(url=_url,
        #               json=payload,
        #               timeout=10)
        async with aiohttp.ClientSession() as session:
            async with session.post(_url,
                                    json=payload,
                                   timeout=timeout) as response:
            # async with session.post(_url,
            #                         json=payload) as response:
                # print(response.status)
                # print('done')

                pass
    except Exception as ex:
        print(ex)


async def new_request_to_bot_exchange_admin_direction_notification(user_id: int,
                                                                   _text: str):
    payload = {
        'user_id': user_id,
        'text': _text,
    }
    # _url = f'https://api.moneyswap.online/exchange_admin_direction_notification?user_id={user_id}&text={_text}'
    _url = f'https://api.moneyswap.online/exchange_admin_direction_notification'
    timeout = aiohttp.ClientTimeout(total=5)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(_url,
                                    json=payload,
                                   timeout=timeout) as response:

                pass
    except Exception as ex:
        print(ex)


def get_partner_bankomats_by_valute(partner_id: int,
                                    valute: str,
                                    only_active: bool = False):
    bankomats = Bankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__name=valute)\
                                .all()

    partner_valute = QRValutePartner.objects.filter(partner_id=partner_id,
                                                    valute_id=valute)
                                                
    partner_bankomats = []

    if partner_valute.exists():
        partner_valute = partner_valute.first()

        partner_valute_bankomats = partner_valute.bankomats\
                                                    .values_list('pk',
                                                                flat=True)
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': bankomat.pk in partner_valute_bankomats,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    else:
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': False,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    
    if only_active:
        partner_bankomats = [bankomat for bankomat in partner_bankomats \
                             if bankomat['available']]

    return partner_bankomats


def get_bankomats_by_valute(partner_id: int,
                            valute_id: int,
                            only_active: bool = False):
    bankomats = NewBankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__pk=valute_id)\
                                .all()

    partner_valute = NewQRValutePartner.objects.filter(partner_id=partner_id,
                                                       valute_id=valute_id)
                                                
    partner_bankomats = []

    if partner_valute.exists():
        partner_valute = partner_valute.first()

        partner_valute_bankomats = partner_valute.bankomats\
                                                    .values_list('pk',
                                                                flat=True)
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': bankomat.pk in partner_valute_bankomats,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    else:
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': False,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    
    if only_active:
        partner_bankomats = [bankomat for bankomat in partner_bankomats \
                             if bankomat['available']]

    return partner_bankomats


def test_get_partner_bankomats_by_valute(partner_id: int,
                                    bankomats: list[Bankomat],
                                    partner_valute_dict: dict,
                                    only_active: bool = False):
    partner_valute = partner_valute_dict.get(partner_id)
                                                
    partner_bankomats = []

    if partner_valute:
        partner_valute_bankomats = [_bankomat.pk for _bankomat in partner_valute.bankomats.all()]
        
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': bankomat.pk in partner_valute_bankomats,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    else:
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': False,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    
    if only_active:
        partner_bankomats = [bankomat for bankomat in partner_bankomats \
                             if bankomat['available']]

    return partner_bankomats


def new_get_partner_bankomats_by_valute(partner_id: int,
                                    bankomats: list[Bankomat],
                                    partner_valute_dict: dict,
                                    only_active: bool = False):
    partner_valute = partner_valute_dict.get(partner_id)
                                                
    partner_bankomats = []

    if partner_valute:
        partner_valute_bankomats = [_bankomat.pk for _bankomat in partner_valute.bankomats.all()]
        
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': bankomat.pk in partner_valute_bankomats,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    else:
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': False,
                'icon': try_generate_icon_url(bankomat)
            }
            partner_bankomats.append(partner_bankomat)
    
    if only_active:
        partner_bankomats = [bankomat for bankomat in partner_bankomats \
                             if bankomat['available']]

    return partner_bankomats


def get_partner_directions(valute_from: str,
                           valute_to: str,
                           city: str = None):
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__exchange')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    if city:
        directions = directions.filter(city__city__code_name=city)

    for direction in directions:
        city: PartnerCity = direction.city
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]
        #
        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True)\
        #   for day in direction.city.working_days.all()]

        direction.info = PartnerCityInfoSchema2(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            )
        
        #
    return directions


def get_partner_directions2(valute_from: str,
                           valute_to: str,
                           city: str = None):
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    review_counts = get_reviews_count_filters('partner_country_direction')

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related('country__country__cities')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        country_directions = country_directions.filter(country__country__cities__code_name=city)

    for direction in directions:
        city: PartnerCity = direction.city
        _valute_to: Valute = direction.direction.valute_to
        _partner_id = city.exchange.account.pk
        
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.direction_marker = 'city'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]
        #
        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True)\
        #   for day in direction.city.working_days.all()]
        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoSchema2(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            )


    for direction in country_directions:
        _valute_to: Valute = direction.direction.valute_to
        _partner_id = direction.country.exchange.account.pk

        min_amount = str(int(direction.country.min_amount)) \
            if direction.country.min_amount else None
        max_amount = str(int(direction.country.max_amount)) \
            if direction.country.max_amount else None

        direction.exchange = direction.country.exchange
        direction.exchange_marker = 'partner'
        direction.direction_marker = 'country'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                 time_to=direction.country.time_to)

        weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                 time_to=direction.country.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in direction.country.working_days.all()]
        #
        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True)\
        #   for day in direction.city.working_days.all()]
        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoSchema2(
            delivery=direction.country.has_delivery,
            office=direction.country.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            )

    # print(directions)
    # print(country_directions)

    check_set = set()

    result = []

    for sequence in (directions, country_directions):
        for direction in sequence:
            if not direction.exchange in check_set:
                check_set.add(direction.exchange)
                result.append(direction)

    return result



def test_get_partner_directions2(valute_from: str,
                           valute_to: str,
                           city: str = None):
    #
    #valute_to
    _valute_to_obj = Valute.objects.get(code_name=valute_to)
    if _valute_to_obj.type_valute == 'ATM QR':
        #bankomats
        _bankomats = Bankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__name=_valute_to_obj.name)\
                                .all()
        #qrvalutepartner
        partner_valute = QRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.name)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    direction_rate_prefetch = Prefetch('direction_rates',
                                       DirectionRate.objects.order_by('min_rate_limit'))

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch)\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    review_counts = get_reviews_count_filters('partner_country_direction')

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       CountryDirectionRate.objects.order_by('min_rate_limit'))

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch,
                                                                  'country__country__cities')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        country_directions = country_directions.filter(country__country__cities__code_name=city)

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'exchange__account',
                                                        'city',
                                                        'city__country')\
                                        .prefetch_related('working_days').all()
    partner_cities_dict = {_city.pk: _city for _city in partner_cities}

    direction_list = []
    for direction in directions:
        city = partner_cities_dict.get(direction.city.pk)
        _valute_to: Valute = direction.direction.valute_to
        _partner_id = city.exchange.account.pk
        
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       _direction_min_amount,
                                       _direction_max_amount,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates


        print('after', _in_count, _out_count)

        # print(exchange_rates)
        if addittional_exchange_rates:
            direction.exchange_rates = [{'in_count': el[0],
                                         'out_count': el[1],
                                         'min_count': el[2],
                                         'max_count': el[3],
                                         'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.direction_marker = 'city'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)

        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoSchema2(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            )
        direction_list.append(direction)

    country_direction_list = []
    if country_directions.exists():
        #partnercountry with workingdays
        partner_countries = PartnerCountry.objects.select_related('exchange',
                                                                  'exchange__account',
                                                                  'country')\
                                                    .prefetch_related('working_days')\
                                                    .all()
        partner_countries_dict = {_country.pk: _country for _country in partner_countries}

        for direction in country_directions:
            _partner_country = partner_countries_dict.get(direction.country.pk)
            # print(direction.__dict__)
            _valute_to: Valute = direction.direction.valute_to
            _partner_id = direction.country.exchange.account.pk

            min_amount = str(int(direction.country.min_amount)) \
                if direction.country.min_amount else None
            max_amount = str(int(direction.country.max_amount)) \
                if direction.country.max_amount else None
            
            exchange_rates = direction.direction_rates.all()

            _in_count = direction.in_count
            _out_count = direction.out_count
            _direction_min_amount = direction.min_amount
            _direction_max_amount = direction.max_amount

            addittional_exchange_rates = None

            if exchange_rates:
                exchange_rate_list = [(el.in_count,
                                    el.out_count,
                                    el.min_rate_limit,
                                    el.max_rate_limit,
                                    el.rate_coefficient) for el in exchange_rates]
                exchange_rate_list.append((_in_count,
                                        _out_count,
                                        _direction_min_amount,
                                        _direction_max_amount,
                                        None))

                sorted_exchange_rates = sorted(exchange_rate_list,
                                            key=lambda el: (-el[1], el[0]))
                
                best_exchange_rate = sorted_exchange_rates[0]
                _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

                addittional_exchange_rates = sorted_exchange_rates

            if addittional_exchange_rates:
                direction.exchange_rates = [{'in_count': el[0],
                                            'out_count': el[1],
                                            'min_count': el[2],
                                            'max_count': el[3],
                                            'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
            else:
                direction.exchange_rates = None

            direction.exchange = direction.country.exchange
            direction.exchange_marker = 'partner'
            direction.direction_marker = 'country'
            direction.valute_from = valute_from
            direction.valute_to = valute_to
            direction.min_amount = min_amount
            direction.max_amount = max_amount
            direction.in_count = _in_count
            direction.out_count = _out_count
            direction.params = None
            direction.fromfee = None

            weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                    time_to=direction.country.time_to)

            weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                    time_to=direction.country.weekend_time_to)

            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in _partner_country.working_days.all()]

            if _valute_to.type_valute == 'ATM QR':
                # bankomats = get_partner_bankomats_by_valute(_partner_id,
                #                                             _valute_to.name,
                #                                             only_active=True)
                bankomats = test_get_partner_bankomats_by_valute(_partner_id,
                                                                 _bankomats,
                                                                 partner_valute_dict,
                                                                 only_active=True)
            else:
                bankomats = None

            direction.info = PartnerCityInfoSchema2(
                delivery=direction.country.has_delivery,
                office=direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                )
            country_direction_list.append(direction)

    check_set = set()

    result = []

    # for sequence in (directions, country_directions):
    for sequence in (direction_list, country_direction_list):
        for direction in sequence:
            if not direction.exchange in check_set:
                check_set.add(direction.exchange)
                result.append(direction)

    return result


def test_get_partner_directions2_with_aml(valute_from: str,
                           valute_to: str,
                           city: str = None):
    #
    #valute_to
    _valute_to_obj = Valute.objects.get(code_name=valute_to)
    if _valute_to_obj.type_valute == 'ATM QR':
        #bankomats
        _bankomats = Bankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__name=_valute_to_obj.name)\
                                .all()
        #qrvalutepartner
        partner_valute = QRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.name)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    
    direction_name = valute_from + ' -> ' + valute_to

    # review_counts = get_reviews_count_filters('partner_direction')
    review_counts = new_get_reviews_count_filters('partner_direction')

    direction_rate_prefetch = Prefetch('direction_rates',
                                       DirectionRate.objects.order_by('min_rate_limit'))

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch)\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    # review_counts = get_reviews_count_filters('partner_country_direction')

    review_counts = new_get_reviews_count_filters('partner_country_direction')

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       CountryDirectionRate.objects.order_by('min_rate_limit'))

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch,
                                                                  'country__country__cities')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        country_directions = country_directions.filter(country__country__cities__code_name=city)

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'exchange__account',
                                                        'city',
                                                        'city__country')\
                                        .prefetch_related('working_days').all()
    partner_cities_dict = {_city.pk: _city for _city in partner_cities}

    direction_list = []
    for direction in directions:
        city = partner_cities_dict.get(direction.city.pk)
        _valute_to: Valute = direction.direction.valute_to
        _partner_id = city.exchange.account.pk
        
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       _direction_min_amount,
                                       _direction_max_amount,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates


        print('after', _in_count, _out_count)

        # print(exchange_rates)
        if addittional_exchange_rates:
            direction.exchange_rates = [{'in_count': el[0],
                                         'out_count': el[1],
                                         'min_count': el[2],
                                         'max_count': el[3],
                                         'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.direction_marker = 'city'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)

        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoWithAmlSchema(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            high_aml=city.exchange.high_aml,
            )
        direction_list.append(direction)

    country_direction_list = []
    if country_directions.exists():
        #partnercountry with workingdays
        partner_countries = PartnerCountry.objects.select_related('exchange',
                                                                  'exchange__account',
                                                                  'country')\
                                                    .prefetch_related('working_days')\
                                                    .all()
        partner_countries_dict = {_country.pk: _country for _country in partner_countries}

        for direction in country_directions:
            _partner_country = partner_countries_dict.get(direction.country.pk)
            # print(direction.__dict__)
            _valute_to: Valute = direction.direction.valute_to
            _partner_id = direction.country.exchange.account.pk

            min_amount = str(int(direction.country.min_amount)) \
                if direction.country.min_amount else None
            max_amount = str(int(direction.country.max_amount)) \
                if direction.country.max_amount else None
            
            exchange_rates = direction.direction_rates.all()

            _in_count = direction.in_count
            _out_count = direction.out_count
            _direction_min_amount = direction.min_amount
            _direction_max_amount = direction.max_amount

            addittional_exchange_rates = None

            if exchange_rates:
                exchange_rate_list = [(el.in_count,
                                    el.out_count,
                                    el.min_rate_limit,
                                    el.max_rate_limit,
                                    el.rate_coefficient) for el in exchange_rates]
                exchange_rate_list.append((_in_count,
                                        _out_count,
                                        _direction_min_amount,
                                        _direction_max_amount,
                                        None))

                sorted_exchange_rates = sorted(exchange_rate_list,
                                            key=lambda el: (-el[1], el[0]))
                
                best_exchange_rate = sorted_exchange_rates[0]
                _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

                addittional_exchange_rates = sorted_exchange_rates

            if addittional_exchange_rates:
                direction.exchange_rates = [{'in_count': el[0],
                                            'out_count': el[1],
                                            'min_count': el[2],
                                            'max_count': el[3],
                                            'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
            else:
                direction.exchange_rates = None

            direction.exchange = direction.country.exchange
            direction.exchange_marker = 'partner'
            direction.direction_marker = 'country'
            direction.valute_from = valute_from
            direction.valute_to = valute_to
            direction.min_amount = min_amount
            direction.max_amount = max_amount
            direction.in_count = _in_count
            direction.out_count = _out_count
            direction.params = None
            direction.fromfee = None

            weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                    time_to=direction.country.time_to)

            weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                    time_to=direction.country.weekend_time_to)

            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in _partner_country.working_days.all()]

            if _valute_to.type_valute == 'ATM QR':
                # bankomats = get_partner_bankomats_by_valute(_partner_id,
                #                                             _valute_to.name,
                #                                             only_active=True)
                bankomats = test_get_partner_bankomats_by_valute(_partner_id,
                                                                 _bankomats,
                                                                 partner_valute_dict,
                                                                 only_active=True)
            else:
                bankomats = None

            direction.info = PartnerCityInfoWithAmlSchema(
                delivery=direction.country.has_delivery,
                office=direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                high_aml=direction.country.exchange.high_aml,
                )
            country_direction_list.append(direction)

    check_set = set()

    result = []

    # for sequence in (directions, country_directions):
    for sequence in (direction_list, country_direction_list):
        for direction in sequence:
            if not direction.exchange in check_set:
                check_set.add(direction.exchange)
                result.append(direction)

    return result


def new_test_get_partner_directions2_with_aml(valute_from: str,
                           valute_to: str,
                           city: str = None):
    #
    #valute_to
    _valute_to_obj = Valute.objects.get(code_name=valute_to)
    if _valute_to_obj.type_valute == 'ATM QR':
        #bankomats
        _bankomats = Bankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__name=_valute_to_obj.name)\
                                .all()
        #qrvalutepartner
        partner_valute = QRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.name)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    
    direction_name = valute_from + ' -> ' + valute_to

    # review_counts = get_reviews_count_filters('partner_direction')
    review_counts = new_get_reviews_count_filters('partner_direction')

    direction_rate_prefetch = Prefetch('direction_rates',
                                       DirectionRate.objects.order_by('min_rate_limit'))

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch)\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    # review_counts = get_reviews_count_filters('partner_country_direction')

    review_counts = new_get_reviews_count_filters('partner_country_direction')

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       CountryDirectionRate.objects.order_by('min_rate_limit'))

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch,
                                                                  'country__country__cities')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        country_directions = country_directions.filter(country__country__cities__code_name=city)

    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'exchange__account',
                                                        'city',
                                                        'city__country')\
                                        .prefetch_related('working_days').all()
    partner_cities_dict = {_city.pk: _city for _city in partner_cities}

    direction_list = []
    for direction in directions:
        city = partner_cities_dict.get(direction.city.pk)
        _valute_to: Valute = direction.direction.valute_to
        _partner_id = city.exchange.account.pk
        
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       _direction_min_amount,
                                       _direction_max_amount,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates


        # print('after', _in_count, _out_count)

        _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

        if addittional_exchange_rates:
            exchange_rate_list = []
            for el in addittional_exchange_rates:
                in_count, out_count = el[0], el[1]
                in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                exchange_rate_list.append(
                    {
                    'in_count': in_count,
                    'out_count': out_count,
                    'min_count': el[2],
                    'max_count': el[3],
                    'rate_coefficient': el[-1],
                    }
                )
            direction.exchange_rates = exchange_rate_list

        # print(exchange_rates)
        # if addittional_exchange_rates:
        #     direction.exchange_rates = [{'in_count': el[0],
        #                                  'out_count': el[1],
        #                                  'min_count': el[2],
        #                                  'max_count': el[3],
        #                                  'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.direction_marker = 'city'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)

        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoWithAmlSchema(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            high_aml=city.exchange.high_aml,
            )
        direction_list.append(direction)

    country_direction_list = []
    if country_directions.exists():
        #partnercountry with workingdays
        partner_countries = PartnerCountry.objects.select_related('exchange',
                                                                  'exchange__account',
                                                                  'country')\
                                                    .prefetch_related('working_days')\
                                                    .all()
        partner_countries_dict = {_country.pk: _country for _country in partner_countries}

        for direction in country_directions:
            _partner_country = partner_countries_dict.get(direction.country.pk)
            # print(direction.__dict__)
            _valute_to: Valute = direction.direction.valute_to
            _partner_id = direction.country.exchange.account.pk

            min_amount = str(int(direction.country.min_amount)) \
                if direction.country.min_amount else None
            max_amount = str(int(direction.country.max_amount)) \
                if direction.country.max_amount else None
            
            exchange_rates = direction.direction_rates.all()

            _in_count = direction.in_count
            _out_count = direction.out_count
            _direction_min_amount = direction.min_amount
            _direction_max_amount = direction.max_amount

            addittional_exchange_rates = None

            if exchange_rates:
                exchange_rate_list = [(el.in_count,
                                    el.out_count,
                                    el.min_rate_limit,
                                    el.max_rate_limit,
                                    el.rate_coefficient) for el in exchange_rates]
                exchange_rate_list.append((_in_count,
                                        _out_count,
                                        _direction_min_amount,
                                        _direction_max_amount,
                                        None))

                sorted_exchange_rates = sorted(exchange_rate_list,
                                            key=lambda el: (-el[1], el[0]))
                
                best_exchange_rate = sorted_exchange_rates[0]
                _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

                addittional_exchange_rates = sorted_exchange_rates

            _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

            if addittional_exchange_rates:
                exchange_rate_list = []
                for el in addittional_exchange_rates:
                    in_count, out_count = el[0], el[1]
                    in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                    exchange_rate_list.append(
                        {
                        'in_count': in_count,
                        'out_count': out_count,
                        'min_count': el[2],
                        'max_count': el[3],
                        'rate_coefficient': el[-1],
                        }
                    )
                direction.exchange_rates = exchange_rate_list

            # if addittional_exchange_rates:
            #     direction.exchange_rates = [{'in_count': el[0],
            #                                 'out_count': el[1],
            #                                 'min_count': el[2],
            #                                 'max_count': el[3],
            #                                 'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
            else:
                direction.exchange_rates = None

            direction.exchange = direction.country.exchange
            direction.exchange_marker = 'partner'
            direction.direction_marker = 'country'
            direction.valute_from = valute_from
            direction.valute_to = valute_to
            direction.min_amount = min_amount
            direction.max_amount = max_amount
            direction.in_count = _in_count
            direction.out_count = _out_count
            direction.params = None
            direction.fromfee = None

            weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                    time_to=direction.country.time_to)

            weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                    time_to=direction.country.weekend_time_to)

            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in _partner_country.working_days.all()]

            if _valute_to.type_valute == 'ATM QR':
                # bankomats = get_partner_bankomats_by_valute(_partner_id,
                #                                             _valute_to.name,
                #                                             only_active=True)
                bankomats = test_get_partner_bankomats_by_valute(_partner_id,
                                                                 _bankomats,
                                                                 partner_valute_dict,
                                                                 only_active=True)
            else:
                bankomats = None

            direction.info = PartnerCityInfoWithAmlSchema(
                delivery=direction.country.has_delivery,
                office=direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                high_aml=direction.country.exchange.high_aml,
                )
            country_direction_list.append(direction)

    check_set = set()

    result = []

    # for sequence in (directions, country_directions):
    for sequence in (direction_list, country_direction_list):
        for direction in sequence:
            if not direction.exchange in check_set:
                check_set.add(direction.exchange)
                result.append(direction)

    return result


def new_test_get_partner_directions2_with_aml2(valute_from: str,
                                               valute_to: str,
                                               city: str = None):
    #
    #valute_to
    _valute_to_obj = Valute.objects.get(code_name=valute_to)
    
    if _valute_to_obj.type_valute == 'ATM QR':
        #bankomats
        _bankomats = Bankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__name=_valute_to_obj.name)\
                                .all()
        #qrvalutepartner
        partner_valute = QRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.name)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    
    direction_name = valute_from + ' -> ' + valute_to

    # review_counts = get_reviews_count_filters('partner_direction')
    review_counts = new_get_reviews_count_filters('partner_direction')

    direction_rate_prefetch = Prefetch('direction_rates',
                                       DirectionRate.objects.order_by('min_rate_limit'))

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch,
                                              'city__working_days')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    # review_counts = get_reviews_count_filters('partner_country_direction')

    review_counts = new_get_reviews_count_filters('partner_country_direction')

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       CountryDirectionRate.objects.order_by('min_rate_limit'))
    
    unavailable_cities_by_partner_country_prefetch = Prefetch('country__exclude_cities',
                                                            queryset=City.objects.filter(is_parse=True))

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch,
                                                                  unavailable_cities_by_partner_country_prefetch,
                                                                  'country__country__cities',
                                                                  'country__working_days')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        country_directions = country_directions.filter(country__country__cities__code_name=city)

    # partner_cities = PartnerCity.objects.select_related('exchange',
    #                                                     'exchange__account',
    #                                                     'city',
    #                                                     'city__country')\
    #                                     .prefetch_related('working_days').all()
    # partner_cities_dict = {_city.pk: _city for _city in partner_cities}

    direction_list = []
    for direction in directions:
        # city = partner_cities_dict.get(direction.city.pk)
        city = direction.city

        _valute_to: Valute = direction.direction.valute_to
        _partner_id = city.exchange.account.pk
        
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       _direction_min_amount,
                                       _direction_max_amount,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates


        # print('after', _in_count, _out_count)

        _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

        if addittional_exchange_rates:
            exchange_rate_list = []
            for el in addittional_exchange_rates:
                in_count, out_count = el[0], el[1]
                in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                exchange_rate_list.append(
                    {
                    'in_count': in_count,
                    'out_count': out_count,
                    'min_count': el[2],
                    'max_count': el[3],
                    'rate_coefficient': el[-1],
                    }
                )
            direction.exchange_rates = exchange_rate_list

        # print(exchange_rates)
        # if addittional_exchange_rates:
        #     direction.exchange_rates = [{'in_count': el[0],
        #                                  'out_count': el[1],
        #                                  'min_count': el[2],
        #                                  'max_count': el[3],
        #                                  'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.direction_marker = 'city'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)

        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoWithAmlSchema(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            high_aml=city.exchange.high_aml,
            )
        direction_list.append(direction)

    country_direction_list = []
    if country_directions.exists():
        #partnercountry with workingdays
        # partner_countries = PartnerCountry.objects.select_related('exchange',
        #                                                           'exchange__account',
        #                                                           'country')\
        #                                             .prefetch_related('working_days')\
        #                                             .all()
        # partner_countries_dict = {_country.pk: _country for _country in partner_countries}

        for direction in country_directions:
            # _partner_country = partner_countries_dict.get(direction.country.pk)
            _partner_country = direction.country

            excluded_cities_code_name_set = {city.code_name for city in _partner_country.exclude_cities.all()}

            if city in excluded_cities_code_name_set:
                continue

            # print(direction.__dict__)
            _valute_to: Valute = direction.direction.valute_to
            _partner_id = direction.country.exchange.account.pk

            min_amount = str(int(direction.country.min_amount)) \
                if direction.country.min_amount else None
            max_amount = str(int(direction.country.max_amount)) \
                if direction.country.max_amount else None
            
            exchange_rates = direction.direction_rates.all()

            _in_count = direction.in_count
            _out_count = direction.out_count
            _direction_min_amount = direction.min_amount
            _direction_max_amount = direction.max_amount

            addittional_exchange_rates = None

            if exchange_rates:
                exchange_rate_list = [(el.in_count,
                                    el.out_count,
                                    el.min_rate_limit,
                                    el.max_rate_limit,
                                    el.rate_coefficient) for el in exchange_rates]
                exchange_rate_list.append((_in_count,
                                        _out_count,
                                        _direction_min_amount,
                                        _direction_max_amount,
                                        None))

                sorted_exchange_rates = sorted(exchange_rate_list,
                                            key=lambda el: (-el[1], el[0]))
                
                best_exchange_rate = sorted_exchange_rates[0]
                _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

                addittional_exchange_rates = sorted_exchange_rates

            _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

            if addittional_exchange_rates:
                exchange_rate_list = []
                for el in addittional_exchange_rates:
                    in_count, out_count = el[0], el[1]
                    in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                    exchange_rate_list.append(
                        {
                        'in_count': in_count,
                        'out_count': out_count,
                        'min_count': el[2],
                        'max_count': el[3],
                        'rate_coefficient': el[-1],
                        }
                    )
                direction.exchange_rates = exchange_rate_list

            # if addittional_exchange_rates:
            #     direction.exchange_rates = [{'in_count': el[0],
            #                                 'out_count': el[1],
            #                                 'min_count': el[2],
            #                                 'max_count': el[3],
            #                                 'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
            else:
                direction.exchange_rates = None

            direction.exchange = direction.country.exchange
            direction.exchange_marker = 'partner'
            direction.direction_marker = 'country'
            direction.valute_from = valute_from
            direction.valute_to = valute_to
            direction.min_amount = min_amount
            direction.max_amount = max_amount
            direction.in_count = _in_count
            direction.out_count = _out_count
            direction.params = None
            direction.fromfee = None

            weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                    time_to=direction.country.time_to)

            weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                    time_to=direction.country.weekend_time_to)

            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in _partner_country.working_days.all()]

            if _valute_to.type_valute == 'ATM QR':
                # bankomats = get_partner_bankomats_by_valute(_partner_id,
                #                                             _valute_to.name,
                #                                             only_active=True)
                bankomats = test_get_partner_bankomats_by_valute(_partner_id,
                                                                 _bankomats,
                                                                 partner_valute_dict,
                                                                 only_active=True)
            else:
                bankomats = None

            direction.info = PartnerCityInfoWithAmlSchema(
                delivery=direction.country.has_delivery,
                office=direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                high_aml=direction.country.exchange.high_aml,
                )
            country_direction_list.append(direction)

    check_set = set()

    result = []

    # for sequence in (directions, country_directions):
    for sequence in (direction_list, country_direction_list):
        for direction in sequence:
            if not direction.exchange in check_set:
                check_set.add(direction.exchange)
                result.append(direction)

    return result


def generate_partner_city_direction(direction: NewDirection,
                                    _bankomats: list[NewBankomat],
                                    partner_valute_dict: dict):
    # direction_dict = {
    #     'exchange': direction.city.exchange,
    #     # for sort
    #     'is_vip': direction.city.exchange.is_vip,
    #     'exchange_direction_id': direction.pk,
    #     'direction': direction.direction,
    #     'direction_marker': 'city',
    #     'valute_from': direction.direction.valute_from_id,
    #     'valute_to': direction.direction.valute_to_id,
    #     'params': None,
    #     'fromfee': None,
    # }

    city = direction.city

    _valute_to: NewValute = direction.direction.valute_to
    _partner_id = city.exchange.account.pk
    
    min_amount = str(int(city.min_amount)) if city.min_amount else None
    max_amount = str(int(city.max_amount)) if city.max_amount else None

    exchange_rates = direction.direction_rates.all()

    _in_count = direction.in_count
    _out_count = direction.out_count
    _direction_min_amount = direction.min_amount
    _direction_max_amount = direction.max_amount

    addittional_exchange_rates = None

    if exchange_rates:
        exchange_rate_list = [(el.in_count,
                                el.out_count,
                                el.min_rate_limit,
                                el.max_rate_limit,
                                el.rate_coefficient) for el in exchange_rates]
        exchange_rate_list.append((_in_count,
                                    _out_count,
                                    _direction_min_amount,
                                    _direction_max_amount,
                                    None))

        sorted_exchange_rates = sorted(exchange_rate_list,
                                        key=lambda el: (-el[1], el[0]))
        
        best_exchange_rate = sorted_exchange_rates[0]
        _in_count, _out_count, _, _, _ = best_exchange_rate

        addittional_exchange_rates = sorted_exchange_rates

    _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

    if addittional_exchange_rates:
        exchange_rate_list = []
        for el in addittional_exchange_rates:
            in_count, out_count = el[0], el[1]
            in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
            exchange_rate_list.append(
                {
                'in_count': in_count,
                'out_count': out_count,
                'min_count': el[2],
                'max_count': el[3],
                'rate_coefficient': el[-1],
                }
            )
        direction.exchange_rates = exchange_rate_list
    
    else:
        direction.exchange_rates = None

    direction.exchange = city.exchange
    # direction.exchange_marker = 'partner'
    direction.direction_marker = 'city'
    direction.valute_from = direction.direction.valute_from.code_name
    direction.valute_to = direction.direction.valute_to.code_name
    direction.min_amount = min_amount
    direction.max_amount = max_amount
    direction.in_count = _in_count
    direction.out_count = _out_count

    direction.city_model = city.city
    direction.country_model = city.city.country

    direction.params = None
    direction.fromfee = None

    weekdays = WeekDaySchema(time_from=city.time_from,
                                time_to=city.time_to)

    weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                time_to=city.weekend_time_to)

    working_days = {key.upper(): value \
                    for key, value in WORKING_DAYS_DICT.items()}
    
    [working_days.__setitem__(day.code_name.upper(), True) \
        for day in city.working_days.all()]

    if _valute_to.type_valute == 'ATM QR':
        bankomats = new_get_partner_bankomats_by_valute(_partner_id,
                                                        _bankomats,
                                                        partner_valute_dict,
                                                        only_active=True)
    else:
        bankomats = None

    direction.info = PartnerCityInfoWithAmlSchema(
        delivery=city.has_delivery,
        office=city.has_office,
        working_days=working_days,
        weekdays=weekdays,
        weekends=weekends,
        bankomats=bankomats,
        high_aml=city.exchange.high_aml,
        )
    
    # direction_dict.update({
    #     'min_amount': min_amount,
    #     'max_amount': max_amount,
    #     'in_count': _in_count,
    #     'out_count': _out_count,
    #     'city_model': city_model,
    #     'country_model': country_model,
    #     'info': info,
    # })
    
    return direction


def generate_partner_city_direction_for_location(direction: NewDirection,
                                                 _bankomats: list[NewBankomat],
                                                 partner_valute_dict: dict):
    direction_dict = {
        'exchange': direction.city.exchange,
        # for sort
        'is_vip': direction.city.exchange.is_vip,
        'exchange_direction_id': direction.pk,
        'direction': direction.direction,
        'direction_marker': 'city',
        'valute_from': direction.direction.valute_from_id,
        'valute_to': direction.direction.valute_to_id,
        'params': None,
        'fromfee': None,
    }

    city = direction.city

    _valute_to: NewValute = direction.direction.valute_to
    _partner_id = city.exchange.account.pk
    
    min_amount = str(int(city.min_amount)) if city.min_amount else None
    max_amount = str(int(city.max_amount)) if city.max_amount else None

    exchange_rates = direction.direction_rates.all()

    _in_count = direction.in_count
    _out_count = direction.out_count
    _direction_min_amount = direction.min_amount
    _direction_max_amount = direction.max_amount

    addittional_exchange_rates = None

    if exchange_rates:
        exchange_rate_list = [(el.in_count,
                                el.out_count,
                                el.min_rate_limit,
                                el.max_rate_limit,
                                el.rate_coefficient) for el in exchange_rates]
        exchange_rate_list.append((_in_count,
                                    _out_count,
                                    _direction_min_amount,
                                    _direction_max_amount,
                                    None))

        sorted_exchange_rates = sorted(exchange_rate_list,
                                        key=lambda el: (-el[1], el[0]))
        
        best_exchange_rate = sorted_exchange_rates[0]
        _in_count, _out_count, _, _, _ = best_exchange_rate

        addittional_exchange_rates = sorted_exchange_rates

    _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

    if addittional_exchange_rates:
        exchange_rate_list = []
        for el in addittional_exchange_rates:
            in_count, out_count = el[0], el[1]
            in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
            exchange_rate_list.append(
                {
                'in_count': in_count,
                'out_count': out_count,
                'min_count': el[2],
                'max_count': el[3],
                'rate_coefficient': el[-1],
                }
            )
        direction_dict['exchange_rates'] = exchange_rate_list
    
    else:
        direction_dict['exchange_rates'] = None

    # direction.exchange = city.exchange
    # direction.exchange_marker = 'partner'
    # direction.direction_marker = 'city'
    # direction.valute_from = direction.direction.valute_from.code_name
    # direction.valute_to = direction.direction.valute_to.code_name
    # direction.min_amount = min_amount
    # direction.max_amount = max_amount
    # direction.in_count = _in_count
    # direction.out_count = _out_count

    city_model = city.city
    country_model = city.city.country

    # direction.params = None
    # direction.fromfee = None

    weekdays = WeekDaySchema(time_from=city.time_from,
                                time_to=city.time_to)

    weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                time_to=city.weekend_time_to)

    working_days = {key.upper(): value \
                    for key, value in WORKING_DAYS_DICT.items()}
    
    [working_days.__setitem__(day.code_name.upper(), True) \
        for day in city.working_days.all()]

    if _valute_to.type_valute == 'ATM QR':
        bankomats = new_get_partner_bankomats_by_valute(_partner_id,
                                                        _bankomats,
                                                        partner_valute_dict,
                                                        only_active=True)
    else:
        bankomats = None

    info = PartnerCityInfoWithAmlSchema(
        delivery=city.has_delivery,
        office=city.has_office,
        working_days=working_days,
        weekdays=weekdays,
        weekends=weekends,
        bankomats=bankomats,
        high_aml=city.exchange.high_aml,
        )
    
    direction_dict.update({
        'min_amount': min_amount,
        'max_amount': max_amount,
        'in_count': _in_count,
        'out_count': _out_count,
        'city_model': city_model,
        'country_model': country_model,
        'info': info,
    })
    
    return direction_dict


def get_bankomats_and_partner_valute_dict(valute_to: str):
    try:
        _valute_to_obj = NewValute.objects.get(code_name=valute_to)
    except Exception:
        raise HTTPException(status_code=404,
                            detail='Valute To not found')
    
    if _valute_to_obj.type_valute == 'ATM QR':
        # bankomats
        _bankomats = NewBankomat.objects.filter(valutes__name=_valute_to_obj.name)\
                                        .all()
        # qrvalutepartner
        partner_valute = NewQRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.pk)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    else:
        _bankomats = None
        partner_valute_dict = None

    return (
        _bankomats,
        partner_valute_dict,
    )


def generate_partner_direction_country_level(direction: NewExchangeDirection,
                                             _bankomats: list[NewBankomat],
                                             partner_valute_dict: dict):
    _valute_to: NewValute = direction.direction.valute_to
    _partner_id = direction.exchange.account.pk
    _partner_country = direction.country_direction.country

    # сделать поля min_amount и max_amount необязательными в cash_models.NewExchangeDirection
    
    if direction.min_amount is None:
        min_amount = None
    elif isinstance(direction.min_amount, str):
        min_amount = direction.min_amount
    else:
        min_amount = str(int(float(direction.min_amount)))

    if direction.max_amount is None:
        max_amount = None
    elif isinstance(direction.max_amount, str):
        max_amount = direction.max_amount
    else:
        max_amount = str(int(float(direction.max_amount)))
    
    exchange_rates = direction.country_direction.direction_rates.all()

    _in_count = direction.in_count
    _out_count = direction.out_count
    _direction_min_amount = direction.min_amount
    _direction_max_amount = direction.max_amount

    addittional_exchange_rates = None

    if exchange_rates:
        exchange_rate_list = [(el.in_count,
                            el.out_count,
                            el.min_rate_limit,
                            el.max_rate_limit,
                            el.rate_coefficient) for el in exchange_rates]
        exchange_rate_list.append((_in_count,
                                _out_count,
                                _direction_min_amount,
                                _direction_max_amount,
                                None))

        sorted_exchange_rates = sorted(exchange_rate_list,
                                    key=lambda el: (-el[1], el[0]))
        
        best_exchange_rate = sorted_exchange_rates[0]
        _in_count, _out_count, _, _, _ = best_exchange_rate

        addittional_exchange_rates = sorted_exchange_rates

    _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

    if addittional_exchange_rates:
        exchange_rate_list = []
        for el in addittional_exchange_rates:
            in_count, out_count = el[0], el[1]
            in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
            exchange_rate_list.append(
                {
                'in_count': in_count,
                'out_count': out_count,
                'min_count': el[2],
                'max_count': el[3],
                'rate_coefficient': el[-1],
                }
            )
        direction.exchange_rates = exchange_rate_list

    else:
        direction.exchange_rates = None

    # direction.exchange = direction.country.exchange
    # direction.exchange_marker = 'partner'
    direction.direction_marker = 'country'
    direction.valute_from = direction.direction.valute_from
    direction.valute_to = direction.direction.valute_to
    direction.min_amount = min_amount
    direction.max_amount = max_amount
    direction.in_count = _in_count
    direction.out_count = _out_count
    direction.params = None
    direction.fromfee = None

    weekdays = WeekDaySchema(time_from=direction.country_direction.country.time_from,
                            time_to=direction.country_direction.country.time_to)

    weekends = WeekDaySchema(time_from=direction.country_direction.country.weekend_time_from,
                            time_to=direction.country_direction.country.weekend_time_to)

    working_days = {key.upper(): value \
                    for key, value in WORKING_DAYS_DICT.items()}
    
    [working_days.__setitem__(day.code_name.upper(), True) \
    for day in _partner_country.working_days.all()]

    if _valute_to.type_valute == 'ATM QR':
        bankomats = new_get_partner_bankomats_by_valute(_partner_id,
                                                            _bankomats,
                                                            partner_valute_dict,
                                                            only_active=True)
    else:
        bankomats = None

    direction.info = PartnerCityInfoWithAmlSchema(
        delivery=direction.country_direction.country.has_delivery,
        office=direction.country_direction.country.has_office,
        working_days=working_days,
        weekdays=weekdays,
        weekends=weekends,
        bankomats=bankomats,
        high_aml=direction.exchange.high_aml,
        )
    
    return direction



def get_partner_directions_with_aml(valute_from: str,
                                     valute_to: str,
                                     city: str = None):
    # valute_to
    try:
        _valute_to_obj = NewValute.objects.get(code_name=valute_to)
    except Exception:
        raise HTTPException(status_code=404,
                            detail='Valute To not found')
    
    if _valute_to_obj.type_valute == 'ATM QR':
        # bankomats
        _bankomats = NewBankomat.objects.filter(valutes__name=_valute_to_obj.name)\
                                        .all()
        # qrvalutepartner
        partner_valute = NewQRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.pk)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    else:
        _bankomats = None
        partner_valute_dict = None

    direction_rate_prefetch = Prefetch('direction_rates',
                                       NewDirectionRate.objects.order_by('min_rate_limit'))

    directions = NewDirection.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch,
                                              'city__working_days')\
                            .annotate(direction_marker=annotate_string_field('city'))\
                            .filter(direction__valute_from_id=valute_from,
                                    direction__valute_to_id=valute_to,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    unavailable_cities_by_partner_country_prefetch = Prefetch('country__exclude_cities',
                                                            queryset=City.objects.select_related('country').filter(is_parse=True))
    country_cities_prefetch = Prefetch('country__country__cities',
                                        queryset=City.objects.select_related('country').filter(is_parse=True))

    country_directions = NewCountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch,
                                                                  unavailable_cities_by_partner_country_prefetch,
                                                                  country_cities_prefetch,
                                                                #   'country__country__cities',
                                                                  'country__working_days')\
                                                .annotate(direction_marker=annotate_string_field('country'))\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        country_directions = country_directions.filter(country__country__cities__code_name=city)

    direction_list = []
    for direction in directions:
        direction = generate_partner_city_direction(direction,
                                                    _bankomats,
                                                    partner_valute_dict)
        direction_list.append(direction)

    country_direction_list = []
    if country_directions.exists():

        for direction in country_directions:
            _partner_country = direction.country

            excluded_cities_code_name_set = {city.code_name for city in _partner_country.exclude_cities.all()}

            if city is not None and city in excluded_cities_code_name_set:
                continue

            _valute_to: NewValute = direction.direction.valute_to
            _partner_id = direction.country.exchange.account.pk

            min_amount = str(int(direction.country.min_amount)) \
                if direction.country.min_amount else None
            max_amount = str(int(direction.country.max_amount)) \
                if direction.country.max_amount else None
            
            exchange_rates = direction.direction_rates.all()

            _in_count = direction.in_count
            _out_count = direction.out_count
            _direction_min_amount = direction.min_amount
            _direction_max_amount = direction.max_amount

            addittional_exchange_rates = None

            if exchange_rates:
                exchange_rate_list = [(el.in_count,
                                    el.out_count,
                                    el.min_rate_limit,
                                    el.max_rate_limit,
                                    el.rate_coefficient) for el in exchange_rates]
                exchange_rate_list.append((_in_count,
                                        _out_count,
                                        _direction_min_amount,
                                        _direction_max_amount,
                                        None))

                sorted_exchange_rates = sorted(exchange_rate_list,
                                            key=lambda el: (-el[1], el[0]))
                
                best_exchange_rate = sorted_exchange_rates[0]
                _in_count, _out_count, _, _, _ = best_exchange_rate

                addittional_exchange_rates = sorted_exchange_rates

            _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

            if addittional_exchange_rates:
                exchange_rate_list = []
                for el in addittional_exchange_rates:
                    in_count, out_count = el[0], el[1]
                    in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                    exchange_rate_list.append(
                        {
                        'in_count': in_count,
                        'out_count': out_count,
                        'min_count': el[2],
                        'max_count': el[3],
                        'rate_coefficient': el[-1],
                        }
                    )
                direction.exchange_rates = exchange_rate_list

            else:
                direction.exchange_rates = None

            direction.exchange = direction.country.exchange
            # direction.exchange_marker = 'partner'
            direction.direction_marker = 'country'
            direction.valute_from = valute_from
            direction.valute_to = valute_to
            direction.min_amount = min_amount
            direction.max_amount = max_amount
            direction.in_count = _in_count
            direction.out_count = _out_count
            direction.params = None
            direction.fromfee = None

            weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                    time_to=direction.country.time_to)

            weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                    time_to=direction.country.weekend_time_to)

            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in _partner_country.working_days.all()]

            if _valute_to.type_valute == 'ATM QR':
                bankomats = new_get_partner_bankomats_by_valute(_partner_id,
                                                                 _bankomats,
                                                                 partner_valute_dict,
                                                                 only_active=True)
            else:
                bankomats = None

            direction.info = PartnerCityInfoWithAmlSchema(
                delivery=direction.country.has_delivery,
                office=direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                high_aml=direction.country.exchange.high_aml,
                )
            country_direction_list.append(direction)

    check_set = set()

    result = []

    # for sequence in (directions, country_directions):
    for sequence in (direction_list, country_direction_list):
        for direction in sequence:
            if not direction.exchange.pk in check_set:
                check_set.add(direction.exchange_id)
                result.append(direction)

    return result


def test_get_partner_directions_with_aml(valute_from: str,
                                     valute_to: str,
                                     city: str = None,
                                     _bankomats: list[NewBankomat] | None = None,
                                     partner_valute_dict: dict | None = None):
    # valute_to
    # try:
    #     _valute_to_obj = NewValute.objects.get(code_name=valute_to)
    # except Exception:
    #     raise HTTPException(status_code=404,
    #                         detail='Valute To not found')
    
    # if _valute_to_obj.type_valute == 'ATM QR':
    #     # bankomats
    #     _bankomats = NewBankomat.objects.filter(valutes__name=_valute_to_obj.name)\
    #                                     .all()
    #     # qrvalutepartner
    #     partner_valute = NewQRValutePartner.objects.prefetch_related('bankomats')\
    #                                             .filter(valute_id=_valute_to_obj.pk)
    #     partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    # else:
    #     _bankomats = None
    #     partner_valute_dict = None

    direction_rate_prefetch = Prefetch('direction_rates',
                                       NewDirectionRate.objects.order_by('min_rate_limit'))

    directions = NewDirection.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch,
                                              'city__working_days')\
                            .annotate(direction_marker=annotate_string_field('city'))\
                            .filter(direction__valute_from_id=valute_from,
                                    direction__valute_to_id=valute_to,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)

    # country_direction_rate_prefetch = Prefetch('direction_rates',
    #                                    NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    # unavailable_cities_by_partner_country_prefetch = Prefetch('country__exclude_cities',
    #                                                         queryset=City.objects.select_related('country').filter(is_parse=True))
    # country_cities_prefetch = Prefetch('country__country__cities',
    #                                     queryset=City.objects.select_related('country').filter(is_parse=True))

    # country_directions = NewCountryDirection.objects.select_related('direction',
    #                                                              'direction__valute_from',
    #                                                              'direction__valute_to',
    #                                                              'country',
    #                                                              'country__exchange',
    #                                                              'country__exchange__account',
    #                                                              'country__country')\
    #                                             .prefetch_related(country_direction_rate_prefetch,
    #                                                               unavailable_cities_by_partner_country_prefetch,
    #                                                               country_cities_prefetch,
    #                                                             #   'country__country__cities',
    #                                                               'country__working_days')\
    #                                             .annotate(direction_marker=annotate_string_field('country'))\
    #                                             .filter(direction__valute_from=valute_from,
    #                                                     direction__valute_to=valute_to,
    #                                                     is_active=True,
    #                                                     country__exchange__is_active=True,
    #                                                     country__exchange__partner_link__isnull=False)

    if city:
        directions = directions.filter(city__city__code_name=city)
        # country_directions = country_directions.filter(country__country__cities__code_name=city)

    direction_list = []
    for direction in directions:
        direction = generate_partner_city_direction(direction,
                                                    _bankomats,
                                                    partner_valute_dict)
        direction_list.append(direction)

    # country_direction_list = []
    # if country_directions.exists():

    #     for direction in country_directions:
    #         _partner_country = direction.country

    #         excluded_cities_code_name_set = {city.code_name for city in _partner_country.exclude_cities.all()}

    #         if city is not None and city in excluded_cities_code_name_set:
    #             continue

    #         _valute_to: NewValute = direction.direction.valute_to
    #         _partner_id = direction.country.exchange.account.pk

    #         min_amount = str(int(direction.country.min_amount)) \
    #             if direction.country.min_amount else None
    #         max_amount = str(int(direction.country.max_amount)) \
    #             if direction.country.max_amount else None
            
    #         exchange_rates = direction.direction_rates.all()

    #         _in_count = direction.in_count
    #         _out_count = direction.out_count
    #         _direction_min_amount = direction.min_amount
    #         _direction_max_amount = direction.max_amount

    #         addittional_exchange_rates = None

    #         if exchange_rates:
    #             exchange_rate_list = [(el.in_count,
    #                                 el.out_count,
    #                                 el.min_rate_limit,
    #                                 el.max_rate_limit,
    #                                 el.rate_coefficient) for el in exchange_rates]
    #             exchange_rate_list.append((_in_count,
    #                                     _out_count,
    #                                     _direction_min_amount,
    #                                     _direction_max_amount,
    #                                     None))

    #             sorted_exchange_rates = sorted(exchange_rate_list,
    #                                         key=lambda el: (-el[1], el[0]))
                
    #             best_exchange_rate = sorted_exchange_rates[0]
    #             _in_count, _out_count, _, _, _ = best_exchange_rate

    #             addittional_exchange_rates = sorted_exchange_rates

    #         _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

    #         if addittional_exchange_rates:
    #             exchange_rate_list = []
    #             for el in addittional_exchange_rates:
    #                 in_count, out_count = el[0], el[1]
    #                 in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
    #                 exchange_rate_list.append(
    #                     {
    #                     'in_count': in_count,
    #                     'out_count': out_count,
    #                     'min_count': el[2],
    #                     'max_count': el[3],
    #                     'rate_coefficient': el[-1],
    #                     }
    #                 )
    #             direction.exchange_rates = exchange_rate_list

    #         else:
    #             direction.exchange_rates = None

    #         direction.exchange = direction.country.exchange
    #         # direction.exchange_marker = 'partner'
    #         direction.direction_marker = 'country'
    #         direction.valute_from = valute_from
    #         direction.valute_to = valute_to
    #         direction.min_amount = min_amount
    #         direction.max_amount = max_amount
    #         direction.in_count = _in_count
    #         direction.out_count = _out_count
    #         direction.params = None
    #         direction.fromfee = None

    #         weekdays = WeekDaySchema(time_from=direction.country.time_from,
    #                                 time_to=direction.country.time_to)

    #         weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
    #                                 time_to=direction.country.weekend_time_to)

    #         working_days = {key.upper(): value \
    #                         for key, value in WORKING_DAYS_DICT.items()}
            
    #         [working_days.__setitem__(day.code_name.upper(), True) \
    #         for day in _partner_country.working_days.all()]

    #         if _valute_to.type_valute == 'ATM QR':
    #             bankomats = new_get_partner_bankomats_by_valute(_partner_id,
    #                                                              _bankomats,
    #                                                              partner_valute_dict,
    #                                                              only_active=True)
    #         else:
    #             bankomats = None

    #         direction.info = PartnerCityInfoWithAmlSchema(
    #             delivery=direction.country.has_delivery,
    #             office=direction.country.has_office,
    #             working_days=working_days,
    #             weekdays=weekdays,
    #             weekends=weekends,
    #             bankomats=bankomats,
    #             high_aml=direction.country.exchange.high_aml,
    #             )
    #         country_direction_list.append(direction)

    # check_set = set()

    # result = []

    # for sequence in (directions, country_directions):
    # for sequence in (direction_list, country_direction_list):
    #     for direction in sequence:
    #         if not direction.exchange.pk in check_set:
    #             check_set.add(direction.exchange_id)
    #             result.append(direction)

    return direction_list


def get_partner_directions_with_location(valute_from: str,
                                         valute_to: str):
    start_time = time()
    # valute_to
    try:
        _valute_to_obj = NewValute.objects.get(code_name=valute_to)
    except Exception:
        raise HTTPException(status_code=404,
                            detail=f'Valute To not found')
    if _valute_to_obj.type_valute == 'ATM QR':
        # bankomats
        _bankomats = NewBankomat.objects.filter(valutes__name=_valute_to_obj.name)\
                                        .all()
        # qrvalutepartner
        partner_valute = NewQRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.pk)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}
    else:
        _bankomats = None
        partner_valute_dict = None

    direction_rate_prefetch = Prefetch('direction_rates',
                                       NewDirectionRate.objects.order_by('min_rate_limit'))

    directions = NewDirection.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch,
                                              'city__working_days')\
                            .annotate(direction_marker=annotate_string_field('city'))\
                            .filter(direction__valute_from_id=valute_from,
                                    direction__valute_to_id=valute_to,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       NewCountryDirectionRate.objects.order_by('min_rate_limit'))
    
    unavailable_cities_by_partner_country_prefetch = Prefetch('country__exclude_cities',
                                                            queryset=City.objects.select_related('country')\
                                                                                .filter(is_parse=True))
    country_cities_prefetch = Prefetch('country__country__cities',
                                        queryset=City.objects.select_related('country')\
                                                            .filter(is_parse=True))

    country_directions = NewCountryDirection.objects.select_related('direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch,
                                                                  unavailable_cities_by_partner_country_prefetch,
                                                                  country_cities_prefetch,
                                                                #   'country__country__cities',
                                                                  'country__working_days')\
                                                .annotate(direction_marker=annotate_string_field('country'))\
                                                .filter(direction__valute_from_id=valute_from,
                                                        direction__valute_to_id=valute_to,
                                                        is_active=True,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    direction_list = []
    for direction in directions:
        direction_dict: dict = generate_partner_city_direction_for_location(direction,
                                                                            _bankomats,
                                                                            partner_valute_dict)
        direction_list.append(direction_dict)

    country_direction_list = []
    if country_directions.exists():

        for country_direction in country_directions:
            _partner_country = country_direction.country
            _country = _partner_country.country

            country_cities: list[City] = _country.cities.all()
            excluded_cities_code_name_set = {city.code_name for city in _partner_country.exclude_cities.all()}

            _valute_to: NewValute = country_direction.direction.valute_to
            _partner_id = country_direction.country.exchange.account.pk

            min_amount = str(int(country_direction.country.min_amount)) \
                if country_direction.country.min_amount else None
            max_amount = str(int(country_direction.country.max_amount)) \
                if country_direction.country.max_amount else None
            
            exchange_rates = country_direction.direction_rates.all()

            _in_count = country_direction.in_count
            _out_count = country_direction.out_count
            _direction_min_amount = country_direction.min_amount
            _direction_max_amount = country_direction.max_amount

            addittional_exchange_rates = None

            if exchange_rates:
                exchange_rate_list = [(el.in_count,
                                    el.out_count,
                                    el.min_rate_limit,
                                    el.max_rate_limit,
                                    el.rate_coefficient) for el in exchange_rates]
                exchange_rate_list.append((_in_count,
                                        _out_count,
                                        _direction_min_amount,
                                        _direction_max_amount,
                                        None))

                sorted_exchange_rates = sorted(exchange_rate_list,
                                            key=lambda el: (-el[1], el[0]))
                
                best_exchange_rate = sorted_exchange_rates[0]
                _in_count, _out_count, _, _, _ = best_exchange_rate

                addittional_exchange_rates = sorted_exchange_rates

            _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

            common_data_dict = {
                'exchange_direction_id': country_direction.pk,
                'exchange': country_direction.country.exchange,
                # for sort
                'is_vip': country_direction.country.exchange.is_vip,
                'direction': country_direction.direction,
                'direction_marker': 'country',
                'valute_from': country_direction.direction.valute_from_id,
                'valute_to': country_direction.direction.valute_to_id,
                'params': None,
                'fromfee': None,
            }

            if addittional_exchange_rates:
                exchange_rate_list = []
                for el in addittional_exchange_rates:
                    in_count, out_count = el[0], el[1]
                    in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                    exchange_rate_list.append(
                        {
                        'in_count': in_count,
                        'out_count': out_count,
                        'min_count': el[2],
                        'max_count': el[3],
                        'rate_coefficient': el[-1],
                        }
                    )
                common_data_dict['exchange_rates'] = exchange_rate_list

            else:
                common_data_dict['exchange_rates'] = None

            # _country_direction.exchange = _country_direction.country.exchange
            # direction.exchange_marker = 'partner'
            # _country_direction.direction_marker = 'country'
            # _country_direction.valute_from = valute_from
            # _country_direction.valute_to = valute_to
            # _country_direction.min_amount = min_amount
            # _country_direction.max_amount = max_amount
            # _country_direction.in_count = _in_count
            # _country_direction.out_count = _out_count
            #
            # _country_direction.city_model = city
            # _country_direction.country_model = city.country
            #
            # _country_direction.params = None
            # _country_direction.fromfee = None

            weekdays = WeekDaySchema(time_from=country_direction.country.time_from,
                                    time_to=country_direction.country.time_to)

            weekends = WeekDaySchema(time_from=country_direction.country.weekend_time_from,
                                    time_to=country_direction.country.weekend_time_to)

            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in _partner_country.working_days.all()]

            if _valute_to.type_valute == 'ATM QR':
                bankomats = new_get_partner_bankomats_by_valute(_partner_id,
                                                                _bankomats,
                                                                partner_valute_dict,
                                                                only_active=True)
            else:
                bankomats = None

            info = PartnerCityInfoWithAmlSchema(
                delivery=country_direction.country.has_delivery,
                office=country_direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                high_aml=country_direction.country.exchange.high_aml,
                )
            
            common_data_dict.update({
                'min_amount': min_amount,
                'max_amount': max_amount,
                'in_count': _in_count,
                'out_count': _out_count,
                'country_model': country_direction.country.country,
                'info': info,
            })

            for city in country_cities:
                if city.code_name in excluded_cities_code_name_set:
                    continue
                
                country_dict = copy.deepcopy(common_data_dict)
                # _country_direction.country_model = city.country
                country_dict['city_model'] = city

                country_direction_list.append(country_dict)

    check_set = set()

    result = []

    # for sequence in (directions, country_directions):
    for sequence in (direction_list, country_direction_list):
        for direction in sequence:
            direction: dict
            check_tuple = (direction['exchange'].pk,
                           direction['direction'].valute_from_id,
                           direction['direction'].valute_to_id,
                           direction['city_model'].pk)
            
            if not check_tuple in check_set:
                check_set.add(check_tuple)
                result.append(direction)

    # print(check_set)

    print(f'time generating partner direction with location {time() - start_time} sec')

    return result



# def get_no_cash_partner_directions(valute_from: str,
#                                    valute_to: str):
#     print(valute_from, valute_to)
#     review_counts = new_get_reviews_count_filters('exchange_direction')
    
#     partner_prefetch = Prefetch('direction_rates',
#                                 queryset=NonCashDirectionRate.objects.order_by('min_rate_limit'))
    
#     directions = NonCashDirection.objects.select_related('exchange',
#                                                                  'direction',
#                                                                  'direction__valute_from',
#                                                                  'direction__valute_to')\
#                                                     .prefetch_related(partner_prefetch)\
#                                                     .annotate(positive_review_count=review_counts['positive'])\
#                                                     .annotate(neutral_review_count=review_counts['neutral'])\
#                                                     .annotate(negative_review_count=review_counts['negative'])\
#                                                     .filter(direction__valute_from=valute_from,
#                                                             direction__valute_to=valute_to,
#                                                             is_active=True,
#                                                             exchange__is_active=True)

#     direction_list = []
#     for direction in directions:

#         exchange_rates = direction.direction_rates.all()

#         _in_count = direction.in_count
#         _out_count = direction.out_count
#         _direction_min_amount = direction.min_amount
#         _direction_max_amount = direction.max_amount

#         addittional_exchange_rates = None

#         if exchange_rates:
#             exchange_rate_list = [(el.in_count,
#                                    el.out_count,
#                                    el.min_rate_limit,
#                                    el.max_rate_limit,
#                                    el.rate_coefficient) for el in exchange_rates]
#             exchange_rate_list.append((_in_count,
#                                        _out_count,
#                                        int(_direction_min_amount) if _direction_min_amount else None,
#                                        int(_direction_max_amount) if _direction_min_amount else None,
#                                        None))

#             sorted_exchange_rates = sorted(exchange_rate_list,
#                                            key=lambda el: (-el[1], el[0]))
            
#             best_exchange_rate = sorted_exchange_rates[0]
#             _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

#             addittional_exchange_rates = sorted_exchange_rates

#         print('after', _in_count, _out_count)

#         if addittional_exchange_rates:
#             direction.exchange_rates = [{'in_count': el[0],
#                                          'out_count': el[1],
#                                          'min_count': el[2],
#                                          'max_count': el[3],
#                                          'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
#         else:
#             direction.exchange_rates = None

#         direction.exchange_marker = 'partner'
#         direction.valute_from = valute_from
#         direction.valute_to = valute_to
#         direction.min_amount = str(_direction_min_amount) if _direction_min_amount else None
#         direction.max_amount = str(_direction_max_amount) if _direction_max_amount else None
#         direction.in_count = _in_count
#         direction.out_count = _out_count
#         direction.params = None
#         direction.fromfee = None

#         # direction.info = PartnerCityInfoWithAmlSchema(
#         #     high_aml=direction.exchange.high_aml,
#         #     )
#         direction_list.append(direction)
    
#     for d in direction_list:
#         print(d.__dict__)
#     return direction_list


def valid_value_for_partner_in_out_count(in_count: float,
                                         out_count: float):
    in_count = abs(float(in_count))
    out_count = abs(float(out_count))
    
    if in_count != 1:
        out_count = out_count / in_count
        in_count = 1

    if out_count < 1:
        in_count = 1 / out_count
        out_count = 1

    return (
        round(in_count, 3),
        round(out_count, 3),
        )

    # if fromfee := dict_for_exchange_direction.get('fromfee'):
    #     if in_count == 1:
    #         defferent = out_count / 100 * fromfee
    #         out_count = out_count - defferent
    #     else:
    #         defferent = in_count / 100 * fromfee
    #         in_count = in_count - defferent  
    
    # dict_for_exchange_direction['in_count'] = in_count
    # dict_for_exchange_direction['out_count'] = out_count


def new_get_no_cash_partner_directions(valute_from: str,
                                       valute_to: str):
    # print(valute_from, valute_to)
    review_counts = new_get_reviews_count_filters('exchange_direction')
    
    partner_prefetch = Prefetch('direction_rates',
                                queryset=NonCashDirectionRate.objects.order_by('min_rate_limit'))
    
    directions = NonCashDirection.objects.select_related('exchange',
                                                                 'direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to')\
                                                    .prefetch_related(partner_prefetch)\
                                                    .annotate(positive_review_count=review_counts['positive'])\
                                                    .annotate(neutral_review_count=review_counts['neutral'])\
                                                    .annotate(negative_review_count=review_counts['negative'])\
                                                    .filter(direction__valute_from=valute_from,
                                                            direction__valute_to=valute_to,
                                                            is_active=True,
                                                            exchange__is_active=True)

    direction_list = []
    for direction in directions:

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       int(_direction_min_amount) if _direction_min_amount else None,
                                       int(_direction_max_amount) if _direction_min_amount else None,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates

        # print('after', _in_count, _out_count)
        _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

        if addittional_exchange_rates:
            exchange_rate_list = []
            for el in addittional_exchange_rates:
                in_count, out_count = el[0], el[1]
                in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                exchange_rate_list.append(
                    {
                    'in_count': in_count,
                    'out_count': out_count,
                    'min_count': el[2],
                    'max_count': el[3],
                    'rate_coefficient': el[-1],
                    }
                )
            direction.exchange_rates = exchange_rate_list
            # direction.exchange_rates = [{'in_count': el[0],
            #                              'out_count': el[1],
            #                              'min_count': el[2],
            #                              'max_count': el[3],
            #                              'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None

        direction.exchange_marker = 'partner'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = str(_direction_min_amount) if _direction_min_amount else None
        direction.max_amount = str(_direction_max_amount) if _direction_max_amount else None
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        # direction.info = PartnerCityInfoWithAmlSchema(
        #     high_aml=direction.exchange.high_aml,
        #     )
        direction_list.append(direction)
    
    # for d in direction_list:
    #     print(d.__dict__)
    return direction_list


def get_no_cash_partner_directions(valute_from: str,
                                   valute_to: str):
    # print(valute_from, valute_to)
    # review_counts = new_get_reviews_count_filters('exchange_direction')
    
    partner_prefetch = Prefetch('direction_rates',
                                queryset=NewNonCashDirectionRate.objects.order_by('min_rate_limit'))
    
    directions = NewNonCashDirection.objects.select_related('exchange',
                                                                 'direction',
                                                                 'direction__valute_from',
                                                                 'direction__valute_to')\
                                                    .prefetch_related(partner_prefetch)\
                                                    .annotate(direction_marker=annotate_string_field('no_cash'))\
                                                    .filter(direction__valute_from=valute_from,
                                                            direction__valute_to=valute_to,
                                                            is_active=True,
                                                            exchange__is_active=True)
                                                    # .values(
                                                    #     'pk',
                                                    #     'exchange',
                                                    #     'direction__valute_from',
                                                    #     'direction__valute_to',
                                                    #     'in_count',
                                                    #     'out_count',
                                                    #     'min_amount',
                                                    #     'max_amount',
                                                    #     'params',
                                                    #     'fromfee',
                                                    # )\
                                                    # .annotate(positive_review_count=review_counts['positive'])\
                                                    # .annotate(neutral_review_count=review_counts['neutral'])\
                                                    # .annotate(negative_review_count=review_counts['negative'])\

    direction_list = []
    for direction in directions:

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       int(_direction_min_amount) if _direction_min_amount else None,
                                       int(_direction_max_amount) if _direction_min_amount else None,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _, _, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates

        # print('after', _in_count, _out_count)
        _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

        if addittional_exchange_rates:
            exchange_rate_list = []
            for el in addittional_exchange_rates:
                in_count, out_count = el[0], el[1]
                in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                exchange_rate_list.append(
                    {
                    'in_count': in_count,
                    'out_count': out_count,
                    'min_count': el[2],
                    'max_count': el[3],
                    'rate_coefficient': el[-1],
                    }
                )
            direction.exchange_rates = exchange_rate_list
            # direction.exchange_rates = [{'in_count': el[0],
            #                              'out_count': el[1],
            #                              'min_count': el[2],
            #                              'max_count': el[3],
            #                              'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None

        # direction.exchange_marker = 'partner'
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = str(_direction_min_amount) if _direction_min_amount else None
        direction.max_amount = str(_direction_max_amount) if _direction_max_amount else None
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        # direction.info = PartnerCityInfoWithAmlSchema(
        #     high_aml=direction.exchange.high_aml,
        #     )
        direction_list.append(direction)
    
    # for d in direction_list:
    #     print(d.__dict__)
    return direction_list


# def get_partner_directions_for_test(valute_from: str,
#                                     valute_to: str,
#                                     city: str = None):
#     print(len(connection.queries))
#     direction_name = valute_from + ' -> ' + valute_to

#     review_counts = get_reviews_count_filters('partner_direction')

#     direction_rates_prefetch = Prefetch('city__exchange__partner_rates',
#                                         DirectionRate.objects.filter(direction_marker='city',
#                                                                      exchange_id=F('city__exchange_id')))

#     directions = Direction.objects\
#                             .select_related('direction',
#                                             'direction__valute_from',
#                                             'direction__valute_to',
#                                             'city',
#                                             'city__city',
#                                             'city__exchange',
#                                             'city__exchange__account')\
#                             .prefetch_related(direction_rates_prefetch)\
#                             .annotate(positive_review_count=review_counts['positive'])\
#                             .annotate(neutral_review_count=review_counts['neutral'])\
#                             .annotate(negative_review_count=review_counts['negative'])\
#                             .filter(direction__display_name=direction_name,
#                                     is_active=True,
#                                     city__exchange__is_active=True,
#                                     city__exchange__partner_link__isnull=False)
    
#     review_counts = get_reviews_count_filters('partner_country_direction')

#     country_directions = CountryDirection.objects.select_related('direction',
#                                                                  'country',
#                                                                  'country__exchange',
#                                                                  'country__exchange__account',
#                                                                  'country__country')\
#                                                 .prefetch_related('country__country__cities')\
#                                                 .annotate(positive_review_count=review_counts['positive'])\
#                                                 .annotate(neutral_review_count=review_counts['neutral'])\
#                                                 .annotate(negative_review_count=review_counts['negative'])\
#                                                 .filter(direction__valute_from=valute_from,
#                                                         direction__valute_to=valute_to,
#                                                         is_active=True,
#                                                         country__exchange__is_active=True,
#                                                         country__exchange__partner_link__isnull=False)

#     if city:
#         directions = directions.filter(city__city__code_name=city)
#         country_directions = country_directions.filter(country__country__cities__code_name=city)

#     for direction in directions:
#         print('TEST PREFETCH',direction.__dict__)
#         print('TEST 2', direction.city.exchange.partner_rates.all())
#         city: PartnerCity = direction.city
#         _valute_to: Valute = direction.direction.valute_to
#         _partner_id = city.exchange.account.pk
        
#         min_amount = str(int(city.min_amount)) if city.min_amount else None
#         max_amount = str(int(city.max_amount)) if city.max_amount else None

#         direction.exchange = city.exchange
#         direction.exchange_marker = 'partner'
#         direction.valute_from = valute_from
#         direction.valute_to = valute_to
#         direction.min_amount = min_amount
#         direction.max_amount = max_amount
#         direction.params = None
#         direction.fromfee = None

#         weekdays = WeekDaySchema(time_from=city.time_from,
#                                  time_to=city.time_to)

#         weekends = WeekDaySchema(time_from=city.weekend_time_from,
#                                  time_to=city.weekend_time_to)


#         # working_days = WORKING_DAYS_DICT.copy()
#         working_days = {key.upper(): value \
#                         for key, value in WORKING_DAYS_DICT.items()}
        
#         [working_days.__setitem__(day.code_name.upper(), True) \
#          for day in city.working_days.all()]
#         #
#         # working_days = WORKING_DAYS_DICT.copy()
#         # [working_days.__setitem__(day.code_name, True)\
#         #   for day in direction.city.working_days.all()]
#         if _valute_to.type_valute == 'ATM QR':
#             bankomats = get_partner_bankomats_by_valute(_partner_id,
#                                                         _valute_to.name,
#                                                         only_active=True)
#         else:
#             bankomats = None

#         direction.info = PartnerCityInfoSchema2(
#             delivery=city.has_delivery,
#             office=city.has_office,
#             working_days=working_days,
#             weekdays=weekdays,
#             weekends=weekends,
#             bankomats=bankomats,
#             )


#     for direction in country_directions:
#         _valute_to: Valute = direction.direction.valute_to
#         _partner_id = direction.country.exchange.account.pk

#         min_amount = str(int(direction.country.min_amount)) \
#             if direction.country.min_amount else None
#         max_amount = str(int(direction.country.max_amount)) \
#             if direction.country.max_amount else None

#         direction.exchange = direction.country.exchange
#         direction.exchange_marker = 'partner'
#         direction.valute_from = valute_from
#         direction.valute_to = valute_to
#         direction.min_amount = min_amount
#         direction.max_amount = max_amount
#         direction.params = None
#         direction.fromfee = None

#         weekdays = WeekDaySchema(time_from=direction.country.time_from,
#                                  time_to=direction.country.time_to)

#         weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
#                                  time_to=direction.country.weekend_time_to)


#         # working_days = WORKING_DAYS_DICT.copy()
#         working_days = {key.upper(): value \
#                         for key, value in WORKING_DAYS_DICT.items()}
        
#         [working_days.__setitem__(day.code_name.upper(), True) \
#          for day in direction.country.working_days.all()]
#         #
#         # working_days = WORKING_DAYS_DICT.copy()
#         # [working_days.__setitem__(day.code_name, True)\
#         #   for day in direction.city.working_days.all()]
#         if _valute_to.type_valute == 'ATM QR':
#             bankomats = get_partner_bankomats_by_valute(_partner_id,
#                                                         _valute_to.name,
#                                                         only_active=True)
#         else:
#             bankomats = None

#         direction.info = PartnerCityInfoSchema2(
#             delivery=direction.country.has_delivery,
#             office=direction.country.has_office,
#             working_days=working_days,
#             weekdays=weekdays,
#             weekends=weekends,
#             bankomats=bankomats,
#             )

#     # print(directions)
#     # print(country_directions)

#     check_set = set()

#     result = []

#     for sequence in (directions, country_directions):
#         for direction in sequence:
#             if not direction.exchange in check_set:
#                 check_set.add(direction.exchange)
#                 result.append(direction)

#     print(len(connection.queries))
#     print(connection.queries)
#     return result

def convert_min_max_count(exchange_rate: dict,
                          marker: Literal['main','additional']):
    if marker == 'main':
        _min = 'min_amount'
        _max = 'max_amount'
    else:
        _min = 'min_rate_limit'
        _max = 'max_rate_limit'
        
    exchange_rate[_min] = exchange_rate.pop('min_count')
    exchange_rate[_max] = exchange_rate.pop('max_count')


def get_partner_directions3(valute_from: str,
                           valute_to: str):
    print('here')
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    review_counts = get_reviews_count_filters('partner_country_direction')

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related('country__exchange__partner_cities')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)

    # if city:
    #     directions = directions.filter(city__city__code_name=city)
    #     country_directions = country_directions.filter(country__country__cities__code_name=city)

    for direction in directions:
        city: PartnerCity = direction.city
        _valute_to = direction.direction.valute_to
        _partner_id = city.exchange.account.pk

        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        # direction.direction_marker = 'city'
        direction.__setattr__('direction_marker', 'city')
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]
        #
        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True)\
        #   for day in direction.city.working_days.all()]
        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        # print(bankomats)

        direction.info = PartnerCityInfoSchema2(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            )


    country_directions_with_city = []

    for direction in country_directions:
        _valute_to = direction.direction.valute_to
        _partner_id = direction.country.exchange.account.pk

        for city in direction.country.exchange.partner_cities.filter(city__country_id=direction.country.country.pk).all():
            # print(city)
            # print(direction.__dict__)

            _direction_dict = direction.__dict__.copy()

            _direction_dict.pop('_state')
            _direction_dict.pop('_prefetched_objects_cache')
            positive_review_count = _direction_dict.pop('positive_review_count')
            neutral_review_count = _direction_dict.pop('neutral_review_count')
            negative_review_count = _direction_dict.pop('negative_review_count')


            new_direction = CountryDirection(**_direction_dict)

            new_direction.__setattr__('positive_review_count', positive_review_count)
            new_direction.__setattr__('neutral_review_count', neutral_review_count)
            new_direction.__setattr__('negative_review_count', negative_review_count)
            
            min_amount = str(int(direction.country.min_amount)) \
                if direction.country.min_amount else None
            max_amount = str(int(direction.country.max_amount)) \
                if direction.country.max_amount else None

            # country_direction_with_city = {
            #     'exchange' : direction.country.exchange,
            #     'exchange_marker' : 'partner',
            #     'valute_from' : valute_from,
            #     'valute_to' : valute_to,
            #     'min_amount' : min_amount,
            #     'max_amount' : max_amount,
            #     'params' : None,
            #     'fromfee' : None,
            # }

            new_direction.exchange = direction.country.exchange
            new_direction.exchange_marker = 'partner'
            new_direction.direction_marker = 'country'
            new_direction.__setattr__('direction_marker', 'country')
            new_direction.valute_from = valute_from
            new_direction.valute_to = valute_to
            new_direction.min_amount = min_amount
            new_direction.max_amount = max_amount
            new_direction.params = None
            new_direction.fromfee = None
            new_direction.city = city

            weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                    time_to=direction.country.time_to)

            weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                    time_to=direction.country.weekend_time_to)


            # working_days = WORKING_DAYS_DICT.copy()
            working_days = {key.upper(): value \
                            for key, value in WORKING_DAYS_DICT.items()}
            
            [working_days.__setitem__(day.code_name.upper(), True) \
            for day in direction.country.working_days.all()]
            #
            # working_days = WORKING_DAYS_DICT.copy()
            # [working_days.__setitem__(day.code_name, True)\
            #   for day in direction.city.working_days.all()]
            if _valute_to.type_valute == 'ATM QR':
                bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                            _valute_to.name,
                                                            only_active=True)
            else:
                bankomats = None

            # print(bankomats)

            new_direction.info = PartnerCityInfoSchema2(
                delivery=direction.country.has_delivery,
                office=direction.country.has_office,
                working_days=working_days,
                weekdays=weekdays,
                weekends=weekends,
                bankomats=bankomats,
                )
            # new_direction.info.bankomats = None

            
            country_directions_with_city.append(new_direction)
            
            

    # print(country_directions_with_city)
    # print(directions)

    check_set = set()

    result = []

    for sequence in (country_directions_with_city, directions):
        for direction in sequence:
            if not (direction.exchange, direction.city) in check_set:
                check_set.add((direction.exchange, direction.city))
                result.append(direction)

    return result


def test_get_partner_directions3(valute_from: str,
                           valute_to: str):
    #valute_to
    _valute_to_obj = Valute.objects.get(code_name=valute_to)
    if _valute_to_obj.type_valute == 'ATM QR':
        #bankomats
        _bankomats = Bankomat.objects.prefetch_related('valutes')\
                                .filter(valutes__name=_valute_to_obj.name)\
                                .all()
        #qrvalutepartner
        partner_valute = QRValutePartner.objects.prefetch_related('bankomats')\
                                                .filter(valute_id=_valute_to_obj.name)
        partner_valute_dict = {p_v.partner_id: p_v for p_v in partner_valute}

    direction_name = valute_from + ' -> ' + valute_to

    review_counts = new_get_reviews_count_filters('partner_direction')

    direction_rate_prefetch = Prefetch('direction_rates',
                                       DirectionRate.objects.order_by('min_rate_limit'))

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange',
                                            'city__exchange__account')\
                            .prefetch_related(direction_rate_prefetch)\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__is_active=True,
                                    city__exchange__partner_link__isnull=False)
    
    review_counts = new_get_reviews_count_filters('partner_country_direction')

    country_direction_rate_prefetch = Prefetch('direction_rates',
                                       CountryDirectionRate.objects.order_by('min_rate_limit'))

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
                                                                 'country__exchange__account',
                                                                 'country__country')\
                                                .prefetch_related(country_direction_rate_prefetch)\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(is_active=True,
                                                        direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
                                                        country__exchange__is_active=True,
                                                        country__exchange__partner_link__isnull=False)
    
    partner_cities = PartnerCity.objects.select_related('exchange',
                                                        'exchange__account',
                                                        'city',
                                                        'city__country')\
                                        .prefetch_related('working_days').all()
    partner_cities_dict = {_city.pk: _city for _city in partner_cities}

    direction_list = []
    for direction in directions:
        # city: PartnerCity = direction.city
        city = partner_cities_dict.get(direction.city.pk)
        _valute_to = direction.direction.valute_to
        _partner_id = city.exchange.account.pk


        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        exchange_rates = direction.direction_rates.all()

        _in_count = direction.in_count
        _out_count = direction.out_count
        _direction_min_amount = direction.min_amount
        _direction_max_amount = direction.max_amount

        addittional_exchange_rates = None

        if exchange_rates:
            exchange_rate_list = [(el.in_count,
                                   el.out_count,
                                   el.min_rate_limit,
                                   el.max_rate_limit,
                                   el.rate_coefficient) for el in exchange_rates]
            exchange_rate_list.append((_in_count,
                                       _out_count,
                                       _direction_min_amount,
                                       _direction_max_amount,
                                       None))

            sorted_exchange_rates = sorted(exchange_rate_list,
                                           key=lambda el: (-el[1], el[0]))
            
            best_exchange_rate = sorted_exchange_rates[0]
            _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

            addittional_exchange_rates = sorted_exchange_rates

        # print('after', _in_count, _out_count)
        _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

        if addittional_exchange_rates:
            exchange_rate_list = []
            for el in addittional_exchange_rates:
                in_count, out_count = el[0], el[1]
                in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                exchange_rate_list.append(
                    {
                    'in_count': in_count,
                    'out_count': out_count,
                    'min_count': el[2],
                    'max_count': el[3],
                    'rate_coefficient': el[-1],
                    }
                )
            direction.exchange_rates = exchange_rate_list

        # if addittional_exchange_rates:
        #     direction.exchange_rates = [{'in_count': el[0],
        #                                  'out_count': el[1],
        #                                  'min_count': el[2],
        #                                  'max_count': el[3],
        #                                  'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
        else:
            direction.exchange_rates = None


        direction.exchange = city.exchange
        direction.exchange_marker = 'partner'
        direction.__setattr__('direction_marker', 'city')
        direction.valute_from = valute_from
        direction.valute_to = valute_to
        direction.min_amount = min_amount
        direction.max_amount = max_amount
        direction.in_count = _in_count
        direction.out_count = _out_count
        direction.params = None
        direction.fromfee = None

        weekdays = WeekDaySchema(time_from=city.time_from,
                                 time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                 time_to=city.weekend_time_to)

        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        if _valute_to.type_valute == 'ATM QR':
            bankomats = get_partner_bankomats_by_valute(_partner_id,
                                                        _valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.info = PartnerCityInfoSchema2(
            delivery=city.has_delivery,
            office=city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            bankomats=bankomats,
            )
        direction_list.append(direction)

    country_directions_with_city = []

    if country_directions.exists():
        #partnercity with workingdays
        partner_cities = PartnerCity.objects.select_related('exchange',
                                                            'city',
                                                            'city__country')\
                                            .prefetch_related('working_days')\
                                            .all()
        partner_cities_dict = {}
        for _city in partner_cities:
            partner_cities_dict[_city.exchange_id] = partner_cities_dict.get(_city.exchange_id,
                                                                             list()) \
                                                        + [_city]
        
        for direction in country_directions:
            _valute_to = direction.direction.valute_to
            _partner_id = direction.country.exchange.account.pk

            partner_cities_by_exchange = partner_cities_dict.get(direction.country.exchange_id,
                                                                 list())

            partner_cities_by_country = [_city for _city in partner_cities_by_exchange \
                                         if _city.city.country.pk == direction.country.country.pk]

            # for city in direction.country.exchange.partner_cities.filter(city__country_id=direction.country.country.pk).all():
            for city in partner_cities_by_country:

                _direction_dict = direction.__dict__.copy()

                _direction_dict.pop('_state')
                _direction_dict.pop('_prefetched_objects_cache')
                positive_review_count = _direction_dict.pop('positive_review_count')
                neutral_review_count = _direction_dict.pop('neutral_review_count')
                negative_review_count = _direction_dict.pop('negative_review_count')

                new_direction = CountryDirection(**_direction_dict)

                new_direction.__setattr__('positive_review_count', positive_review_count)
                new_direction.__setattr__('neutral_review_count', neutral_review_count)
                new_direction.__setattr__('negative_review_count', negative_review_count)
                
                min_amount = str(int(direction.country.min_amount)) \
                    if direction.country.min_amount else None
                max_amount = str(int(direction.country.max_amount)) \
                    if direction.country.max_amount else None
                
                exchange_rates = direction.direction_rates.all()

                _in_count = direction.in_count
                _out_count = direction.out_count
                _direction_min_amount = direction.min_amount
                _direction_max_amount = direction.max_amount

                addittional_exchange_rates = None

                if exchange_rates:
                    exchange_rate_list = [(el.in_count,
                                        el.out_count,
                                        el.min_rate_limit,
                                        el.max_rate_limit,
                                        el.rate_coefficient) for el in exchange_rates]
                    exchange_rate_list.append((_in_count,
                                            _out_count,
                                            _direction_min_amount,
                                            _direction_max_amount,
                                            None))

                    sorted_exchange_rates = sorted(exchange_rate_list,
                                                key=lambda el: (-el[1], el[0]))
                    
                    best_exchange_rate = sorted_exchange_rates[0]
                    _in_count, _out_count, _min_amount, _max_amount, _ = best_exchange_rate

                    addittional_exchange_rates = sorted_exchange_rates

                # print('after', _in_count, _out_count)
                _in_count, _out_count = valid_value_for_partner_in_out_count(_in_count, _out_count)

                if addittional_exchange_rates:
                    exchange_rate_list = []
                    for el in addittional_exchange_rates:
                        in_count, out_count = el[0], el[1]
                        in_count, out_count = valid_value_for_partner_in_out_count(in_count, out_count)
                        exchange_rate_list.append(
                            {
                            'in_count': in_count,
                            'out_count': out_count,
                            'min_count': el[2],
                            'max_count': el[3],
                            'rate_coefficient': el[-1],
                            }
                        )
                    new_direction.exchange_rates = exchange_rate_list

                # if addittional_exchange_rates:
                #     new_direction.exchange_rates = [{'in_count': el[0],
                #                                 'out_count': el[1],
                #                                 'min_count': el[2],
                #                                 'max_count': el[3],
                #                                 'rate_coefficient': el[-1]} for el in addittional_exchange_rates]
                else:
                    new_direction.exchange_rates = None

                new_direction.exchange = direction.country.exchange
                new_direction.exchange_marker = 'partner'
                new_direction.direction_marker = 'country'
                # new_direction.__setattr__('direction_marker', 'country')
                new_direction.valute_from = valute_from
                new_direction.valute_to = valute_to
                new_direction.min_amount = min_amount
                new_direction.max_amount = max_amount
                new_direction.in_count = _in_count
                new_direction.out_count = _out_count
                new_direction.params = None
                new_direction.fromfee = None
                new_direction.city = city

                weekdays = WeekDaySchema(time_from=direction.country.time_from,
                                        time_to=direction.country.time_to)

                weekends = WeekDaySchema(time_from=direction.country.weekend_time_from,
                                        time_to=direction.country.weekend_time_to)

                working_days = {key.upper(): value \
                                for key, value in WORKING_DAYS_DICT.items()}
                
                # [working_days.__setitem__(day.code_name.upper(), True) \
                # for day in direction.country.working_days.all()]
                [working_days.__setitem__(day.code_name.upper(), True) \
                    for day in city.working_days.all()]

                if _valute_to.type_valute == 'ATM QR':
                    # bankomats = get_partner_bankomats_by_valute(_partner_id,
                    #                                             _valute_to.name,
                    #                                             only_active=True)
                    bankomats = test_get_partner_bankomats_by_valute(_partner_id,
                                                                    _bankomats,
                                                                    partner_valute_dict,
                                                                    only_active=True)
                else:
                    bankomats = None

                new_direction.info = PartnerCityInfoSchema2(
                    delivery=direction.country.has_delivery,
                    office=direction.country.has_office,
                    working_days=working_days,
                    weekdays=weekdays,
                    weekends=weekends,
                    bankomats=bankomats,
                    )
                                
                country_directions_with_city.append(new_direction)

    check_set = set()

    result = []
    # for sequence in (country_directions_with_city, directions):
    for sequence in (country_directions_with_city, direction_list):
        for direction in sequence:
            if not (direction.exchange, direction.city) in check_set:
                check_set.add((direction.exchange, direction.city))
                result.append(direction)

    return result


# def get_partner_directions_with_location(valute_from: str,
#                                          valute_to: str):
#     direction_name = valute_from + ' -> ' + valute_to

#     review_counts = get_reviews_count_filters('partner_direction')

#     directions = Direction.objects\
#                             .select_related('direction',
#                                             'direction__valute_from',
#                                             'direction__valute_to',
#                                             'city',
#                                             'city__city',
#                                             'city__city__country',
#                                             'city__exchange')\
#                             .annotate(positive_review_count=review_counts['positive'])\
#                             .annotate(neutral_review_count=review_counts['neutral'])\
#                             .annotate(negative_review_count=review_counts['negative'])\
#                             .filter(direction__display_name=direction_name,
#                                     is_active=True,
#                                     city__exchange__partner_link__isnull=False)

#     for direction in directions:
#         city: PartnerCity = direction.city
#         min_amount = str(int(city.min_amount)) if city.min_amount else None
#         max_amount = str(int(city.max_amount)) if city.max_amount else None

#         direction.exchange = direction.city.exchange
#         direction.exchange_marker = 'partner'
#         direction.valute_from = valute_from
#         direction.valute_to = valute_to
#         direction.min_amount = min_amount
#         direction.max_amount = max_amount
#         direction.params = None
#         direction.fromfee = None

#         weekdays = WeekDaySchema(time_from=city.time_from,
#                                  time_to=city.time_to)

#         weekends = WeekDaySchema(time_from=city.weekend_time_from,
#                                  time_to=city.weekend_time_to)

#         # working_days = WORKING_DAYS_DICT.copy()
#         # [working_days.__setitem__(day.code_name, True)\
#         #   for day in direction.city.working_days.all()]
#         working_days = {key.upper(): value \
#                         for key, value in WORKING_DAYS_DICT.items()}
        
#         [working_days.__setitem__(day.code_name.upper(), True) \
#          for day in city.working_days.all()]

#         direction.info = PartnerCityInfoSchema2(
#             delivery=direction.city.has_delivery,
#             office=direction.city.has_office,
#             working_days=working_days,
#             weekdays=weekdays,
#             weekends=weekends,
#             )

#     return directions


def generate_partner_cities(partner_cities: list[PartnerCity]):
    for city in partner_cities:
        city.name = city.city.name
        city.code_name = city.city.code_name
        city.country = city.city.country.name
        city.country_flag = try_generate_icon_url(city.city.country)

        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True) for day in city.working_days.all()]
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        city.info = PartnerCityInfoSchema(delivery=city.has_delivery,
                                          office=city.has_office,
                                          working_days=working_days,
                                          time_from=city.time_from,
                                          time_to=city.time_to)
        date = time = None

        if city.time_update:
            date, time = city.time_update.astimezone().strftime('%d.%m.%Y %H:%M').split()
        
        city.updated = UpdatedTimeByPartnerCitySchema(date=date,
                                                      time=time)
        
    # print(len(connection.queries))
    return partner_cities


def generate_partner_cities2(partner_cities: list[PartnerCity]):
    for city in partner_cities:
        city.city_multiple_name = MultipleName(name=city.city.name,
                                               en_name=city.city.en_name)
        city.code_name = city.city.code_name
        city.country_multiple_name = MultipleName(name=city.city.country.name,
                                                  en_name=city.city.country.en_name)
        city.country_flag = try_generate_icon_url(city.city.country)

        weekdays = WeekDaySchema(time_from=city.time_from,
                                      time_to=city.time_to)

        weekends = WeekDaySchema(time_from=city.weekend_time_from,
                                      time_to=city.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        city.info = PartnerCityInfoSchema2(delivery=city.has_delivery,
                                          office=city.has_office,
                                          working_days=working_days,
                                          weekdays=weekdays,
                                          weekends=weekends,
                                          bankomats=None)
        date = time = None

        if city.time_update:
            date, time = city.time_update.astimezone().strftime('%d.%m.%Y %H:%M').split()
        
        city.updated = UpdatedTimeByPartnerCitySchema(date=date,
                                                      time=time)
        
    # print(len(connection.queries))
    return partner_cities


def generate_partner_cities(partner_cities: list[PartnerCity]):
    for city in partner_cities:
        city.name = city.city.name
        city.code_name = city.city.code_name
        city.country = city.city.country.name
        city.country_flag = try_generate_icon_url(city.city.country)

        # working_days = WORKING_DAYS_DICT.copy()
        # [working_days.__setitem__(day.code_name, True) for day in city.working_days.all()]
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        city.info = PartnerCityInfoSchema(delivery=city.has_delivery,
                                          office=city.has_office,
                                          working_days=working_days,
                                          time_from=city.time_from,
                                          time_to=city.time_to)
        date = time = None

        if city.time_update:
            date, time = city.time_update.astimezone().strftime('%d.%m.%Y %H:%M').split()
        
        city.updated = UpdatedTimeByPartnerCitySchema(date=date,
                                                      time=time)
        
    # print(len(connection.queries))
    return partner_cities


def generate_partner_countries(partner_countries: list[PartnerCountry]):
    for country in partner_countries:
        country.country_multiple_name = MultipleName(name=country.country.name,
                                                     en_name=country.country.en_name)
        country.country_flag = try_generate_icon_url(country.country)

        weekdays = WeekDaySchema(time_from=country.time_from,
                                      time_to=country.time_to)

        weekends = WeekDaySchema(time_from=country.weekend_time_from,
                                      time_to=country.weekend_time_to)


        # working_days = WORKING_DAYS_DICT.copy()
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in country.working_days.all()]

        country.info = PartnerCityInfoSchema2(delivery=country.has_delivery,
                                              office=country.has_office,
                                              working_days=working_days,
                                              weekdays=weekdays,
                                              weekends=weekends,
                                              bankomats=None)
        date = time = None

        if country.time_update:
            date, time = country.time_update.astimezone().strftime('%d.%m.%Y %H:%M').split()
        
        country.updated = UpdatedTimeByPartnerCitySchema(date=date,
                                                      time=time)
        
    # print(len(connection.queries))
    return partner_countries


def generate_partner_directions_by_city(directions: list[Direction]):
    for direction in directions:
        direction.valute_from = direction.direction.valute_from.code_name
        direction.icon_valute_from = try_generate_icon_url(direction.direction.valute_from)
        direction.in_count_type = direction.direction.valute_from.type_valute

        direction.valute_to = direction.direction.valute_to.code_name
        direction.icon_valute_to = try_generate_icon_url(direction.direction.valute_to)
        direction.out_count_type = direction.direction.valute_to.type_valute

    # print(len(connection.queries))
    return directions


def generate_partner_directions_by_city2(directions: list[Direction],
                                        marker: str):
    for direction in directions:
        print(direction.__dict__)
        if direction.direction.valute_to.type_valute == 'ATM QR':
            match marker:
                case 'country':
                    partner_id = direction.country.exchange.account.pk
                case 'city':
                    partner_id = direction.city.exchange.account.pk
            # partner_valute = QRValutePartner.objects.filter(partner_id=partner_id,
            #                                            valute=direction.direction.valute_to.name)
            # if partner_valute.exists():
            #     bankomats = get_partner_bankomats_by_valute(partner_id,
            #                                                 direction.direction.valute_to.name)
            # else:
            #     bankomats = None
            bankomats = get_partner_bankomats_by_valute(partner_id,
                                                        direction.direction.valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.valute_from = direction.direction.valute_from.code_name
        direction.icon_valute_from = try_generate_icon_url(direction.direction.valute_from)
        direction.in_count_type = direction.direction.valute_from.type_valute

        direction.valute_to = direction.direction.valute_to.code_name
        direction.icon_valute_to = try_generate_icon_url(direction.direction.valute_to)
        direction.out_count_type = direction.direction.valute_to.type_valute
        direction.bankomats = bankomats


    # print(len(connection.queries))
    return directions


def generate_partner_directions_by_3(directions: list[Direction],
                                     marker: str):
    for direction in directions:
        # print(direction.__dict__)
        if direction.direction.valute_to.type_valute == 'ATM QR':
            match marker:
                case 'country':
                    partner_id = direction.country.exchange.account.pk
                case 'city':
                    partner_id = direction.city.exchange.account.pk
                case _:
                    raise HTTPException(status_code=400,
                                        detail='ATM QR in non cash direction!')
            # partner_valute = QRValutePartner.objects.filter(partner_id=partner_id,
            #                                            valute=direction.direction.valute_to.name)
            # if partner_valute.exists():
            #     bankomats = get_partner_bankomats_by_valute(partner_id,
            #                                                 direction.direction.valute_to.name)
            # else:
            #     bankomats = None
            bankomats = get_partner_bankomats_by_valute(partner_id,
                                                        direction.direction.valute_to.name,
                                                        only_active=True)
        else:
            bankomats = None

        direction.valute_from = direction.direction.valute_from.code_name
        direction.icon_valute_from = try_generate_icon_url(direction.direction.valute_from)
        direction.in_count_type = direction.direction.valute_from.type_valute

        direction.valute_to = direction.direction.valute_to.code_name
        direction.icon_valute_to = try_generate_icon_url(direction.direction.valute_to)
        direction.out_count_type = direction.direction.valute_to.type_valute
        direction.bankomats = bankomats

        exchange_rates = []
        
        main_exchange_rate = {
            'min_count': direction.min_amount,
            'max_count': direction.max_amount,
            'in_count': direction.in_count,
            'out_count': direction.out_count,
        }
        exchange_rates.append(main_exchange_rate)

        for direction_rate in direction.direction_rates.all():
            additional_direction_rate = {
                'id': direction_rate.pk,
                'min_count': direction_rate.min_rate_limit,
                'max_count': direction_rate.max_rate_limit,
                'in_count': direction_rate.in_count,
                'out_count': direction_rate.out_count,
                'rate_coefficient': direction_rate.rate_coefficient,
            }
            exchange_rates.append(additional_direction_rate)
        
        direction.exchange_rates = exchange_rates

    # print(len(connection.queries))
    return directions


def generate_partner_directions_by(directions: list[NewDirection | NewCountryDirection],
                                   marker: str):
    for direction in directions:
        # print(direction.__dict__)
        if direction.direction.valute_to.type_valute == 'ATM QR':
            match marker:
                case 'country':
                    partner_id = direction.exchange.account.pk
                case 'city':
                    partner_id = direction.exchange.account.pk
                case _:
                    raise HTTPException(status_code=400,
                                        detail='ATM QR in non cash direction!')

            bankomats = get_bankomats_by_valute(partner_id,
                                                direction.direction.valute_to.pk,
                                                only_active=True)
        else:
            bankomats = None

        direction.valute_from = direction.direction.valute_from.code_name
        direction.icon_valute_from = try_generate_icon_url(direction.direction.valute_from)
        direction.in_count_type = direction.direction.valute_from.type_valute

        direction.valute_to = direction.direction.valute_to.code_name
        direction.icon_valute_to = try_generate_icon_url(direction.direction.valute_to)
        direction.out_count_type = direction.direction.valute_to.type_valute
        direction.bankomats = bankomats

        exchange_rates = []
        
        main_exchange_rate = {
            'min_count': direction.min_amount,
            'max_count': direction.max_amount,
            'in_count': direction.in_count,
            'out_count': direction.out_count,
        }
        exchange_rates.append(main_exchange_rate)

        for direction_rate in direction.direction_rates.all():
            additional_direction_rate = {
                'id': direction_rate.pk,
                'min_count': direction_rate.min_rate_limit,
                'max_count': direction_rate.max_rate_limit,
                'in_count': direction_rate.in_count,
                'out_count': direction_rate.out_count,
                'rate_coefficient': direction_rate.rate_coefficient,
            }
            exchange_rates.append(additional_direction_rate)
        
        direction.exchange_rates = exchange_rates

    # print(len(connection.queries))
    return directions


def generate_valute_list(queries: list[CashDirection],
                         marker: str):
    valute_list = sorted({query.__getattribute__(marker) for query in queries},
                         key=lambda el: el.code_name)

    json_dict = defaultdict(list)

    for _id, valute in enumerate(valute_list, start=1):
        type_valute = valute.type_valute

        valute_dict = {
            'id': _id,
            'name': valute.name,
            'code_name': valute.code_name,
            'icon_url': try_generate_icon_url(valute),
            'type_valute': type_valute,
        }

        json_dict[type_valute].append(valute_dict)
    # print(len(connection.queries))
    return json_dict


def generate_valute_list2(queries: list[CashDirection],
                         marker: str):
    valute_list = sorted({query.__getattribute__(marker) for query in queries},
                         key=lambda el: el.code_name)

    json_dict = defaultdict(list)

    for _id, valute in enumerate(valute_list, start=1):
        type_valute = valute.type_valute

        valute_dict = {
            'id': _id,
            'name': MultipleName2(ru=valute.name,
                                 en=valute.en_name),
            'code_name': valute.code_name,
            'icon_url': try_generate_icon_url(valute),
            'type_valute': type_valute,
        }

        json_dict[type_valute].append(valute_dict)
    # print(len(connection.queries))
    return json_dict


def generate_actual_course(direction: CashDirection):
    in_out_count = get_partner_in_out_count(direction.actual_course)
    icon_valute_from = try_generate_icon_url(direction.valute_from)
    icon_valute_to = try_generate_icon_url(direction.valute_to)

    if in_out_count is not None:
        in_count, out_count = in_out_count
    else:
        in_count = out_count = 0

    return {
        'valute_from': direction.valute_from.code_name,
        'icon_valute_from': icon_valute_from,
        'in_count': in_count,
        'valute_to': direction.valute_to.code_name,
        'icon_valute_to': icon_valute_to,
        'out_count': out_count,
    }


def try_add_bankomats_to_valute(partner_id: int,
                                valute_to: str,
                                bankomats: list):
    try:
        valute_id = Valute.objects.get(code_name=valute_to).name
    except Exception:
        pass
    else:
        selected_bankomats = [bankomat.get('id') for bankomat in bankomats \
                              if bankomat.get('available')]
        unselected_bankomats = [bankomat.get('id') for bankomat in bankomats \
                              if not bankomat.get('available')]
        with transaction.atomic():
            partner_valute, _ = QRValutePartner.objects.get_or_create(partner_id=partner_id,
                                                                    valute_id=valute_id)
            
            # bankomat_ids = [bankomat.get('id') for bankomat in bankomats if bankomat.get('available')]
            # for bankomat in bankomats:
            partner_valute.bankomats.add(*selected_bankomats)
            partner_valute.bankomats.remove(*unselected_bankomats)


def new_try_add_bankomats_to_valute(partner_id: int,
                                    valute_to: str,
                                    bankomats: list):
    try:
        valute_id = NewValute.objects.get(code_name=valute_to).pk
    except Exception:
        pass
    else:
        selected_bankomats = [bankomat.get('id') for bankomat in bankomats \
                              if bankomat.get('available')]
        unselected_bankomats = [bankomat.get('id') for bankomat in bankomats \
                              if not bankomat.get('available')]
        with transaction.atomic():
            partner_valute, _ = NewQRValutePartner.objects.get_or_create(partner_id=partner_id,
                                                                         valute_id=valute_id)
            
            partner_valute.bankomats.add(*selected_bankomats)
            partner_valute.bankomats.remove(*unselected_bankomats)



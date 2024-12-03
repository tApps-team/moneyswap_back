from collections import defaultdict

from django.db.models import Count, Q
from django.db import connection, transaction

from general_models.utils.endpoints import try_generate_icon_url, get_reviews_count_filters

from general_models.schemas import MultipleName, MultipleName2

from general_models.models import Valute

from cash.models import Direction as CashDirection

from partners.models import (Direction,
                             PartnerCity,
                             CountryDirection,
                             PartnerCountry,
                             QRValutePartner,
                             Bankomat)

from partners.schemas import (PartnerCityInfoSchema,
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


# def get_partner_directions(city: str,
#                            valute_from: str,
#                            valute_to: str):
#     direction_name = valute_from + ' -> ' + valute_to

#     review_counts = get_reviews_count_filters('partner_direction')

#     directions = Direction.objects\
#                             .select_related('direction',
#                                             'direction__valute_from',
#                                             'direction__valute_to',
#                                             'city',
#                                             'city__city',
#                                             'city__exchange')\
#                             .annotate(positive_review_count=review_counts['positive'])\
#                             .annotate(neutral_review_count=review_counts['neutral'])\
#                             .annotate(negative_review_count=review_counts['negative'])\
#                             .filter(direction__display_name=direction_name,
#                                     city__city__code_name=city,
#                                     is_active=True,
#                                     city__exchange__partner_link__isnull=False)

#     for direction in directions:
#         direction.exchange = direction.city.exchange
#         direction.exchange_marker = 'partner'
#         direction.valute_from = valute_from
#         direction.valute_to = valute_to
#         direction.min_amount = None
#         direction.max_amount = None
#         direction.params = None
#         direction.fromfee = None
#         #
#         working_days = WORKING_DAYS_DICT.copy()
#         [working_days.__setitem__(day.code_name, True)\
#           for day in direction.city.working_days.all()]

#         direction.info = PartnerCityInfoSchema(
#             delivery=direction.city.has_delivery,
#             office=direction.city.has_office,
#             working_days=working_days,
#             time_from=direction.city.time_from,
#             time_to=direction.city.time_to
#             )
#         #
#     return directions

def get_partner_bankomats_by_valute(partner_id: int,
                                    valute: str,
                                    only_active: bool = False):
    bankomats = Bankomat.objects.all()

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
                'available': bankomat.pk in partner_valute_bankomats
            }
            partner_bankomats.append(partner_bankomat)
    else:
        for bankomat in bankomats:
            partner_bankomat = {
                'id': bankomat.pk,
                'name': bankomat.name,
                'available': False,
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
                                                                 'country',
                                                                 'country__country')\
                                                .prefetch_related('country__country__cities')\
                                                .annotate(positive_review_count=review_counts['positive'])\
                                                .annotate(neutral_review_count=review_counts['neutral'])\
                                                .annotate(negative_review_count=review_counts['negative'])\
                                                .filter(direction__valute_from=valute_from,
                                                        direction__valute_to=valute_to,
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
                                                        _valute_to.name)
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
        min_amount = str(int(direction.country.min_amount)) \
            if direction.country.min_amount else None
        max_amount = str(int(direction.country.max_amount)) \
            if direction.country.max_amount else None

        direction.exchange = direction.country.exchange
        direction.exchange_marker = 'partner'
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

        direction.info = PartnerCityInfoSchema2(
            delivery=direction.country.has_delivery,
            office=direction.country.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
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


def get_partner_directions3(valute_from: str,
                           valute_to: str):
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
    
    review_counts = get_reviews_count_filters('partner_country_direction')

    country_directions = CountryDirection.objects.select_related('direction',
                                                                 'direction__valute_to',
                                                                 'country',
                                                                 'country__exchange',
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


def get_partner_directions_with_location(valute_from: str,
                                         valute_to: str):
    direction_name = valute_from + ' -> ' + valute_to

    review_counts = get_reviews_count_filters('partner_direction')

    directions = Direction.objects\
                            .select_related('direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city',
                                            'city__city',
                                            'city__city__country',
                                            'city__exchange')\
                            .annotate(positive_review_count=review_counts['positive'])\
                            .annotate(neutral_review_count=review_counts['neutral'])\
                            .annotate(negative_review_count=review_counts['negative'])\
                            .filter(direction__display_name=direction_name,
                                    is_active=True,
                                    city__exchange__partner_link__isnull=False)

    for direction in directions:
        city: PartnerCity = direction.city
        min_amount = str(int(city.min_amount)) if city.min_amount else None
        max_amount = str(int(city.max_amount)) if city.max_amount else None

        direction.exchange = direction.city.exchange
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
        # [working_days.__setitem__(day.code_name, True)\
        #   for day in direction.city.working_days.all()]
        working_days = {key.upper(): value \
                        for key, value in WORKING_DAYS_DICT.items()}
        
        [working_days.__setitem__(day.code_name.upper(), True) \
         for day in city.working_days.all()]

        direction.info = PartnerCityInfoSchema2(
            delivery=direction.city.has_delivery,
            office=direction.city.has_office,
            working_days=working_days,
            weekdays=weekdays,
            weekends=weekends,
            )

    return directions


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
                                          weekends=weekends)
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
                                              weekends=weekends)
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



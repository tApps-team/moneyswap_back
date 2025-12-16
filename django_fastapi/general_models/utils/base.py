from datetime import datetime, timedelta

from django_celery_beat.models import IntervalSchedule

from django.db.models import CharField, Value, IntegerField
from django.conf import settings
from django.utils import timezone

from fastapi import APIRouter

from general_models.models import PartnerTimeUpdate

import no_cash.models as no_cash_models
import cash.models as cash_models


DEFAUT_ROUND = 3

v2_api_router = APIRouter(prefix='/v2',
                          tags=['Новая версия API'])


UNIT_TIME_CHOICES = {
    'SECOND': IntervalSchedule.SECONDS,
    'MINUTE': IntervalSchedule.MINUTES,
    'HOUR': IntervalSchedule.HOURS,
    'DAY': IntervalSchedule.DAYS,
    }


def get_actual_datetime():
    return datetime.now() + timedelta(hours=9)


def get_timedelta():
    time_live_obj = PartnerTimeUpdate.objects\
                                        .get(name='Управление временем жизни направлений')
    amount = time_live_obj.amount
    unit_time = time_live_obj.unit_time

    match unit_time:
        case 'SECOND':
            time_delta = timedelta(seconds=amount)
        case 'MINUTE':
            time_delta = timedelta(minutes=amount)
        case 'HOUR':
            time_delta = timedelta(hours=amount)
        case 'DAY':
            time_delta = timedelta(days=amount)
    
    return time_delta



def annotate_string_field(exchange_marker):
    return Value(exchange_marker,
                    output_field=CharField())


def annotate_number_field(user_id: int):
    return Value(user_id,
                    output_field=IntegerField())


def get_valid_active_direction_str(direction):
    _timedelta = direction.time_update - (timezone.now() - timedelta(days=3))
    total_seconds = int(_timedelta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    formatted_time = f"{hours:02d} часов {minutes:02d} минут]"
    return f'{direction} (активно✅, отключится через {formatted_time}🕚)'


def try_generate_icon_url(obj) -> str | None:
    '''
    Генерирует путь до иконки переданного объекта.
    '''
    
    icon_url = None

    if obj.icon_url.name:
        icon_url = settings.PROTOCOL + settings.SITE_DOMAIN\
                                            + obj.icon_url.url
    if not icon_url:
        icon_url = settings.PROTOCOL + settings.SITE_DOMAIN\
                                            + '/media/icons/valute/BTC.svg'

    return icon_url


def round_in_out_count_values(direction: cash_models.NewDirection | no_cash_models.NewDirection,
                              in_count: float,
                              out_count: float):

    '''
    Округляет значения "min_amount" и "max_amount"
    '''

    try:
        valute_from = direction.valute_from
        type_valute_from = direction.valute_from.type_valute

        valute_to = direction.valute_to
        type_valute_to = direction.valute_to.type_valute
        
        valute_type_set = set((type_valute_from,type_valute_to))
        check_valutes = valute_type_set.intersection(set(('Наличные',
                                                         'Банкинг',
                                                         'Денежные переводы',
                                                         'ATM QR')))

        tether_set = set(('USDTTRC20', 'USDTERC20', 'USDTBEP20', 'USDCERC20', 'USDCTRC20'))
        
        if check_valutes:
            if set((valute_from.code_name,
                    valute_to.code_name)).intersection(tether_set):
                # 3 знака
                # print('here')
                _sign_number = 3

                in_count = round(in_count, _sign_number)
                out_count = round(out_count, _sign_number)
                pass
            # else:
            # поменял по просьбе Андрея модера
            elif len(check_valutes) == 2:
                # 1 знак
                _sign_number = 3
                
                in_count = round(in_count, _sign_number)
                out_count = round(out_count, _sign_number)
            else:
                # 1 знак
                # print('here 2')
                _sign_number = 1

                in_count = round(in_count, _sign_number)
                out_count = round(out_count, _sign_number)
        elif type_valute_from == 'Криптовалюта' and type_valute_to == 'Криптовалюта':
            # 5 знаков
            _sign_number = 5

            in_count = round(in_count, _sign_number)
            out_count = round(out_count, _sign_number)
        else:
            _sign_number = DEFAUT_ROUND

            in_count = round(in_count, _sign_number)
            out_count = round(out_count, _sign_number)
        
        return (
            in_count,
            out_count,
        )

    except Exception as ex:
        print(ex)
        pass


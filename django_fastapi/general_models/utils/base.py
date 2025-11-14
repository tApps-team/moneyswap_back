from datetime import datetime, timedelta

from django_celery_beat.models import IntervalSchedule

from django.db.models import CharField, Value, IntegerField
from django.conf import settings
from django.utils import timezone

from fastapi import APIRouter

from general_models.models import PartnerTimeUpdate


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

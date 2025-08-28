from datetime import datetime

from general_models.utils.base import get_actual_datetime

from cash.models import City

from partners.models import Direction


def make_city_active(obj: City):
    if not obj.is_parse:
        obj.is_parse = True
        obj.save()


def update_field_time_update(obj: Direction, update_fields: set):
     obj.time_update = datetime.now()
     update_fields.add('time_update')
     
     if not obj.is_active and 'is_active' not in update_fields:
          obj.is_active = True
          update_fields.add('is_active')


def get_saved_course(direction: Direction):
     return f'{direction.in_count} {direction.direction.valute_from} -> {direction.out_count} {direction.direction.valute_to}'
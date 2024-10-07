from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group, Permission, User

from general_models.utils.groups import create_group

from partners.models import (Exchange,
                             Direction,
                             Review,
                             Comment,
                             PartnerCity,
                             CustomUser)


# python manage.py create_moderator_group в docker-compose файле
# Команда для создания группы "Партнёры" с ограниченными правами доступа


class Command(BaseCommand):
    print('Creating Moder Group')

    def handle(self, *args, **kwargs):
        try:
            create_group(group_name='Модераторы',
                         models=(Exchange, Direction, Review, Comment, PartnerCity, CustomUser, User))

        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')
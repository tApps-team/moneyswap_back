from django.core.management.base import BaseCommand, CommandError

from django_celery_beat.models import PeriodicTask, IntervalSchedule

from django.db.utils import IntegrityError

from general_models.utils.periodic_tasks import get_or_create_schedule

from general_models.models import NewBaseReview, NewBaseComment

import no_cash.models as no_cash_models
import cash.models as cash_models
import partners.models as partners_models


# python manage.py create_periodic_task_for_delete_reviews в docker-compose файле
# Команда для создания периодической задачи, которая проверяет и удаляет
# отклонённые отзывы и комментарии


class Command(BaseCommand):
    print('Create reviews in new db table...')

    def handle(self, *args, **kwargs):
        try:
            for review_model in (no_cash_models.Review,
                                 cash_models.Review,
                                 partners_models.Review):
                reviews = review_model.objects.select_related('exchange')\
                                                .all()
                for review in reviews:
                    data = {
                        'exchange_name': review.exchange.name,
                        'username': review.username,
                        'guest_id': review.guest_id,
                        'text': review.text,
                        'grade': review.grade,
                        'transaction_id': review.transaction_id,
                        'status': review.status,
                        'moderation': review.moderation,
                        'time_create': review.time_create,
                        'review_from': review.review_from,
                    }
                    try:
                        new_review = NewBaseReview.objects.create(**data)
                    except IntegrityError as ex:
                        new_review = NewBaseReview.objects.filter(exchange_name=review.exchange.name,
                                                                  username=review.username,
                                                                  time_create=review.time_create).first()
                        print(ex)
                        pass
                    for comment in review.comments.all():
                        comment_data = {
                            'review_id': new_review.pk,
                            'username': comment.username,
                            'guest_id': comment.guest_id,
                            'text': comment.text,
                            'grade': comment.grade,
                            'status': comment.status,
                            'moderation': comment.moderation,
                            'time_create': comment.time_create,
                            'review_from': comment.review_from,
                        }
                        try:
                            NewBaseComment.objects.create(**comment_data)
                        except IntegrityError as ex:
                            print('COMMENT ERROR', ex)
                            pass
                    
            pass
        except Exception as ex:
            print(ex)
            raise CommandError('Initalization failed.')
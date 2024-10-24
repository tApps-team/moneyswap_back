from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User

from general_models.models import (BaseExchange,
                                   BaseReview,
                                   BaseComment,
                                   Guest,
                                   BaseAdminComment,
                                   BaseExchangeLinkCount)

from cash.models import Direction as CashDirection, City

from .utils.models import get_limit_direction, is_positive_validator


class Exchange(BaseExchange):
    
    class Meta:
        verbose_name = 'Обменник'
        verbose_name_plural = 'Обменники'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['en_name']),
        ]


class CustomUser(models.Model):
    limit_user = Q(is_superuser=False)

    user = models.OneToOneField(User,
                                verbose_name='Пользователь',
                                on_delete=models.CASCADE,
                                limit_choices_to=limit_user,
                                related_name='moderator_account')
    exchange = models.OneToOneField(Exchange,
                                    verbose_name='Партнёрский обменник',
                                    unique=True,
                                    blank=True,
                                    null=True,
                                    default=None,
                                    on_delete=models.SET_DEFAULT,
                                    related_name='account')
    refresh_token = models.CharField('Рефреш токен',
                                     max_length=255,
                                     null=True,
                                     default=None)
    
    class Meta:
        verbose_name = 'Администратор обменника'
        verbose_name_plural = 'Администраторы обменников'

    def __str__(self):
        return f'Пользователь: {self.user}, Обменник: {self.exchange}'


class WorkingDay(models.Model):
    name = models.CharField('Название',
                            max_length=30)
    code_name = models.CharField('Сокращение',
                                 max_length=10,
                                 null=True,
                                 default=None)
    
    class Meta:
        verbose_name = 'Рабочий день'
        verbose_name_plural = 'Рабочие дни'
        indexes = [
            models.Index(fields=['code_name']),
        ]

    def __str__(self):
        return self.name


class PartnerCity(models.Model):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.CASCADE,
                                 related_name='partner_cities')
    city = models.ForeignKey(City,
                             on_delete=models.CASCADE,
                             verbose_name='Город',
                             related_name='partner_cities')
    has_delivery = models.BooleanField('Есть ли доставка?', default=False)
    has_office = models.BooleanField('Есть ли офис?', default=False)
    working_days = models.ManyToManyField(WorkingDay,
                                          related_name='working_days_cities',
                                          verbose_name='Рабочие дни')
    time_from = models.CharField('Работаем с ',
                                 max_length=50,
                                 null=True,
                                 default=None) 
    time_to = models.CharField('Работаем до ',
                               max_length=50,
                               null=True,
                               default=None)
    weekend_time_from = models.CharField('Работаем с (выходные)',
                                         max_length=50,
                                         null=True,
                                         default=None) 
    weekend_time_to = models.CharField('Работаем до (выходные)',
                                       max_length=50,
                                       null=True,
                                       default=None)
    time_update = models.DateTimeField('Время последнего обновления',
                                       null=True,
                                       default=None)
    
    class Meta:
        #
        unique_together = (('exchange', 'city'),)
        #
        verbose_name = 'Партнёрский город'
        verbose_name_plural = 'Партнёрские города'
        ordering = ('exchange', 'city')

    def __str__(self):
        return f'{self.city}'


class Direction(models.Model):
    limit_direction = get_limit_direction()

    city = models.ForeignKey(PartnerCity,
                             on_delete=models.CASCADE,
                             verbose_name='Город',
                             related_name='partner_directions')
    direction = models.ForeignKey(CashDirection,
                                  verbose_name='Направление',
                                  on_delete=models.CASCADE,
                                  limit_choices_to=limit_direction,
                                  related_name='partner_directions')
    min_amount = models.FloatField('Минимальное количество',
                                   blank=True,
                                   null=True,
                                   default=None)
    max_amount = models.FloatField('Максимальное количество',
                                   blank=True,
                                   null=True,
                                   default=None)

    # percent = models.FloatField('Процент',
    #                             default=0,
    #                             validators=[is_positive_validator])
    # fix_amount = models.FloatField('Фиксированная ставка',
    #                                default=0,
    #                                validators=[is_positive_validator])

    in_count = models.DecimalField('Сколько отдаём',
                                   max_digits=20,
                                   decimal_places=2,
                                   null=True,
                                   default=None)
    out_count = models.DecimalField('Сколько получаем',
                                    max_digits=20,
                                    decimal_places=2,
                                    null=True,
                                    default=None)
    time_update = models.DateTimeField('Последнее обновление',
                                       auto_now_add=True,
                                       help_text='Время указано по московскому часовому поясу. При не обновлении процентов или фикс. ставки в течении 3 дней, направление становится неактивным.')
    is_active = models.BooleanField('Активно?', default=True)

    class Meta:
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'
        unique_together = (('city', 'direction'), )
        ordering = ('city__exchange', 'city', 'direction')

    def __str__(self):
        return f'{self.city.exchange} {self.city} - {self.direction}'


class Review(BaseReview):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.CASCADE,
                                 verbose_name='Наличный обменник',
                                 related_name='reviews')
    guest = models.ForeignKey(Guest,
                              blank=True,
                              null=True,
                              default=None,
                              verbose_name='Гостевой пользователь',
                              related_name='partner_reviews',
                              on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('-time_create', 'status', 'exchange')

    def __str__(self):
        return 'Партнёрский ' + super().__str__()


class Comment(BaseComment):
    review = models.ForeignKey(Review,
                               on_delete=models.CASCADE,
                               verbose_name='Отзыв',
                               related_name='comments')
    guest = models.ForeignKey(Guest,
                              blank=True,
                              null=True,
                              default=None,
                              verbose_name='Гостевой пользователь',
                              related_name='partner_comments',
                              on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('-time_create', 'status', 'review')

    def __str__(self):
        return 'Партнёрский ' + super().__str__()
    

class AdminComment(BaseAdminComment):
    review = models.ForeignKey(Review,
                               on_delete=models.CASCADE,
                               verbose_name='Отзыв',
                               related_name='admin_comments')

    class Meta:
        # unique_together = (('review','username','time_create'), )
        verbose_name = 'Комментарий администрации'
        verbose_name_plural = 'Комментарии администрации'
        ordering = ('-time_create', 'review')

    def __str__(self):
        return 'Партнёрский админский ' + super().__str__()
    

class ExchangeLinkCount(BaseExchangeLinkCount):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.CASCADE,
                                 verbose_name='Обменник',
                                 related_name='exchange_counts')
    user = models.ForeignKey(Guest,
                             on_delete=models.CASCADE,
                             verbose_name='Гостевой пользователь',
                             related_name='partner_exchange_counts')
    exchange_direction = models.ForeignKey(Direction,
                                           on_delete=models.CASCADE,
                                           verbose_name='Готовое направление',
                                           related_name='exchange_counts',
                                           null=True,
                                           default=None)
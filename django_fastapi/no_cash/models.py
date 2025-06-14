from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

from general_models.models import (Valute,
                                   ParseExchange,
                                   BaseDirection,
                                   BaseExchangeDirection,
                                   BaseReview,
                                   BaseComment,
                                   Guest,
                                   BaseAdminComment,
                                   BaseExchangeLinkCount)


#Модель обменника 
class Exchange(ParseExchange):
    direction_black_list = models.ManyToManyField('Direction', verbose_name='Чёрный список')


#Модель отзыва
class Review(BaseReview):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.CASCADE,
                                 verbose_name='Безналичный обменник',
                                 related_name='reviews')
    guest = models.ForeignKey(Guest,
                              blank=True,
                              null=True,
                              default=None,
                              verbose_name='Гостевой пользователь',
                              related_name='no_cash_reviews',
                              on_delete=models.CASCADE)
    
    class Meta:
        # unique_together = (('exchange','username','time_create'), )
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('-time_create', 'status', 'exchange')

    def __str__(self):
        return 'Безналичный' + super().__str__()


#Модель комментария
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
                              related_name='no_cash_comments',
                              on_delete=models.CASCADE)
    
    class Meta:
        unique_together = (('review','username','time_create'), )
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ('-time_create', 'status', 'review')
    
    def __str__(self):
        return 'Безналичный' + super().__str__()
    

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
        return 'Безналичный' + super().__str__()


#Модель направления
class Direction(BaseDirection):
    valute_from = models.ForeignKey(Valute,
                                    to_field='code_name',
                                    on_delete=models.CASCADE,
                                    verbose_name='Отдаём',
                                    limit_choices_to=~Q(type_valute='Наличные'),
                                    related_name='no_cash_valutes_from')
    valute_to = models.ForeignKey(Valute,
                                  to_field='code_name',
                                  on_delete=models.CASCADE,
                                  verbose_name='Получаем',
                                  limit_choices_to=~Q(type_valute='Наличные'),
                                  related_name='no_cash_valutes_to')
    
    def clean(self) -> None:
        super().clean_fields()
        
        if self.valute_from == self.valute_to:
            raise ValidationError('Валюты "Отдаём" и "Получаем" должны быть разные')


#Модель попуярного направления
class PopularDirection(models.Model):
    name = models.CharField('Название',
                            max_length=255)
    directions = models.ManyToManyField(Direction,
                                        verbose_name='Популярные направления',
                                        blank=True)
    
    class Meta:
        verbose_name = 'Популярное направление'
        verbose_name_plural = 'Популярные направления'

    def __str__(self):
        return self.name


#Модель готового направления
class ExchangeDirection(BaseExchangeDirection):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.CASCADE,
                                 verbose_name='Обменник',
                                 related_name='directions')
    direction = models.ForeignKey(Direction,
                                  verbose_name='Направление для обмена',
                                  on_delete=models.CASCADE,
                                  related_name='exchange_directions')
    
    class Meta:
        # unique_together = (("exchange", "valute_from", "valute_to"), )
        unique_together = (("exchange", "direction"), )
        verbose_name = 'Готовое направление'
        verbose_name_plural = 'Готовые направления'
        ordering = ['-is_active',
                    'exchange',
                    'direction__valute_from',
                    'direction__valute_to']
        indexes = [
            models.Index(fields=['is_active', 'exchange']),
        ]
        # indexes = [
        #     models.Index(fields=['direction__valute_from', 'direction__valute_to'])
        # ]

    def __str__(self):
        # return f'{self.exchange}:  {self.valute_from} -> {self.valute_to}'
        return f'{self.exchange.name}:  {self.direction}'
    

class ExchangeLinkCount(BaseExchangeLinkCount):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.CASCADE,
                                 verbose_name='Обменник',
                                 related_name='exchange_counts')
    user = models.ForeignKey(Guest,
                             on_delete=models.CASCADE,
                             verbose_name='Гостевой пользователь',
                             related_name='no_cash_exchange_counts')
    exchange_direction = models.ForeignKey(ExchangeDirection,
                                           on_delete=models.CASCADE,
                                           verbose_name='Готовое направление',
                                           related_name='no_cash_exchange_counts',
                                           null=True,
                                           default=None)
    
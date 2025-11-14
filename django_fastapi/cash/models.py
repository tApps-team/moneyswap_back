from django.db import models
from django.core.exceptions import ValidationError

from general_models.models import (BaseExchangeDirection,
                                   BaseExchangeLinkCount,
                                   NewBaseExchangeLinkCount,
                                   BaseDirection,
                                   BaseNewDirection,
                                   ParseExchange,
                                   Valute,
                                   Guest,
                                   NewValute,
                                   Exchanger,
                                #    BaseReview,
                                #    BaseComment,
                                #    BaseAdminComment,
                                   )


#Модель страны
class Country(models.Model):
    name = models.CharField('Название страны(ru)', max_length=100,
                            unique=True)
    en_name = models.CharField('Название страны(en)', max_length=100,
                               unique=True)
    icon_url = models.FileField('Флаг страны',
                                upload_to='icons/country/',
                                blank=True,
                                null=True)
    is_popular = models.BooleanField('Популярная',
                                     default=False)

    class Meta:
        verbose_name = 'Страна'
        verbose_name_plural = 'Страны'
        ordering = ('name', )
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['en_name'])
        ]

    def __str__(self):
        return self.name


#Модель города
class City(models.Model):
    name = models.CharField('Название города(ru)',
                            max_length=100,
                            unique=True)
    en_name = models.CharField('Название города(en)',
                               max_length=100,
                               unique=True)
    code_name = models.CharField('Кодовое имя',
                                 max_length=10,
                                 unique=True)
    country = models.ForeignKey(Country,
                                on_delete=models.CASCADE,
                                verbose_name='Страна',
                                related_name='cities')
    is_parse = models.BooleanField('Статус парсинга', default=False)
    popular_count = models.BigIntegerField('Счетчик популярности',
                                           default=0)
    # has_partner_cities: bool

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['name']

        indexes = [
            models.Index(fields=['code_name', ])
        ]

    def __str__(self):
        return self.name


#Модель обменника    
class Exchange(ParseExchange):
    pass
    # direction_black_list = models.ManyToManyField('BlackListElement',
    #                                               verbose_name='Чёрный список')
    

#Модель отзыва
# class Review(BaseReview):
#     exchange = models.ForeignKey(Exchange,
#                                  on_delete=models.CASCADE,
#                                  verbose_name='Наличный обменник',
#                                  related_name='reviews')
#     guest = models.ForeignKey(Guest,
#                               blank=True,
#                               null=True,
#                               default=None,
#                               verbose_name='Гостевой пользователь',
#                               related_name='cash_reviews',
#                               on_delete=models.CASCADE)
    
#     class Meta:
#         # unique_together = (('exchange','username','time_create'), )
#         verbose_name = 'Отзыв'
#         verbose_name_plural = 'Отзывы'
#         ordering = ('-time_create', 'status', 'exchange')

#     def __str__(self):
#         return 'Наличный ' + super().__str__()


#Модель комментария
# class Comment(BaseComment):
#     review = models.ForeignKey(Review,
#                                on_delete=models.CASCADE,
#                                verbose_name='Отзыв',
#                                related_name='comments')
#     guest = models.ForeignKey(Guest,
#                               blank=True,
#                               null=True,
#                               default=None,
#                               verbose_name='Гостевой пользователь',
#                               related_name='cash_comments',
#                               on_delete=models.CASCADE)
    
#     class Meta:
#         # unique_together = (('review','username','time_create'), )
#         verbose_name = 'Комментарий'
#         verbose_name_plural = 'Комментарии'
#         ordering = ('-time_create', 'status', 'review')

#     def __str__(self):
#         return 'Наличный ' + super().__str__()


# class AdminComment(BaseAdminComment):
#     review = models.ForeignKey(Review,
#                                on_delete=models.CASCADE,
#                                verbose_name='Отзыв',
#                                related_name='admin_comments')

#     class Meta:
#         # unique_together = (('review','username','time_create'), )
#         verbose_name = 'Комментарий администрации'
#         verbose_name_plural = 'Комментарии администрации'
#         ordering = ('-time_create', 'review')

#     def __str__(self):
#         return 'Наличный ' + super().__str__()


#Модель направления
class Direction(BaseDirection):
    valute_from = models.ForeignKey(Valute,
                                    to_field='code_name',
                                    on_delete=models.CASCADE,
                                    verbose_name='Отдаём',
                                    related_name='cash_valutes_from')
    valute_to = models.ForeignKey(Valute,
                                  to_field='code_name',
                                  on_delete=models.CASCADE,
                                  verbose_name='Получаем',
                                  related_name='cash_valutes_to')
    
    display_name = models.CharField('Отображение в админ панели',
                                    max_length=40,
                                    blank=True,
                                    null=True,
                                    default=None)
    previous_course = models.FloatField('Предыдующий курс обмена',
                                        blank=True,
                                        null=True,
                                        default=None)
    # actual_course = models.FloatField('Актуальный курс обмена',
    #                                   blank=True,
    #                                   null=True,
    #                                   default=None)
    
    def __str__(self):
        return self.display_name
    
    
    def clean(self) -> None:
        super().clean_fields()
        
        # if self.valute_from.type_valute == self.valute_to.type_valute:
        #     raise ValidationError('Значения "Отдаём" и "Получаем" должны иметь разные типы валют')
        
        if (not 'Наличные' in (self.valute_from.type_valute, self.valute_to.type_valute)) and \
            (not 'ATM QR' in self.valute_to.type_valute):
            raise ValidationError('Одно из значений "Отдаём" и "Получаем" должно иметь наличный тип валюты, другое - безналичный')


# new Direction model
class NewDirection(BaseNewDirection):
    valute_from = models.ForeignKey(NewValute,
                                    to_field='code_name',
                                    on_delete=models.SET_NULL,
                                    blank=True,
                                    null=True,
                                    default=None,
                                    verbose_name='Отдаём',
                                    related_name='cash_valutes_from')
    valute_to = models.ForeignKey(NewValute,
                                  to_field='code_name',
                                  on_delete=models.SET_NULL,
                                  blank=True,
                                  null=True,
                                  default=None,
                                  verbose_name='Получаем',
                                  related_name='cash_valutes_to')
    
    class Meta:
        unique_together = (("valute_from", "valute_to"), )
        verbose_name = 'Направление для обмена (новое)'
        verbose_name_plural = 'Направления для обмена (новые)'
        ordering = ['valute_from', 'valute_to']
        indexes = [
            models.Index(fields=['valute_from', 'valute_to'])
        ]
    
    def clean(self) -> None:
        super().clean_fields()
        
        if (not 'Наличные' in (self.valute_from.type_valute, self.valute_to.type_valute)) and \
            (not 'ATM QR' in self.valute_to.type_valute):
            raise ValidationError('Одно из значений "Отдаём" и "Получаем" должно иметь наличный тип валюты, другое - безналичный')


#Модель готового направления
class ExchangeDirection(BaseExchangeDirection):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.SET_NULL,
                                 verbose_name='Обменник',
                                 related_name='directions',
                                 blank=True,
                                 null=True)
    direction = models.ForeignKey(Direction,
                                  verbose_name='Направление для обмена',
                                  on_delete=models.SET_NULL,
                                  blank=True,
                                  null=True,
                                  related_name='exchange_directions')
    # city = models.CharField('Город', max_length=100)
    city = models.ForeignKey(City,
                             verbose_name='Город',
                             on_delete=models.SET_NULL,
                             blank=True,
                             null=True,
                             related_name='cash_directions')
    fromfee = models.FloatField('Процент', blank=True, null=True)
    params = models.CharField('Параметры', max_length=100, blank=True, null=True)

    class Meta:
        # unique_together = (("exchange", "city", "valute_from", "valute_to"), )
        unique_together = (("exchange", "city", "direction"), )
        verbose_name = 'Готовое направление (старое)'
        verbose_name_plural = 'Готовые направления (старые)'
        ordering = ['-is_active',
                    'exchange',
                    'city',
                    'direction__valute_from',
                    'direction__valute_to']
        # indexes = [
        #     models.Index(fields=['city', 'valute_from', 'valute_to'])
        # ]

    def __str__(self):
        # return f'{self.city}: {self.valute_from} -> {self.valute_to}'
        return f'{self.exchange} {self.city}: {self.direction}'


# new ExchangeDirection model
class NewExchangeDirection(BaseExchangeDirection):
    exchange = models.ForeignKey(Exchanger,
                                 on_delete=models.SET_NULL,
                                 verbose_name='Обменник',
                                 related_name='cash_directions',
                                 blank=True,
                                 null=True)
    direction = models.ForeignKey(NewDirection,
                                  verbose_name='Направление для обмена',
                                  on_delete=models.SET_NULL,
                                  blank=True,
                                  null=True,
                                  related_name='exchange_directions')
    # city = models.CharField('Город', max_length=100)
    city = models.ForeignKey(City,
                             verbose_name='Город',
                             on_delete=models.SET_NULL,
                             blank=True,
                             null=True,
                             related_name='new_cash_directions')
    country_direction = models.ForeignKey('partners.NewCountryDirection',
                                          verbose_name='Партерское направление страны',
                                          related_name='directions',
                                          on_delete=models.CASCADE,
                                          blank=True,
                                          null=True,
                                          default=None)
    fromfee = models.FloatField('Процент', blank=True, null=True)
    params = models.CharField('Параметры', max_length=100, blank=True, null=True)

    class Meta:
        # unique_together = (("exchange", "city", "valute_from", "valute_to"), )
        unique_together = (("exchange", "city", "direction"), )
        verbose_name = 'Готовое направление (новое)'
        verbose_name_plural = 'Готовые направления (новые)'
        ordering = ['-is_active',
                    'exchange',
                    'city',
                    'direction__valute_from',
                    'direction__valute_to']
        # indexes = [
        #     models.Index(fields=['city', 'valute_from', 'valute_to'])
        # ]

    def __str__(self):
        # return f'{self.city}: {self.valute_from} -> {self.valute_to}'
        return f'{self.exchange} {self.city}: {self.direction}'


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
    

class ExchangeLinkCount(BaseExchangeLinkCount):
    exchange = models.ForeignKey(Exchange,
                                 on_delete=models.SET_NULL,
                                 blank=True,
                                 null=True,
                                 verbose_name='Обменник',
                                 related_name='exchange_counts')
    user = models.ForeignKey(Guest,
                             on_delete=models.CASCADE,
                             verbose_name='Гостевой пользователь',
                             related_name='cash_exchange_counts')
    exchange_direction = models.ForeignKey(ExchangeDirection,
                                           on_delete=models.SET_NULL,
                                           blank=True,
                                           verbose_name='Готовое направление',
                                           related_name='cash_exchange_counts',
                                           null=True,
                                           default=None)
    

# new ExchangeLinkCount model
class NewExchangeLinkCount(NewBaseExchangeLinkCount):
    exchange = models.ForeignKey(Exchanger,
                                 on_delete=models.SET_NULL,
                                 blank=True,
                                 null=True,
                                 verbose_name='Обменник',
                                 related_name='cash_exchange_counts')
    user = models.ForeignKey(Guest,
                             on_delete=models.CASCADE,
                             verbose_name='Гостевой пользователь',
                             related_name='new_cash_exchange_counts')
    exchange_direction = models.ForeignKey(NewExchangeDirection,
                                           on_delete=models.SET_NULL,
                                           verbose_name='Готовое направление',
                                           related_name='exchange_direction_counts',
                                           blank=True,
                                           null=True,
                                           default=None)
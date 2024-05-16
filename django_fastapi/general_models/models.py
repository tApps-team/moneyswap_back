from typing import Iterable
from datetime import datetime

from django.db import models

from .utils.model_validators import is_positive_validate


en_type_valute_dict = {
    'Криптовалюта': 'Cryptocurrency',
    'Эл. деньги': 'Digital currencies',
    'Балансы криптобирж': 'Crypto exchange balances',
    'Банкинг': 'Online banking',
    'Денежные переводы': 'Money transfers',
    'Наличные': 'Cash',
}


#Модель валюты
class Valute(models.Model):
    type_valute_list = [
        ('Криптовалюта', 'Криптовалюта'),
        ('Эл. деньги', 'Эл. деньги'),
        ('Балансы криптобирж', 'Балансы криптобирж'),
        ('Банкинг', 'Банкинг'),
        ('Денежные переводы', 'Денежные переводы'),
        ('Наличные', 'Наличные'),
        ]
    name = models.CharField('Название валюты(ru)',
                            max_length=50,
                            primary_key=True)
    en_name = models.CharField('Название валюты(en)',
                               max_length=50,
                               unique=True,
                               null=True,
                               default=None)
    code_name = models.CharField('Кодовое сокращение',
                                 max_length=10,
                                 unique=True)
    type_valute = models.CharField('Тип валюты',
                                   max_length=30,
                                   choices=type_valute_list)
    icon_url = models.FileField('Иконка валюты',
                                upload_to='icons/valute/',
                                blank=True,
                                null=True)
    available_for_partners = models.BooleanField('Доступно для партнёров',
                                                 default=False)

    class Meta:
        verbose_name = 'Валюта'
        verbose_name_plural = 'Валюты'
        ordering = ['code_name']
        indexes = [
            models.Index(fields=['code_name', ])
        ]

    def __str__(self):
        return self.code_name


# Модель для времени проверки партнёрских
# готовых направлений на активность
class PartnerTimeUpdate(models.Model):
    unit_time_choices = [
        ('SECOND', 'Секунды'),
        ('MINUTE', 'Минуты'),
        ('HOUR', 'Часы'),
        ('DAY', 'Дни'),
    ]
    name = models.CharField('Название',
                            max_length=100,
                            unique=True)
    amount = models.IntegerField('Количество')
    unit_time = models.CharField('Единица измерения',
                                 max_length=100,
                                 choices=unit_time_choices)
    
    class Meta:
        verbose_name = 'Управление временем партнёрских направлений'
        verbose_name_plural = 'Управление временем партнёрских направлений'

    def __str__(self):
        return self.name
    


class Guest(models.Model):
    username = models.CharField('Никнейм',
                                max_length=255,
                                blank=True,
                                null=True,
                                default=None)
    tg_id = models.BigIntegerField('Telegram id',
                                   primary_key=True)

    class Meta:
        verbose_name = 'Гостевой пользователь'
        verbose_name_plural = 'Гостевые пользователи'
        # indexes = [
        #     models.Index(fields=('tg_id', )),
        # ]

    def __str__(self):
        return f'{self.username} - {self.tg_id}'


#Абстрактная модель отзыва/комментария (для наследования)
class BaseReviewComment(models.Model):
    status_list = [
    ('Опубликован', 'Опубликован'),
    ('Модерация', 'Модерация'),
    ('Отклонён', 'Отклонён'),
    ]
    #
    # grade_list = [
    #     ('Положительный', '1'),
    #     ('Нейтральный', '0'),
    #     ('Отрицательный', '-1'),
    # ]
    #
    class GradeChoices(models.IntegerChoices):
        POS = 1, 'Положительный'
        NET = 0, 'Нейтральный'
        NEG = -1, 'Отрицальный'
    # grade_list = [
    #     ('1', 'Положительный'),
    #     ('0', 'Нейтральный'),
    #     ('-1', 'Отрицательный'),
    # ]
    username = models.CharField('Имя пользователя',
                                max_length=255,
                                blank=True,
                                null=True,
                                default=None)
    text = models.TextField('Текст сообщения')
    time_create = models.DateTimeField('Дата создания',
                                       blank=True,
                                       null=True,
                                       default=None,
                                       help_text='Если оставить поля пустыми, время установится автоматически по московскому часовому поясу')
    status = models.CharField('Статус модерации',
                                  max_length=20,
                                  choices=status_list,
                                  default='Модерация',
                                  help_text='При выборе статуса "Отклонён" попадает в очередь на удаление')
    moderation = models.BooleanField('Прошел модерацию?', default=False)
    # grade = models.IntegerField('Оценка',
    #                             choices=GradeChoices.choices,
    #                             default=GradeChoices.NET)

    class Meta:
        abstract = True


#Абстрактная модель отзыва (для наследования)
class BaseReview(BaseReviewComment):
    class Meta:
        abstract = True
    
    def __str__(self):
        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f' отзыв {self.pk}, Обменник: {self.exchange}, Пользователь: {self.username}, Время создания: {date}'


#Абстрактная модель комментария (для наследования)
class BaseComment(BaseReviewComment):
    class Meta:
        abstract = True

    def __str__(self):
        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f' комментарий {self.pk}, Отзыв №{self.review.pk}, Обменник: {self.review.exchange}, Пользователь: {self.username}, Время создания: {date}'


#Абстрактная модель обменника (для наследования)
class BaseExchange(models.Model):
    name = models.CharField('Название обменника(ru)',
                            max_length=20,
                            unique=True)
    en_name = models.CharField('Название обменника(en)',
                               max_length=20,
                               unique=True,
                               blank=True,
                               null=True,
                               default=None)
    partner_link = models.CharField('Партнёрская ссылка',
                                    max_length=50,
                                    blank=True,
                                    null=True,
                                    default=None)
    is_active = models.BooleanField('Статус обменника', default=True)
    #
    # is_vip = models.BooleanField('VIP',
    #                              default=False)
    #

    class Meta:
        abstract = True

    def __str__(self):
        return self.name
    

class ParseExchange(BaseExchange):
    xml_url = models.CharField('Ссылка на XML файл',
                               max_length=50)
    period_for_create = models.IntegerField('Частота добавления в секундах',
                                            blank=True,
                                            null=True,
                                            default=90,
                                            help_text='Значение - положительное целое число.При установлении в 0, останавливает задачу периодических добавлений',
                                            validators=[is_positive_validate])
    period_for_update = models.IntegerField('Частота обновлений в секундах',
                                            blank=True,
                                            null=True,
                                            default=60,
                                            help_text='Значение - положительное целое число.При установлении в 0, останавливает задачу периодических обновлений',
                                            validators=[is_positive_validate])
    period_for_parse_black_list = models.IntegerField('Частота парсинга чёрного списка в часах',
                                                      blank=True,
                                                      null=True,
                                                      default=24,
                                                      help_text='Рекомендуемое значение - 24 часа.\nЗначение - положительное целое число.При установлении в 0, останавливает задачу периодического парсинга чёрного списка',
                                                      validators=[is_positive_validate])
    
    class Meta:
        abstract = True
        verbose_name = 'Обменник'
        verbose_name_plural = 'Обменники'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['en_name']),
        ]

#Абстрактная модель направления (для наследования)
class BaseDirection(models.Model):
    popular_count = models.IntegerField('Счётчик популярности',
                                        default=0)
    
    class Meta:
        abstract = True
        unique_together = (("valute_from", "valute_to"), )
        verbose_name = 'Направление для обмена'
        verbose_name_plural = 'Направления для обмена'
        ordering = ['valute_from', 'valute_to']
        indexes = [
            models.Index(fields=['valute_from', 'valute_to'])
        ]
    
    #для более красивого вывода в чёрном списке
    def __str__(self):
        return self.valute_from.code_name + ' -> ' + self.valute_to.code_name + '\n\n'
    

#Абстрактная модель готового направления (для наследования)
class BaseExchangeDirection(models.Model):
    # valute_from = models.CharField('Отдаём', max_length=10)
    # valute_to = models.CharField('Получаем', max_length=10)
    in_count = models.DecimalField('Сколько отдаём',
                                   max_digits=20,
                                   decimal_places=2)
    out_count = models.DecimalField('Сколько получаем',
                                    max_digits=20,
                                    decimal_places=2)
    min_amount = models.CharField('Минимальное количество', max_length=50)
    max_amount = models.CharField('Максимальное количество', max_length=50)
    is_active = models.BooleanField('Активно?', default=True)

    class Meta:
        abstract = True
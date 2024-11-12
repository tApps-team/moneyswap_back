from typing import Iterable
from datetime import datetime

from django.db import models

# from partners.models import CustomUser

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
    

# Модель Гостевых Пользователей
class Guest(models.Model):
    username = models.CharField('Никнейм',
                                max_length=255,
                                blank=True,
                                null=True,
                                default=None)
    tg_id = models.BigIntegerField('Telegram id',
                                   primary_key=True)
    first_name = models.CharField('Имя пользователя',
                                  max_length=255,
                                  null=True,
                                  blank=True,
                                  default=None)
    last_name = models.CharField('Фамилия пользователя',
                                 max_length=255,
                                 blank=True,
                                 null=True,
                                 default=None)
    language_code = models.CharField('Язык интерфейса',
                                     max_length=255,
                                     blank=True,
                                     null=True,
                                     default=None)
    is_premium = models.BooleanField('Премиум',
                                     default=False)
    is_active = models.BooleanField('Активен',
                                    default=True)
    chat_link = models.CharField('Ссылка на чат',
                                 max_length=255,
                                 blank=True,
                                 null=True,
                                 default=None)
    utm_source = models.CharField('Ресурс, с которого пришёл пользователь',
                                  max_length=64,
                                  null=True,
                                  blank=True,
                                  default=None)

    class Meta:
        verbose_name = 'Гостевой пользователь'
        verbose_name_plural = 'Гостевые пользователи'
        # indexes = [
        #     models.Index(fields=('tg_id', )),
        # ]

    def __str__(self):
        return f'{self.username} - {self.tg_id}'
    

# Модель рассылок в телеграм боте
class MassSendMessage(models.Model):
    name = models.CharField('Название',
                            max_length=255)
    content = models.TextField('Контент')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Массовая рассылка'
        verbose_name_plural = 'Массовые рассылки'

# Модель изображений связанных с рассылкой 
class MassSendImage(models.Model):
    image = models.ImageField('Изображение',
                              upload_to='mass_send/images/')
    message = models.ForeignKey(MassSendMessage,
                                 on_delete=models.CASCADE,
                                 verbose_name='Cообщение',
                                 related_name='images')
    file_id = models.CharField('ID файла',
                               max_length=255,
                               null=True,
                               blank=True,
                               default=None)
    
    def __str__(self):
        return f'Изображение {self.id}'
    
    class Meta:
        verbose_name = 'Изображение для расслыки'
        verbose_name_plural = 'Изображения для расслыки'

# Модель видео связанных с рассылкой 
class MassSendVideo(models.Model):
    video = models.FileField('Видео',
                             upload_to='mass_send/videos/')
    message = models.ForeignKey(MassSendMessage,
                                 on_delete=models.CASCADE,
                                 verbose_name='Cообщение',
                                 related_name='videos')
    file_id = models.CharField('ID файла',
                               max_length=255,
                               null=True,
                               blank=True,
                               default=None)

    def __str__(self):
        return f'Видео {self.id}'

    class Meta:
        verbose_name = 'Видео для расслыки'
        verbose_name_plural = 'Видео для расслыки'


# Модель файлов связанных с рассылкой 
class MassSendFile(models.Model):
    file = models.FileField('Файл',
                            upload_to='mass_send/files/')
    message = models.ForeignKey(MassSendMessage,
                                 on_delete=models.CASCADE,
                                 verbose_name='Cообщение',
                                 related_name='files')
    file_id = models.CharField('ID файла',
                               max_length=255,
                               null=True,
                               blank=True,
                               default=None)
    
    def __str__(self):
        return f'Файл {self.id}'

    class Meta:
        verbose_name = 'Файл для расслыки'
        verbose_name_plural = 'Файлы для расслыки'


# Модель Заявок(Swify/Sepa) гостевых пользователей
class CustomOrder(models.Model):
    status_choice = (
        ('Модерация', 'Модерация'),
        ('В обработке', 'В обработке'),
        ('Завершен', 'Завершен'),
    )
    request_type = models.CharField('Тип заявки',
                                    max_length=255)
    country = models.CharField('Страна',
                               max_length=255)
    amount = models.CharField('Сумма',
                              max_length=255)
    comment = models.TextField('Комментарий')

    guest = models.ForeignKey(Guest,
                              on_delete=models.CASCADE,
                              related_name='custom_orders')
    time_create = models.DateTimeField('Время создания',
                                       auto_now_add=True)
    status = models.CharField('Статус модерации',
                              max_length=255,
                              choices=status_choice,
                              default='Модерация')
    moderation = models.BooleanField('Прошел модерацию',
                                     default=False)

    class Meta:
        verbose_name = 'Завка пользователя'
        verbose_name_plural = 'Заявки пользователей'
        ordering = ('-time_create', )

    def __str__(self):
        return f'Заявка №{self.pk} -> {self.guest}'
    

class FeedbackForm(models.Model):
    reasons_choice = [
        ('Ошибка', 'Ошибка'),
        ('Проблемма с обменником', 'Проблемма с обменником'),
        ('Сотрудничество', 'Сотрудничество'),
        ('Другое', 'Другое'),
    ]
    username = models.CharField('Имя пользователя',
                                max_length=255)
    email = models.CharField('Email',
                            max_length=255)
    reasons = models.CharField('Причина',
                               max_length=255,
                               choices=reasons_choice)
    description = models.TextField('Описание')
    time_create = models.DateTimeField('Время создания',
                                    #    auto_created=True,
                                       auto_now_add=True)
    
    def __str__(self):
        return f'{self.username} {self.reasons} {self.time_create}'
    
    class Meta:
        verbose_name = 'Форма обратной связи'
        verbose_name_plural = 'Формы обратной связи'
    

#Абстрактная модель отзыва/комментария (для наследования)
class BaseReviewComment(models.Model):
    status_list = [
    ('Опубликован', 'Опубликован'),
    ('Модерация', 'Модерация'),
    ('Отклонён', 'Отклонён'),
    ]
    #
    grade_list = [
        ('1', 'Положительный'),
        ('0', 'Нейтральный'),
        ('-1', 'Отрицательный'),
    ]
    #
    # class GradeChoices(models.IntegerChoices):
    #     POS = 1, 'Положительный'
    #     NET = 0, 'Нейтральный'
    #     NEG = -1, 'Отрицальный'
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
    grade = models.CharField('Оценка',
                             choices=grade_list,
                             default='0')


    class Meta:
        abstract = True


#Абстрактная модель отзыва (для наследования)
class BaseReview(BaseReviewComment):
    transaction_id = models.CharField('Номер транзакции',
                                      blank=True,
                                      null=True,
                                      default=None)
    
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


#
class BaseAdminComment(models.Model):
    text = models.TextField('Текст сообщения')
    time_create = models.DateTimeField('Дата создания',
                                       blank=True,
                                       null=True,
                                       default=None,
                                       help_text='Если оставить поля пустыми, время установится автоматически по московскому часовому поясу')

    class Meta:
        abstract = True

    def __str__(self):
        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f' комментарий администрации {self.pk}, Отзыв №{self.review.pk}, Обменник: {self.review.exchange}, Время создания: {date}'
#


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
                                    max_length=255,
                                    blank=True,
                                    null=True,
                                    default=None)
    is_active = models.BooleanField('Статус обменника', default=True)
    #
    is_vip = models.BooleanField('VIP',
                                 default=False)
    #
    course_count = models.CharField('Количество курсов для обмена',
                                       max_length=255,
                                       blank=True,
                                       null=True,
                                       default=None)
    reserve_amount = models.CharField('Сумма резерва',
                                      max_length=255,
                                      blank=True,
                                      null=True,
                                      default=None)
    age = models.CharField('Возраст',
                           max_length=255,
                           blank=True,
                           null=True,
                           default=None)
    country = models.CharField('Страна',
                               max_length=255,
                               blank=True,
                               null=True,
                               default=None)
    icon_url = models.FileField('Иконка обменника',
                                upload_to='icons/exchange/',
                                blank=True,
                                null=True,
                                default='icons/country/russia.svg')
    

    class Meta:
        abstract = True

    def __str__(self):
        return self.name
    

class ParseExchange(BaseExchange):
    xml_url = models.CharField('Ссылка на XML файл',
                               max_length=255)
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
    actual_course = models.FloatField('Актуальный курс обмена',
                                      blank=True,
                                      null=True,
                                      default=None)
    
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
                                   decimal_places=5)
    out_count = models.DecimalField('Сколько получаем',
                                    max_digits=20,
                                    decimal_places=5)
    min_amount = models.CharField('Минимальное количество', max_length=50)
    max_amount = models.CharField('Максимальное количество', max_length=50)
    is_active = models.BooleanField('Активно?', default=True)

    class Meta:
        abstract = True



class BaseExchangeLinkCount(models.Model):
    count = models.PositiveBigIntegerField('Счетчик просмотров',
                                           default=0)
    exchange_marker = models.CharField('Маркер',
                                       max_length=255)
    # user = models.ForeignKey(Guest,
    #                          on_delete=models.CASCADE,
    #                          verbose_name='Гостевой пользователь')
    
    class Meta:
        verbose_name = 'Счётчик перехода по ссылке'
        verbose_name_plural = 'Счётчики перехода по ссылкам'
        unique_together = [('exchange', 'user', 'exchange_direction', 'exchange_marker')]
        abstract = True

    def __str__(self):
        return f'{self.user} {self.exchange} - {self.count}'
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
    'ATM QR': 'ATM QR',
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
        ('ATM QR', 'ATM QR'),
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
    is_popular = models.BooleanField('Популярная',
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
    select_language = models.CharField('Выбранный язык',
                                       max_length=255,
                                       choices=(('ru', 'ru'),
                                                ('en', 'en')),
                                        default='ru')
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
    time_create = models.DateTimeField('Время добавления',
                                       default=None,
                                       blank=True,
                                       null=True)

    class Meta:
        verbose_name = 'Гостевой пользователь'
        verbose_name_plural = 'Гостевые пользователи'
        ordering = (
            'username',
        )
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
                               max_length=255,
                               blank=True,
                               null=True,
                               default=None)
    amount = models.CharField('Сумма',
                              max_length=255,
                              blank=True,
                              null=True,
                              default=None)
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

    review_from_list = [
        ('bestchange', 'bestchange'),
        ('moneyswap', 'moneyswap'),
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
    review_from = models.CharField('Откуда отзыв',
                                   max_length=50,
                                   choices=review_from_list,
                                   default='moneyswap')

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
        if self.time_create is None:
            self.time_create = datetime.now()
            
        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f' отзыв {self.pk}, Обменник: {self.exchange}, Пользователь: {self.username}, Время создания: {date}'


class NewBaseReview(BaseReviewComment):
    guest = models.ForeignKey(Guest,
                              blank=True,
                              null=True,
                              default=None,
                              verbose_name='Гостевой пользователь',
                              related_name='reviews',
                              on_delete=models.CASCADE)
    exchange_name = models.CharField('Название обменника',
                                     max_length=255)
    transaction_id = models.CharField('Номер транзакции',
                                      blank=True,
                                      null=True,
                                      default=None)
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = (('exchange_name','username','time_create', 'text'), )
    
    def __str__(self):
        if self.time_create is None:
            self.time_create = datetime.now()
            
        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f'Отзыв {self.pk}, Обменник: {self.exchange_name}, Пользователь: {self.username}, Время создания: {date}'


class NewBaseComment(BaseReviewComment):
    guest = models.ForeignKey(Guest,
                              blank=True,
                              null=True,
                              default=None,
                              verbose_name='Гостевой пользователь',
                              related_name='comments',
                              on_delete=models.CASCADE)
    review = models.ForeignKey(NewBaseReview,
                               on_delete=models.CASCADE,
                               verbose_name='Отзыв',
                               related_name='comments')
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        # unique_together = (('review','username','time_create'), )

    def __str__(self):
        if self.time_create is None:
            self.time_create = datetime.now()

        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f' комментарий {self.pk}, Отзыв №{self.review.pk}, Обменник: {self.review.exchange_name}, Пользователь: {self.username}, Время создания: {date}'


class NewBaseAdminComment(models.Model):
    review = models.ForeignKey(NewBaseReview,
                               on_delete=models.CASCADE,
                               verbose_name='Отзыв',
                               related_name='admin_comments')
    text = models.TextField('Текст сообщения')
    time_create = models.DateTimeField('Дата создания',
                                       blank=True,
                                       null=True,
                                       default=None,
                                       help_text='Если оставить поля пустыми, время установится автоматически по московскому часовому поясу')

    class Meta:
        verbose_name = 'Комментарий администрации'
        verbose_name_plural = 'Комментарии администрации'

    def __str__(self):
        if self.time_create is None:
            self.time_create = datetime.now()

        date = self.time_create.strftime("%d.%m.%Y, %H:%M:%S")
        return f' комментарий администрации {self.pk}, Отзыв №{self.review.pk}, Обменник: {self.review.exchange_name}, Время создания: {date}'


#Абстрактная модель комментария (для наследования)
class BaseComment(BaseReviewComment):
    class Meta:
        abstract = True

    def __str__(self):
        if self.time_create is None:
            self.time_create = datetime.now()

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
        if self.time_create is None:
            self.time_create = datetime.now()

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
    time_create = models.DateTimeField('Время добавления',
                                       blank=True,
                                       null=True,
                                       auto_now_add=True)
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
    high_aml = models.BooleanField('Высокий AML риск?', default=False)

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
    # def __str__(self):
    #     return f'{self.user}  - {self.count}'
    

class BaseDirectionRate(models.Model):
    in_count = models.DecimalField('Сколько отдаём',
                                   max_digits=20,
                                   decimal_places=5,
                                   null=True,
                                   default=None)
    out_count = models.DecimalField('Сколько получаем',
                                    max_digits=20,
                                    decimal_places=5,
                                    null=True,
                                    default=None)
    min_rate_limit = models.FloatField('Минимальный лимит')
    max_rate_limit = models.FloatField('Максимальный лимит',
                                   blank=True,
                                   null=True,
                                   default=None)
    rate_coefficient = models.FloatField('Коэффициент разницы курса от объема',
                                         null=True,
                                         default=None)

    class Meta:
        # verbose_name = ''
        # verbose_name_plural = 'Счётчики перехода по ссылкам'
        unique_together = [('exchange', 'exchange_direction', 'min_rate_limit')]
        abstract = True


class ExchangeAdminOrder(models.Model):
    # user = models.ForeignKey(Guest,
    #                          on_delete=models.CASCADE,
    #                          verbose_name='Пользователь')
    user_id = models.BigIntegerField('Tg id пользователя')
    exchange_name = models.CharField('Название обменника',
                                     max_length=255,
                                     help_text='Название должно совпадать с названием обменника из НАШЕЙ базы!')
    moderation = models.BooleanField('Модерация',
                                     default=False)
    time_create = models.DateTimeField('Время создания',
                                    #    auto_created=True,
                                       auto_now_add=True)
    
    class Meta:
        verbose_name = 'Заявка на подключение обменника к юзеру'
        verbose_name_plural = 'Заявки на подключения обменников к юзерам'

    def __str__(self):
        return f'{self.user_id} {self.exchange_name}'


class ExchangeAdmin(models.Model):
    user = models.ForeignKey(Guest,
                             on_delete=models.CASCADE,
                             verbose_name='Пользователь',
                             related_name='liked_exchanges')
    exchange_marker = models.CharField('Маркер обменника',
                                       max_length=255)
    exchange_name = models.CharField('Название обменника',
                                     max_length=255)
    exchange_id = models.IntegerField('Id обменника')
    
    class Meta:
        unique_together = [('user', 'exchange_marker', 'exchange_id')]
        verbose_name = 'Подключенный обменник к юзеру'
        verbose_name_plural = 'Подключенные обменники к юзерам'

    def __str__(self):
        return f'{self.user} {self.exchange_name} {self.exchange_marker}'    
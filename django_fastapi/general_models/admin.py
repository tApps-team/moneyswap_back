from datetime import datetime, timedelta, timezone
from typing import Any

from django.db.models import Count, Sum, Value, OuterRef, Subquery, DateTimeField
from django.db.models.functions import Coalesce
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.http.request import HttpRequest
from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntry

from django_celery_beat.models import (SolarSchedule,
                                       PeriodicTask,
                                       IntervalSchedule,
                                       ClockedSchedule,
                                       CrontabSchedule)

from rangefilter.filters import (
    DateRangeFilterBuilder,
    DateTimeRangeFilterBuilder,
    NumericRangeFilterBuilder,
    DateRangeQuickSelectListFilterBuilder,
)

from partners.utils.periodic_tasks import edit_time_for_task_check_directions_on_active

from .utils.admin import NewUTMSourceFilter, ReviewAdminMixin, DateTimeRangeFilter, UTMSourceFilter
from .utils.endpoints import try_generate_icon_url
from .models import ExchangeAdmin, ExchangeAdminOrder, NewBaseAdminComment, NewBaseComment, Valute, PartnerTimeUpdate, Guest, CustomOrder, FeedbackForm, NewBaseReview

from no_cash import models as no_cash_models
from cash import models as cash_models
from partners import models as partner_models


#DONT SHOW PERIODIC TASKS IN ADMIN PANEL
admin.site.unregister(SolarSchedule)
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(CrontabSchedule)

#DONT SHOW USER AND GROUP IN ADMIN PANEL
# admin.site.unregister(User)
# admin.site.unregister(Group)


class CustomAdminSite(AdminSite):
    index_template = 'admin/custom_index.html'

    site_header = 'Страница для ослеживания действий в админ панели'
    

custom_admin_site = CustomAdminSite(name='admin22')


@admin.register(LogEntry, site=custom_admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'content_type',
        'action_flag',
        'action_time',
    )
    fields = (
        'user',
        'content_type',
        'object_id',
        'object_repr',
        'action_flag',
        'action_time',
    )

    def has_change_permission(self, request, obj = ...):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user',
                                                            'content_type')


@admin.register(FeedbackForm)
class FeedbackFormAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        )
    
    readonly_fields = (
        'time_create',
        'description',
    )
    
    fields = (
        'username',
        'email',
        'reasons',
        'description',
        'time_create',
    )

    ordering = (
        '-time_create',
    )


@admin.register(PartnerTimeUpdate)
class PartnerTimeUpdateAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        )
    fields = (
        'amount',
        'unit_time',
    )

    def has_delete_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        update_fields = []
        fields_to_update_task = {}

        if change:
            for key, value in form.cleaned_data.items():
                if value != form.initial[key]:
                    update_fields.append(key)
                match key:
                    case 'amount':
                        fields_to_update_task[key] = value
                    case 'unit_time':
                        fields_to_update_task[key] = value

            obj.save(update_fields=update_fields)

            match obj.name:
                case 'Управление временем проверки активности направлений':
                    task = 'check_update_time_for_directions_task'
                    edit_time_for_task_check_directions_on_active(task,
                                                                  fields_to_update_task)
                case 'Управление временем обнуления популярности направления':
                    task = 'update_popular_count_direction_time_task'
                    edit_time_for_task_check_directions_on_active(task,
                                                                  fields_to_update_task)
                # case 'Управление временем жизни направлений':
                #     edit_time_live_for_partner_directions(fields_to_update_task)
        else:
            return super().save_model(request, obj, form, change)


class CustomDateTimeFilter(admin.SimpleListFilter):
    title = 'Фильтры по дате'
    parameter_name = 'custom_date_filter'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Сегодня'),
            ('yesterday', 'Вчера'),
            ('this_week', 'В течении 7 дней'),
            ('this_month', 'В этом месяце'),
            ('this_year', 'В этом году'),
            ('date_exists', 'Дата указана'),
            ('date_not_exists', 'Дата не указана'),
        )

    def queryset(self, request, queryset):
        today = datetime.now()
        print(today)
        if self.value() == 'today':
            start_of_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_today = today.replace(hour=23, minute=59, second=59, microsecond=999999)
            return queryset.filter(time_create__range=(start_of_today, end_of_today))
        elif self.value() == 'yesterday':
            start_of_yesterday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            end_of_yesterday = today.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
            return queryset.filter(time_create__range=(start_of_yesterday, end_of_yesterday))
        elif self.value() == 'this_week':
            # start_of_week = today - timedelta(days=today.weekday())
            start_of_week = today - timedelta(days=6, hours=23, minutes=59, seconds=59)

            # end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
            end_of_week = today

            return queryset.filter(time_create__range=(start_of_week, end_of_week))
        elif self.value() == 'this_month':
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            return queryset.filter(time_create__range=(start_of_month, end_of_month))
        elif self.value() == 'this_year':
            start_of_year = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_of_year = today.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
            return queryset.filter(time_create__range=(start_of_year, end_of_year))
        elif self.value() == 'date_exists':
            return queryset.exclude(time_create__isnull=True)
        elif self.value() == 'date_not_exists':
            return queryset.filter(time_create__isnull=True)
        
        return queryset



#Отображение Гостевых пользователей в админ панели
@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'tg_id',
        'link_count',
        'is_active',
        'utm_source',
        'time_create',
    )

    readonly_fields = (
        'link_count',
        'utm_source',
        'time_create',
    )

    list_filter = (
        CustomDateTimeFilter,
        ("time_create", DateRangeFilterBuilder()),
        NewUTMSourceFilter,
        # ('time_create', DateRangeQuickSelectListFilterBuilder()),
        # ("time_create", NumericRangeFilterBuilder()),
        # 'time_create',
        # UTMSourceSecondPartFilter,
        )
    ordering = (
        '-time_create',
        'username',
    )
    search_fields = (
        'username',
    )

    def link_count(self, obj):
        # print(obj.__dict__)
        # no_cash_count = no_cash_models.ExchangeLinkCount.objects.filter(user_id=obj.tg_id)\
        #                                                         .aggregate(count=Sum('count'))
        # cash_count = cash_models.ExchangeLinkCount.objects.filter(user_id=obj.tg_id)\
        #                                                         .aggregate(count=Sum('count'))
        # partner_count = partner_models.ExchangeLinkCount.objects.filter(user_id=obj.tg_id)\
        #                                                         .aggregate(count=Sum('count'))
        
        # sum_count = [count for count in (no_cash_count,
        #                                  cash_count,
        #                                  partner_count) if count is not None]
        sum_count = 0

        # sum_count = []

        if obj.no_cash_link_count:
            sum_count += obj.no_cash_link_count

        if obj.cash_link_count:
            sum_count += obj.cash_link_count

        if obj.partner_link_count:
            sum_count += obj.partner_link_count

        if obj.partner_country_link_count:
            sum_count += obj.partner_country_link_count

        # sum_count += obj.no_cash_link_count + obj.cash_link_count\
        #                  + obj.partner_link_count + obj.partner_country_link_count
        
        return sum_count


        # for count in (no_cash_count, cash_count, partner_count):
        #     if count['count'] is not None:
        #         sum_count.append(count['count'])

        # # res = no_cash_count['count'] +\
        # #         cash_count['count'] +\
        # #         partner_count['count']
        # res = sum(sum_count) if sum_count else 0
        # # print(res)
        # return res
    
    link_count.short_description = 'Счётчик перехода по ссылкам обменников'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        no_cash_link_count_subquery = no_cash_models.ExchangeLinkCount.objects.filter(
            user_id=OuterRef('tg_id')
        ).values('user_id').annotate(
            total_count=Coalesce(Sum('count'), Value(0))
        ).values('total_count')

        cash_link_count_subquery = cash_models.ExchangeLinkCount.objects.filter(
            user_id=OuterRef('tg_id')
        ).values('user_id').annotate(
            total_count=Coalesce(Sum('count'), Value(0))
        ).values('total_count')

        partner_link_count_subquery = partner_models.ExchangeLinkCount.objects.filter(
            user_id=OuterRef('tg_id')
        ).values('user_id').annotate(
            total_count=Coalesce(Sum('count'), Value(0))
        ).values('total_count')

        partner_country_link_count_subquery = partner_models.CountryExchangeLinkCount.objects.filter(
            user_id=OuterRef('tg_id')
        ).values('user_id').annotate(
            total_count=Coalesce(Sum('count'), Value(0))
        ).values('total_count')

        return queryset.annotate(no_cash_link_count=Subquery(no_cash_link_count_subquery),
                                 cash_link_count=Subquery(cash_link_count_subquery),
                                partner_link_count=Subquery(partner_link_count_subquery),
                                partner_country_link_count=Subquery(partner_country_link_count_subquery))


@admin.register(CustomOrder)
class CustomOrderAdmin(admin.ModelAdmin):
    list_display = (
        'guest',
        'request_type',
        'has_moderation',
        'time_create',
        )
    
    readonly_fields = (
        'request_type',
        'comment',
        'amount',
        'guest',
        'utm_source',
        'time_create',
        )
    ordering = (
        '-time_create',
        'moderation',
    )
    fieldsets = [
        (
            None,
            {
                "fields": ['request_type',
                           "comment",
                           "amount",
                           "guest",
                           "utm_source",
                           "time_create",
                           "moderation"]
            },
        ),
    ]

    def has_moderation(self, obj):
        return obj.status != 'Модерация' and obj.moderation
    
    def utm_source(self, obj):
        return obj.guest.utm_source
    
    utm_source.short_description = 'UTM метка'
    
    has_moderation.boolean = True
    has_moderation.short_description = 'Модерация'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        return queryset.select_related('guest')

#Отображение валют в админ панели
@admin.register(Valute)
class ValuteAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code_name',
        'get_icon',
        'type_valute',
        'available_for_partners',
        )
    list_editable = (
        'available_for_partners',
        )
    list_filter = (
        'type_valute',
        'available_for_partners',
        'is_popular',
        )
    fields = (
        'name',
        'en_name',
        'code_name',
        'icon_url',
        'get_icon',
        'type_valute',
        'is_popular',
        'available_for_partners',
        )
    readonly_fields = (
        'get_icon',
        )
    search_fields = (
        'name',
        'code_name',
        'en_name',
        )
    ordering = (
        '-available_for_partners',
        'code_name',
        )
    list_per_page = 20

    def get_icon(self, obj):
        if obj.icon_url:
            icon_url = try_generate_icon_url(obj)
            return mark_safe(f"<img src='{icon_url}' width=40")

    get_icon.short_description = 'Иконка'


#Базовое отображение комментариев в админ панели
class BaseCommentAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        "username",
        "get_exchange",
        "time_create",
        "moderation",
        )
    readonly_fields = (
        'moderation',
        'review',
        )
    ordering = (
        '-time_create',
        'moderation',
        )
    list_filter = (
        'time_create',
        )

    def get_exchange(self, obj):
        return obj.review.exchange
    
    get_exchange.short_description = 'Обменник'

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request)\
                        .select_related('review', 'review__exchange')
    

#Базовое отображение комментариев на странице связанного отзыва
class BaseCommentStacked(admin.StackedInline):
    extra = 0
    readonly_fields = (
        'moderation',
        )
    ordering = (
        '-time_create',
        'status',
        )
    classes = [
        'collapse',
        ]

    def get_queryset(self, request):
        return super().get_queryset(request)\
                        .select_related('review', 'review__exchange', 'guest')


#Базовое отображение комментариев администрации на странице связанного отзыва
class BaseAdminCommentStacked(admin.StackedInline):
    extra = 0
    classes = [
        'collapse',
        ]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related('review',
                                                            'review__exchange')


#Базовое отображение отзывов в админ панели
class BaseReviewAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        "username",
        "exchange",
        "time_create",
        "moderation",
        "comment_count",
        )
    list_filter = (
        'time_create',
        )
    readonly_fields = (
        'moderation',
        )
    ordering = (
        # 'exchange__name',
        '-time_create',
        # 'status',
        )
    
    def comment_count(self, obj):
        return obj.comment_count
    
    comment_count.short_description = 'Число комментариев'

    def get_queryset(self, request):
        return super().get_queryset(request)\
                        .select_related('exchange',
                                        'guest')\
                        .annotate(comment_count=Count('comments'))


#Базовое отображение отзывов на странице связанного обменника
class BaseReviewStacked(admin.StackedInline):
    extra = 0
    readonly_fields = (
        'moderation',
        )
    show_change_link = True
    classes = [
        'collapse',
        ]
    raw_id_fields = ('guest', )


#Базовое отображение готовых направлений в админ панели
class BaseExchangeDirectionAdmin(admin.ModelAdmin):
    list_display = (
        "get_display_name",
        )
    # list_filter = (
    #     'direction',
    #     'exchange',
    #     )

    def has_change_permission(self, request, obj = None):
        return False
    
    def has_add_permission(self, request, obj = None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request)\
                        .select_related('exchange',
                                        'direction',
                                        'direction__valute_from',
                                        'direction__valute_to')
    


#Базовое отображение готовых направлений на странице связанного обменника
class BaseExchangeDirectionStacked(admin.StackedInline):
    classes = [
        'collapse',
        ]
    # max_num = 20
    
    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    
    def has_add_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    

#
class BaseExchangeLinkCountStacked(admin.StackedInline):
    classes = [
        'collapse',
        ]
    
    fields = (
        'count',
        'user',
        'exchange_direction',
    )

    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    
    def has_add_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange',
                                                            'user',
                                                            'exchange_direction',
                                                            'exchange_direction__exchange',
                                                            'exchange_direction__direction',
                                                            'exchange_direction__direction__valute_from',
                                                            'exchange_direction__direction__valute_to')\
                                            .order_by('-count')

#


#Базовое отображение обменника в админ панели
class BaseExchangeAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        'name',
        # 'xml_url',
        'link_count',
        'is_active',
        'time_create',
        'high_aml',
        )
    readonly_fields = (
        # 'direction_black_list',
        'is_active',
        # 'course_count',
        # 'reserve_amount',
        # 'age',
        # 'country',
        'get_total_direction_count',
        'time_create',
        'get_icon',
        'link_count',
        )
    
    list_editable = (
        'high_aml',
    )
    list_filter = (
        'name',
    )
    search_fields = (
        'name',
    )
    
    def link_count(self, obj):
        exchange_link_count = obj.exchange_counts.all()

        _sum = sum([link.count for link in exchange_link_count])
        # print(obj.link_count)
        return _sum
    
    link_count.short_description = 'Счетчик перехода по ссылке'

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request)
        # return queryset.annotate(link_count=Sum('exchange_counts__count'))
        return queryset.prefetch_related('exchange_counts')


    def get_icon(self, obj):
        if obj.icon_url:
            icon_url = try_generate_icon_url(obj)
            return mark_safe(f"<img src='{icon_url}' width=40")

    get_icon.short_description = 'Иконка'
    
    fieldsets = [
        (
            None,
            {
                "fields": [("name", "en_name"),
                           "xml_url",
                           "partner_link",
                           "is_active",
                           "is_vip",
                           'high_aml',
                           "get_total_direction_count",
                           "reserve_amount",
                           "age",
                           'time_create',
                           "country",
                           ("period_for_create", "period_for_update", "period_for_parse_black_list"),
                           'icon_url',
                           'get_icon',
                           'link_count'],
            },
        ),
        # (
        #     "Отсутствующие направления",
        #     {
        #         "classes": ["collapse"],
        #         "fields": ["direction_black_list"],
        #     },
        # ),
    ]


#Базовое отображение направлений в админ панели
class BaseDirectionAdmin(admin.ModelAdmin):
    list_display = (
        'get_direction_name',
        'popular_count',
        )
    list_select_related = (
        'valute_from',
        'valute_to',
        )
    search_fields = (
        'valute_from__code_name',
        'valute_to__code_name',
        )
    readonly_fields = (
        'popular_count',
        )
    # list_filter = (
    #     'popular_count',
    # )

    autocomplete_fields = ['valute_from',
                           'valute_to']

    def get_direction_name(self, obj):
        return f'{obj.valute_from} -> {obj.valute_to}'
    
    get_direction_name.short_description = 'Название направления'
    
    def has_change_permission(self, request, obj = None):
        return False
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request)\
                        .select_related('valute_from',
                                        'valute_to')
    


class BasePopularDirectionAdmin(admin.ModelAdmin):
    readonly_fields = (
        'name',
    )
    fields = (
        'name',
        'directions',
    )
    def has_add_permission(self, request, obj = None):
        return False
    
    def has_delete_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    

class BaseExchangeLinkCountAdmin(admin.ModelAdmin):
    list_display = (
        # 'exchange',
        'exchange_direction',
        'user',
        'count',
        )
    list_filter = (
        'exchange',
        'user',
    )

    ordering = (
        '-count',
        '-user',
        'exchange',
    )
    # readonly_fields = (
    #     'exchange',
    #     'user',
    #     'count',
    #     'exchange'
    # )
    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        return False
    # fields = (
    #     'name',
    #     'directions',
    # )
    # def has_add_permission(self, request, obj = None):
    #     return False
    
    # def has_delete_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
    #     return False

@admin.register(ExchangeAdminOrder)
class ExchangeAdminOrderAdmin(admin.ModelAdmin):
    list_display = (
        'user_id',
        'exchange_name',
        'moderation',
        'time_create',
    )
    readonly_fields = (
        'moderation',
        'activate_link',
    )
    fields = (
        'user_id',
        'exchange_name',
        'activate_link',
    )

    ordering = (
        '-time_create',
    )

    def activate_link(self, obj):
        return f'https://t.me/MoneySwap_robot?start=admin_activate'
    
    activate_link.short_description = 'Ссылка для активации'


@admin.register(ExchangeAdmin)
class ExchangeAdminAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'exchange_name',
        'exchange_marker',
    )

    raw_id_fields = (
        'user',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    # readonly_fields = (
    #     'moderation',
    # )
    # fields = (
    #     'user_id',
    #     'exchange_name',
    # )
class NewBaseAdminCommentStacked(admin.StackedInline):
    model = NewBaseAdminComment
    extra = 0
    classes = [
        'collapse',
        ]
    
class NewBaseCommentStacked(admin.StackedInline):
    model = NewBaseComment
    extra = 0
    classes = [
        'collapse',
        ]


@admin.register(NewBaseReview)
class NewBaseReviewAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        'username',
        'exchange_name',
        'time_create',
        'moderation',
    )

    list_filter = (
        'exchange_name',
        'guest',
    )

    ordering = (
        '-time_create',
    )

    inlines = [
        NewBaseAdminCommentStacked,
        NewBaseCommentStacked,
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('guest')
    
    
@admin.register(NewBaseComment)
class NewBaseCommentAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        'username',
        'exchange_name',
        'time_create',
        'moderation',
    )

    list_filter = (
        'guest',
    )

    readonly_field = (
        'exchange_name',
    )

    ordering = (
        '-time_create',
    )

    def exchange_name(self, obj):
        return obj.review.exchange_name

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('review',
                                                            'guest')
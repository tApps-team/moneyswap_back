from typing import Any

from django.db.models import Count, Sum, Subquery, F
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.http.request import HttpRequest

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

from .utils.admin import ReviewAdminMixin, DateTimeRangeFilter, UTMSourceFilter
from .utils.endpoints import try_generate_icon_url
from .models import Valute, PartnerTimeUpdate, Guest, CustomOrder, FeedbackForm

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


# @admin.register(LogEntry)
# class LogEntryAdmin(admin.ModelAdmin):
#     list_display = (
#         'user',
#     )

@admin.register(FeedbackForm)
class FeedbackFormAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        )
    
    readonly_fields = (
        'time_create',
    )
    
    fields = (
        'username',
        'email',
        'reasons',
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


#Отображение Гостевых пользователей в админ панели
@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'tg_id',
        'link_count',
        'is_active',
        'utm_source',
    )

    readonly_fields = (
        'link_count',
        'utm_source',
        'time_create',
    )

    # list_filter = (
    #     ("created_at", DateRangeFilterBuilder()),
    #     (
    #         "updated_at",
    #         DateTimeRangeFilterBuilder(
    #             title="Custom title",
    #             default_start=datetime(2020, 1, 1),
    #             default_end=datetime(2030, 1, 1),
    #         ),
    #     ),
    #     ("num_value", NumericRangeFilterBuilder()),
    #     ("created_at", DateRangeQuickSelectListFilterBuilder()),  # Range + QuickSelect Filter
    # )

    # list_filter = (
    #     'time_create',
    #     'utm_source',
    #     DateTimeRangeFilter,
    # )
    list_filter = (
        ("time_create", DateRangeFilterBuilder()),
        UTMSourceFilter,
        # ("time_create", NumericRangeFilterBuilder()),
        # ('time_create', DateRangeQuickSelectListFilterBuilder()),
        # 'time_create',
        # UTMSourceSecondPartFilter,
        )

    def link_count(self, obj):
        no_cash_count = no_cash_models.ExchangeLinkCount.objects.filter(user_id=obj.tg_id)\
                                                                .aggregate(count=Sum('count'))
        cash_count = cash_models.ExchangeLinkCount.objects.filter(user_id=obj.tg_id)\
                                                                .aggregate(count=Sum('count'))
        partner_count = partner_models.ExchangeLinkCount.objects.filter(user_id=obj.tg_id)\
                                                                .aggregate(count=Sum('count'))
        
        # sum_count = [count for count in (no_cash_count,
        #                                  cash_count,
        #                                  partner_count) if count is not None]
        sum_count = []
        for count in (no_cash_count, cash_count, partner_count):
            if count['count'] is not None:
                sum_count.append(count['count'])

        # res = no_cash_count['count'] +\
        #         cash_count['count'] +\
        #         partner_count['count']
        res = sum(sum_count) if sum_count else 0
        # print(res)
        return res
    
    link_count.short_description = 'Счётчик перехода по ссылкам обменников'


@admin.register(CustomOrder)
class CustomOrderAdmin(admin.ModelAdmin):
    list_display = (
        'guest',
        'request_type',
        'has_moderation',
        'time_create',
        )
    
    readonly_fields = (
        'time_create',
        )
    ordering = (
        '-time_create',
        'moderation',
    )

    def has_moderation(self, obj):
        return obj.status != 'Модерация' and obj.moderation
    
    has_moderation.boolean = True


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
        'exchange__name',
        '-time_create',
        'status',
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


#Базовое отображение готовых направлений в админ панели
class BaseExchangeDirectionAdmin(admin.ModelAdmin):
    list_display = (
        "get_display_name",
        )
    list_filter = (
        'direction',
        'exchange',
        )

    def has_change_permission(self, request, obj = None):
        return False
    
    def has_add_permission(self, request, obj = None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request)\
                        .select_related('exchange')
    


#Базовое отображение готовых направлений на странице связанного обменника
class BaseExchangeDirectionStacked(admin.StackedInline):
    classes = [
        'collapse',
        ]
    
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
                                                            'user')\
                                            .order_by('-count')

#


#Базовое отображение обменника в админ панели
class BaseExchangeAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        'name',
        'xml_url',
        'is_active',
        )
    readonly_fields = (
        # 'direction_black_list',
        'is_active',
        # 'course_count',
        # 'reserve_amount',
        # 'age',
        # 'country',
        'link_count',
        )
    
    def link_count(self, obj):
        return obj.link_count
    
    link_count.short_description = 'Счетчик перехода по ссылке'

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request)
        return queryset.annotate(link_count=Sum('exchange_counts__count'))
    
    fieldsets = [
        (
            None,
            {
                "fields": [("name", "en_name"),
                           "xml_url",
                           "partner_link",
                           "is_active",
                           "is_vip",
                           "course_count",
                           "reserve_amount",
                           "age",
                           "country",
                           ("period_for_create", "period_for_update", "period_for_parse_black_list"),
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
    list_filter = (
        'popular_count',
    )

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
from collections.abc import Sequence
from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.db.models import Count, Q, Sum, Value, Subquery, OuterRef, Prefetch
from django.db.models.functions import Coalesce
from django.http.request import HttpRequest
from django.utils.safestring import mark_safe
from django.utils import timezone

from general_models.utils.endpoints import try_generate_icon_url

from .periodic_tasks import (manage_periodic_task_for_create,
                             manage_periodic_task_for_update,
                             manage_periodic_task_for_parse_black_list)

from general_models.admin import (BaseCommentAdmin,
                                  BaseCommentStacked,
                                  BaseReviewAdmin,
                                  BaseReviewStacked,
                                  BaseExchangeAdmin,
                                  BaseExchangeDirectionAdmin,
                                  BaseExchangeDirectionStacked,
                                  BaseDirectionAdmin,
                                  BaseAdminCommentStacked,
                                  BasePopularDirectionAdmin,
                                  BaseExchangeLinkCountAdmin,
                                  BaseExchangeLinkCountStacked)
from general_models.tasks import parse_reviews_for_exchange

import no_cash.models as no_cash_models

from .models import (Country,
                     City,
                     Exchange,
                     Direction,
                     ExchangeDirection,
                     Review,
                     Comment,
                     AdminComment,
                     PopularDirection,
                     ExchangeLinkCount)


#Отображение городов в админ панели
@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code_name',
        'country',
        'is_parse',
        )
    list_editable = (
        'is_parse',
        )
    list_select_related = (
        'country',
        )
    ordering = (
        '-is_parse',
        'name',
        )
    search_fields = (
        'name',
        'country__name',
        )
    list_per_page = 20


#Отображение городов на странице связанной страны
class CityStacked(admin.StackedInline):
    model = City
    extra = 0
    fields = (
        'is_parse',
        )
    ordering = (
        '-is_parse',
        'name',
        )
    show_change_link = True


#Отображение стран в админ панели
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        'get_icon',
        )
    readonly_fields = (
        'get_icon',
        )
    search_fields = (
        'name',
        )
    inlines = [
        CityStacked,
        ]

    def get_icon(self, obj):
        if obj.icon_url:
            icon_url = try_generate_icon_url(obj)
            return mark_safe(f"<img src='{icon_url}' width=40")
    
    get_icon.short_description = 'Текущий флаг'


#Отображение комментариев в админ панели
# @admin.register(Comment)
class CommentAdmin(BaseCommentAdmin):
    
    def get_queryset(self, request):
        return super().get_queryset(request)


#Отображение комментариев на странице связанного отзыва
class CommentStacked(BaseCommentStacked):
    model = Comment

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related('review')


#Отображение комментариев администрации на странице связанного отзыва
class AdminCommentStacked(BaseAdminCommentStacked):
    model = AdminComment


#Отображение отзывов в админ панели
# @admin.register(Review)
class ReviewAdmin(BaseReviewAdmin):
    inlines = [
        CommentStacked,
        AdminCommentStacked,
        ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        if not request.user.is_superuser:
                return False
        return super().has_add_permission(request)

    def get_queryset(self, request): 
        return super().get_queryset(request)


#Отображение отзывов на странице связанного обменника
class ReviewStacked(BaseReviewStacked):
    model = Review

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related('exchange')


#Отображение готовых направлений на странице связанного обменника
class ExchangeDirectionStacked(BaseExchangeDirectionStacked):
    model = ExchangeDirection

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related('exchange',
                                                            'city',
                                                            'direction',
                                                            'direction__valute_from',
                                                            'direction__valute_to')


class ExchangeLinkCountStacked(BaseExchangeLinkCountStacked):
    model = ExchangeLinkCount

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange',
                                                            'user',
                                                            'exchange_direction',
                                                            'exchange_direction__exchange',
                                                            'exchange_direction__city',
                                                            'exchange_direction__direction',
                                                            'exchange_direction__direction__valute_from',
                                                            'exchange_direction__direction__valute_to')\
                                            .order_by('-count')


#Отображение обменников в админ панели
@admin.register(Exchange)
class ExchangeAdmin(BaseExchangeAdmin):
    inlines = [
        ExchangeDirectionStacked,
        # ReviewStacked,
        ExchangeLinkCountStacked,
        ]

    def get_total_direction_count(self, obj):
        # print(obj.__dict__)
        direction_count = obj.direction_count
        # print(direction_count)
        try:
            no_cash_exchange = no_cash_models.Exchange.objects.annotate(no_cash_direction_count=Count('directions',
                                                                                                        filter=Q(directions__is_active=True),
                                                                                                        distinct=True))\
                                                                .get(name=obj.name)
        except Exception as ex:
            pass
        else:
            if no_cash_exchange and no_cash_exchange.no_cash_direction_count:
                direction_count += no_cash_exchange.no_cash_direction_count

        return direction_count
    
    get_total_direction_count.short_description = 'Кол-во активных направлений'
    
    def get_formset_kwargs(self, request, obj, inline, prefix):
        formset_kwargs = super().get_formset_kwargs(request, obj, inline, prefix)
        
        if isinstance(inline, ExchangeDirectionStacked) or \
            isinstance(inline, ReviewStacked) or \
                isinstance(inline, ExchangeLinkCountStacked):
            queryset = formset_kwargs['queryset']

            ids = queryset.filter(exchange=obj).values_list('pk', flat=True)[:20]

            formset_kwargs['queryset'] = queryset.filter(pk__in=ids)
        return formset_kwargs
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        update_fields = []

        if change: 
            print(form.cleaned_data.items())
            for key, value in form.cleaned_data.items():
                # print(obj.name)
                # print('key', key)
                # print('value', value)
                if key == 'id':
                    continue
                if value != form.initial[key]:
                    match key:
                        case 'period_for_create':
                            manage_periodic_task_for_create(obj.pk,
                                                            obj.name,
                                                            value)
                        # case 'period_for_update':
                        #     manage_periodic_task_for_update(obj.pk,
                        #                                     obj.name,
                        #                                     value)
                        # case 'period_for_parse_black_list':
                        #     manage_periodic_task_for_parse_black_list(obj.pk,
                        #                                               obj.name,
                        #                                               value)
                        case 'active_status':
                            if value in ('disabled', 'scam', 'skip'):
                                obj.is_active = False
                                update_fields.append('is_active')
                            
                            if value == 'disabled':
                                obj.time_disable = timezone.now()
                            else:
                                obj.time_disable = None

                            update_fields.append('time_disable')
                                
                    update_fields.append(key)

            obj.save(update_fields=update_fields)
        else:
            print('NOT CHANGE!!!!')
            super().save_model(request, obj, form, change)
            # parse_reviews_for_exchange.delay(obj.en_name, 'cash')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        # direction_count_subquery = 
        # direction_count_subquery = ExchangeDirection.objects.filter(
        #     exchange_id=OuterRef('id'),
        #     is_active=True,
        # ).values('exchange_id').annotate(
        #     total_count=Coalesce(Count('id'), Value(0))
        # ).values('total_count')

        # return queryset.annotate(direction_count=Coalesce(Subquery(direction_count_subquery), Value(0)))
        return queryset.annotate(direction_count=Count('directions',
                                                       filter=Q(directions__is_active=True),
                                                       distinct=True))


#Отображение направлений в админ панели
@admin.register(Direction)
class DirectionAdmin(BaseDirectionAdmin):

    def get_readonly_fields(self, request: HttpRequest, obj: Any | None = ...) -> list[str] | tuple[Any, ...]:
        readonly_fileds = super().get_readonly_fields(request, obj)
        readonly_fileds += ('display_name', 'actual_course', 'previous_course')
        return readonly_fileds

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related('valute_from', 'valute_to')
    

# Кастомный фильтр для ExchangeDirection для отпимизации sql запросов ( решение для N+1 prodlem ) 
class CustomDirectionFilter(admin.SimpleListFilter):
    title = 'Direction'
    parameter_name = 'direction'

    def lookups(self, request, model_admin):
        # Используйте select_related для оптимизации запроса
        directions = Direction.objects.select_related('valute_from',
                                                      'valute_to').distinct()
        return [(d.id, str(d)) for d in directions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(direction__id=self.value())
        return queryset


#Отображение готовых направлений в админ панели
@admin.register(ExchangeDirection)
class ExchangeDirectionAdmin(BaseExchangeDirectionAdmin):
    list_filter = (
        'exchange',
        CustomDirectionFilter,
    )
    def get_display_name(self, obj):
        return f'{obj.exchange} ({obj.city}: {obj.direction})'
    
    def get_list_filter(self, request: HttpRequest) -> Sequence[str]:
        list_filter = super().get_list_filter(request)
        list_filter = list_filter + ('city', )
        return list_filter

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange',
                                                            'direction',
                                                            'city')
    

@admin.register(PopularDirection)
class PopularDirectionAdmin(BasePopularDirectionAdmin):
    list_display = (
        'name',
    )
    filter_horizontal = (
        'directions',
    )
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Prefetch directions and their related valute_from and valute_to
        return qs.prefetch_related(
            Prefetch(
                'directions',
                queryset=Direction.objects.select_related('valute_from', 'valute_to')
            )
        )
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'directions':
            # Оптимизируем queryset для виджета filter_horizontal
            kwargs['queryset'] = Direction.objects.select_related('valute_from', 'valute_to')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(ExchangeLinkCount)
class ExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    pass
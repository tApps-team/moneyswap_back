from typing import Any
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.db.models.query import QuerySet
from django.db.models import Count, Q, Sum, Value, Subquery, OuterRef, Prefetch, F
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.db.models import Sum, Count
from django.contrib.admin import SimpleListFilter
from django.urls import path

from django.utils import timezone

import cash.models as cash_models
from cash.forms import BulkDirectionForm

from no_cash.models import (Exchange,
                            Direction,
                            ExchangeDirection,
                            PopularDirection,
                            ExchangeLinkCount,
                            NewDirection,
                            NewExchangeDirection,
                            NewExchangeLinkCount)
from no_cash.periodic_tasks import (manage_periodic_task_for_create,
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
                                  BaseExchangeLinkCountStacked,
                                  NewBaseExchangeLinkCountAdmin,
                                  NewBaseDirectionAdmin)
from general_models.tasks import parse_reviews_for_exchange


#Отображение комментариев в админ панели
# @admin.register(Comment)
class CommentAdmin(BaseCommentAdmin):
    pass


#Отображение готовых направлений на странице связанного обменника
class ExchangeDirectionStacked(BaseExchangeDirectionStacked):
    model = ExchangeDirection

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange',
                                                            'direction',
                                                            'direction__valute_from',
                                                            'direction__valute_to')
    

class ExchangeLinkCountStacked(BaseExchangeLinkCountStacked):
    model = ExchangeLinkCount

    # fields = (
    #     'count',
    #     'user',
    # )

    # def get_queryset(self, request):
    #     return super().get_queryset(request).select_related('exchange',
    #                                                         'user')


#Отображение обменников в админ панели
# @admin.register(Exchange)
class ExchangeAdmin(BaseExchangeAdmin):
    # list_display = ('link_count', )
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
            cash_exchange = cash_models.Exchange.objects.annotate(cash_direction_count=Count('directions',
                                                                                                        filter=Q(directions__is_active=True)))\
                                                                .get(name=obj.name)
        except Exception as ex:
            pass
        else:
            if cash_exchange and cash_exchange.cash_direction_count:
                direction_count += cash_exchange.cash_direction_count

        return direction_count
    
    get_total_direction_count.short_description = 'Кол-во активных направлений'
    
    def get_formset_kwargs(self, request, obj, inline, prefix):
        formset_kwargs = super().get_formset_kwargs(request, obj, inline, prefix)
        
        if isinstance(inline, ExchangeDirectionStacked) or \
                isinstance(inline, ExchangeLinkCountStacked):
            queryset = formset_kwargs['queryset']

            ids = queryset.filter(exchange=obj).values_list('pk', flat=True)[:20]

            formset_kwargs['queryset'] = queryset.filter(pk__in=ids)
        return formset_kwargs
    
    # def link_count(self, obj):
    #     return obj.link_count

    # def get_queryset(self, request: HttpRequest) -> QuerySet:
    #     queryset = super().get_queryset(request)
    #     return queryset.annotate(link_count=Sum('exchangelistcount__count'))
    
    def save_model(self, request, obj, form, change):
        update_fields = []

        if change:
            print('CHANGE!!!')
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
                        case 'period_for_update':
                            manage_periodic_task_for_update(obj.pk,
                                                            obj.name,
                                                            value)
                        case 'period_for_parse_black_list':
                            manage_periodic_task_for_parse_black_list(obj.pk,
                                                                      obj.name,
                                                                      value)
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
            return super().save_model(request, obj, form, change)
            # parse_reviews_for_exchange.delay(obj.en_name, 'no_cash')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        # direction_count_subquery = 
        # direction_count_subquery = ExchangeDirection.objects.filter(
        #     exchange_id=OuterRef('id'),
        #     is_active=True,
        # ).values('exchange_id').annotate(
        #     total_count=Coalesce(Count('id'), Value(0))
        # ).values('total_count')
        queryset = queryset.annotate(direction_count=Count('directions',
                                                       filter=Q(directions__is_active=True),
                                                       distinct=True))
        
        # for w in queryset.get(name='1WM').directions.all():
        #     print(w)

        return queryset
        # return queryset.annotate(direction_count=Coalesce(Subquery(direction_count_subquery), Value(0)))

#Отображение направлений в админ панели
# @admin.register(Direction)
class DirectionAdmin(BaseDirectionAdmin):
    pass


@admin.register(NewDirection)
class NewDirectionAdmin(NewBaseDirectionAdmin):

    class Media:
        js = ('no_cash/js/test_1.js', )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'bulk-add/',
                self.admin_site.admin_view(self.bulk_create_directions_view),
                name='bulk_create_directions',
            ),
        ]
        return custom_urls + urls

    def bulk_create_directions_view(self, request):

        if request.method == "POST":
            form = BulkDirectionForm(request.POST)
            if form.is_valid():
                valute_from = form.cleaned_data["valute_from"]
                valute_to_list = form.cleaned_data["valute_to"]

                direction_list = [(valute_from, valute_to) for valute_to in valute_to_list]
                direction_list += [(valute_to, valute_from) for valute_from, valute_to in direction_list]

                create_list = []
                for direction in direction_list:
                    valute_from, valute_to = direction
                    valute_from_type = valute_from.type_valute
                    valute_to_type = valute_to.type_valute

                    # проверка что направления будут безналичные
                    check_set = set(['Наличные', 'ATM QR'])
                    
                    if set([valute_from_type, valute_to_type]).intersection(check_set):
                        print('NO NO NO')
                        continue

                    data = {
                        'valute_from_id': valute_from.code_name,
                        'valute_to_id': valute_to.code_name,
                    }

                    create_list.append(NewDirection(**data))
                
                try:
                    NewDirection.objects.bulk_create(create_list,
                                                     ignore_conflicts=True)
                    self.message_user(request, "Направления успешно созданы")
                except Exception as ex:
                    print(ex)
                    self.message_user(request,
                                      "Возникла ошибка при создании",
                                      level=messages.WARNING)

                return redirect("..")

        else:
            form = BulkDirectionForm()

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title='Создание безналичных направлений'
        )

        return render(request, "admin/bulk_create_directions.html", context)
    pass


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
    

class NewCustomDirectionFilter(admin.SimpleListFilter):
    title = 'Направление для обмена'
    parameter_name = 'direction'

    def lookups(self, request, model_admin):
        # Используйте select_related для оптимизации запроса
        directions = NewDirection.objects.select_related('valute_from',
                                                         'valute_to').distinct()
        return [(d.id, str(d)) for d in directions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(direction__id=self.value())
        return queryset


#Отображение готовых направлений в админ панели
# @admin.register(ExchangeDirection)
class ExchangeDirectionAdmin(BaseExchangeDirectionAdmin):
    list_filter = (
        'exchange',
        CustomDirectionFilter,
    )
    def get_display_name(self, obj):
        return f'{obj.exchange} ({obj.direction})'
    
    get_display_name.short_description = 'Название'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange',
                                                            'direction',
                                                            'direction__valute_to',
                                                            'direction__valute_from')
    

@admin.register(NewExchangeDirection)
class NewExchangeDirectionAdmin(BaseExchangeDirectionAdmin):
    list_filter = (
        'exchange',
        NewCustomDirectionFilter,
    )
    def get_display_name(self, obj):
        return f'{obj.exchange} ({obj.direction})'
    
    get_display_name.short_description = 'Название'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange',
                                                            'direction',
                                                            'direction__valute_to',
                                                            'direction__valute_from')
    


# class PopularDirectionFilter(SimpleListFilter):
#     title = 'Направление'
#     parameter_name = 'direction'

#     def lookups(self, request, model_admin):
#         directions = Direction.objects.select_related('valute_from', 'valute_to')
#         return [
#             (d.id, f'{d.valute_from} → {d.valute_to}') for d in directions
#         ]

#     def queryset(self, request, queryset):
#         if self.value():
#             return queryset.filter(directions__id=self.value())
#         return queryset


# @admin.register(PopularDirection)
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


# @admin.register(ExchangeLinkCount)
class ExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    pass


@admin.register(NewExchangeLinkCount)
class NewExchangeListCountAdmin(NewBaseExchangeLinkCountAdmin):
    pass
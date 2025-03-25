from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.db.models import Sum, Count

from no_cash.models import (Exchange,
                            Direction,
                            ExchangeDirection,
                            Review,
                            Comment,
                            AdminComment,
                            PopularDirection,
                            ExchangeLinkCount)
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
                                  BaseExchangeLinkCountStacked)
from general_models.tasks import parse_reviews_for_exchange


#Отображение комментариев в админ панели
@admin.register(Comment)
class CommentAdmin(BaseCommentAdmin):
    pass


#Отображение комментариев на странице связанного отзыва
class CommentStacked(BaseCommentStacked):
    model = Comment


#Отображение комментариев администрации на странице связанного отзыва
class AdminCommentStacked(BaseAdminCommentStacked):
    model = AdminComment


#Отображение отзывов в админ панели
@admin.register(Review)
class ReviewAdmin(BaseReviewAdmin):
    inlines = [
        CommentStacked,
        AdminCommentStacked,
        ]
    
    # def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
    #     return super().get_queryset(request)\
    #                     .select_related('guest')


#Отображение отзывов на странице связанного обменника
class ReviewStacked(BaseReviewStacked):
    model = Review

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('exchange')


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
    #                                                         'user')\
    #                                         .order_by('-count')


#Отображение обменников в админ панели
@admin.register(Exchange)
class ExchangeAdmin(BaseExchangeAdmin):
    # list_display = ('link_count', )
    inlines = [
        ExchangeDirectionStacked,
        ReviewStacked,
        ExchangeLinkCountStacked,
        ]
    
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
                    update_fields.append(key)
            obj.save(update_fields=update_fields)
        else:
            print('NOT CHANGE!!!!')
            super().save_model(request, obj, form, change)
            # parse_reviews_for_exchange.delay(obj.en_name, 'no_cash')


#Отображение направлений в админ панели
@admin.register(Direction)
class DirectionAdmin(BaseDirectionAdmin):
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


#Отображение готовых направлений в админ панели
@admin.register(ExchangeDirection)
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
    



@admin.register(PopularDirection)
class PopularDirectionAdmin(BasePopularDirectionAdmin):
    list_display = (
        'name',
    )
    filter_horizontal = (
        'directions',
    )


@admin.register(ExchangeLinkCount)
class ExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    pass
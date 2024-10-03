from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from django_admin_action_forms import action_with_form, AdminActionForm

from django import forms
from django.contrib import admin, messages
from django.db.models import Sum
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import render

from general_models.admin import (BaseCommentAdmin,
                                  BaseCommentStacked,
                                  BaseReviewAdmin,
                                  BaseReviewStacked,
                                  BaseAdminCommentStacked,
                                  BaseExchangeLinkCountStacked,
                                  BaseExchangeLinkCountAdmin)
from general_models.utils.admin import ReviewAdminMixin

from partners.utils.endpoints import get_course_count

from .models import (Exchange,
                     Direction,
                     Review,
                     Comment,
                     CustomUser,
                     PartnerCity,
                     WorkingDay,
                     AdminComment,
                     ExchangeLinkCount)
from .utils.admin import (make_city_active,
                          update_field_time_update,
                          get_saved_course)
from .utils.cache import (get_or_set_user_account_cache,
                          set_user_account_cache)


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'exchange',
        )

    fields = (
        'user',
        'exchange',
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
         return super().get_queryset(request)\
                        .select_related('exchange', 'user')


class DirectionStacked(admin.StackedInline):
    model = Direction
    extra = 0
    show_change_link = True
    classes = [
        'collapse',
        ]
    
    fields = (
        'get_direction_name',
        'in_count',
        'out_count',
        'is_active',
        'time_update',
        )
    readonly_fields = (
        'get_direction_name',
        'in_count',
        'out_count',
        'is_active',
        'time_update',
        )
    list_select_related = (
        'direction',
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
         return super().get_queryset(request)\
                        .select_related('city',
                                        'direction',
                                        'city__city')

    def has_add_permission(self, request, obj=None):
        return False

    def get_direction_name(self, obj):
         return obj.direction.display_name
    
    get_direction_name.short_description = 'Название направления'


class ChangeOrderStatusActionForm(AdminActionForm):
    in_count = forms.FloatField(
        label="Отдаём",
        required=True,
    )
    out_count = forms.FloatField(
        label="Получаем",
        required=True,
    )



@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_directions',
        )
    
    list_display = (
        'direction',
        'city',
        'exchange_name',
        'is_active',
        )
    list_filter = (
        'city__city',
        'city__exchange',
        'direction',
        )
    readonly_fields = (
        'course',
        'saved_partner_course',
        'is_active',
        'time_update',
        )
    fields = (
        'city',
        'direction',
        'course',
        'in_count',
        'out_count',
        'saved_partner_course',
        'is_active',
        'time_update',
        )
    
    class Media:
         js = ('parnters/js/test.js', )

    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if change:
            update_fields = set()
            for key, value in form.cleaned_data.items():
                if value != form.initial[key]:
                    update_field_time_update(obj, update_fields)
                    update_fields.add(key)
            obj.save(update_fields=update_fields)
        else:
            return super().save_model(request, obj, form, change)
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if not request.user.is_superuser:
            if db_field.name == 'city':
                account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.filter(exchange=account.exchange)\
                                                .select_related('city')
        return field

    def exchange_name(self, obj=None):
        return obj.city.exchange
    
    exchange_name.short_description = 'Партнёрский обменник'

    def course(self, obj=None):
        return get_course_count(obj)
    
    course.short_description = 'Курс обмена'

    def saved_partner_course(self, obj=None):
        return get_saved_course(obj)
    
    saved_partner_course.short_description = 'Сохранённый курс'

    def has_add_permission(self, request: HttpRequest) -> bool:
        if not request.user.is_superuser:
            account = get_or_set_user_account_cache(request.user)

            if account.exchange:
                return super().has_add_permission(request)
        
        return False
    
    def has_change_permission(self, request: HttpRequest, obj: Any | None = ...) -> bool:
        if request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('city',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city__city',
                                            'city__exchange')

        if not request.user.is_superuser:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(city__exchange=account.exchange)
            
        return queryset

    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_directions(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')
    
    # def get_actions(self, request: HttpRequest):
    #     actions = super().get_actions(request)
    #     if request.user.is_superuser:
    #         del actions['get_directions_active']
    #     return actions


@admin.register(WorkingDay)
class WorkingDayAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        )


class PartnerCityStacked(admin.StackedInline):
    model = PartnerCity
    extra = 0
    show_change_link = True
    classes = [
        'collapse',
        ]
    
    fields = (
        'get_city_name',
        'has_office',
        'has_delivery',
        )
    readonly_fields = (
        'get_city_name',
        )
    list_select_related = (
        'direction',
        )

    def has_add_permission(self, request: HttpRequest, *args) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
         return super().get_queryset(request)\
                        .select_related('city')

    def get_city_name(self, obj=None):
        return obj.city
    
    get_city_name.short_description = 'Город'


@admin.register(PartnerCity)
class PartnerCityAdmin(admin.ModelAdmin):
    list_display = (
        'city',
        'exchange',
        )   
    fields = (
        'city',
        ('has_office',
        'has_delivery',),
        'time_update',
        'working_days',
    )
    inlines = [
        DirectionStacked,
        ]
    filter_horizontal = (
        'working_days',
        )

    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if not change:
            if not request.user.is_superuser:
                account = get_or_set_user_account_cache(request.user)
                partner_cities = account.exchange.partner_cities\
                                                    .filter(city=obj.city)\
                                                    .all()
                make_city_active(obj.city)

                if partner_cities:
                    has_office = obj.has_office
                    has_delivery = obj.has_delivery
                    obj = partner_cities.get()
                    obj.has_office = has_office
                    obj.has_delivery = has_delivery
                    change = True
                else:
                    obj.exchange = account.exchange
        return super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        if not request.user.is_superuser:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                return super().has_add_permission(request)
        return False
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if db_field.name == 'city':
            field.queryset = field.queryset.order_by('name')

        return field
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('city',
                                            'exchange')
        if not request.user.is_superuser:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                queryset = queryset.filter(exchange=account.exchange)
            else:
                # вернуть пустой queryset
                queryset = queryset.filter(id=0)
        return queryset
    
    def get_city_name(self, obj=None):
        return obj.city
    
    get_city_name.short_description = 'Город'
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        path_info = request.environ['PATH_INFO']
        if path_info.endswith('change/'):
            readonly_fields = ('get_city_name', 'time_update', ) + readonly_fields
        return readonly_fields

    def get_fields(self, request: HttpRequest, obj: Any | None = ...) -> Sequence[Callable[..., Any] | str]:
        fields = super().get_fields(request, obj)
        path_info = request.environ['PATH_INFO']
        if path_info.endswith('change/'):
            fields = (
                'get_city_name',
                ('has_office', 'has_delivery'),
                'time_update',
                'working_days'
            )
        return fields


@admin.register(Comment)
class CommentAdmin(BaseCommentAdmin):
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        
        if not request.user.is_superuser:
                account = get_or_set_user_account_cache(request.user)
                if account.exchange:
                    queryset = queryset\
                                    .select_related('review')\
                                    .filter(review__in=account.exchange.reviews.all())
                else:
                    queryset = queryset.filter(status='На ожидании')
        return queryset


#Отображение комментариев на странице связанного отзыва
class CommentStacked(BaseCommentStacked):
    model = Comment

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related('review')


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

    def has_add_permission(self, request: HttpRequest) -> bool:
        if not request.user.is_superuser:
                return False
        return super().has_add_permission(request)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        
        if not request.user.is_superuser:
                account = get_or_set_user_account_cache(request.user)
                if account.exchange:
                    queryset = queryset.select_related('exchange')\
                                        .filter(exchange=account.exchange)
                else:
                    queryset = queryset.filter(status='На ожидании')
        return queryset


#Отображение отзывов на странице связанного обменника
class ReviewStacked(BaseReviewStacked):
    model = Review

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request)\
                        .select_related('exchange',
                                        'exchange__account')


class ExchangeLinkCountStacked(BaseExchangeLinkCountStacked):
    model = ExchangeLinkCount


@admin.register(Exchange)
class ExchangeAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        'name',
        'en_name',
        'account',
        'has_partner_link',
        )
    readonly_fields = (
        'is_active',
        )
    filter_horizontal = ()

    inlines = [
        PartnerCityStacked,
        ReviewStacked,
        ExchangeLinkCountStacked,
        ]

    def has_partner_link(self, obj=None):
        return bool(obj.partner_link)
    
    has_partner_link.boolean = True
    has_partner_link.short_description = 'Партнёрская ссылка'

    def link_count(self, obj):
        return obj.link_count
    
    link_count.short_description = 'Счетчик перехода по ссылке'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            readonly_fields = ('partner_link', ) + readonly_fields

        return readonly_fields + ('link_count', )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        if not request.user.is_superuser:
                account = get_or_set_user_account_cache(request.user)
                exchange = account.exchange
                
                if not exchange:
                    # вернуть пустой queryset
                    queryset = super().get_queryset(request)\
                                    .filter(name='Не выбрано!!!')
                # вернуть обменник партнёра
                else:
                    queryset = super().get_queryset(request)\
                                    .select_related('account',
                                                    'account__user',
                                                    'account__exchange')\
                                    .filter(name=exchange.name)
        # вернуть все партнёрские обменники
        else:
            queryset = super().get_queryset(request)\
                            .select_related('account', 'account__user')
        
        return queryset.annotate(link_count=Sum('exchangelinkcount__count'))
    
    # fieldsets = [
    #     (
    #         None,
    #         {
    #             "fields": [("name", "en_name"),
    #                        "partner_link",
    #                        "is_active",
    #                        "is_vip",
    #                        "course_count",
    #                        "reserve_amount",
    #                        "age",
    #                        "country",
    #                        'link_count'],
    #         },
    #     ),
    # ]
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        if not request.user.is_superuser:
            account = get_or_set_user_account_cache(request.user)

            if account.exchange:
                return False
        return super().has_add_permission(request)
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if not request.user.is_superuser and not change:
            account = get_or_set_user_account_cache(request.user)
            account.exchange = obj
            super().save_model(request, obj, form, change)
            account.save()
            set_user_account_cache(account)
        else:
            return super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        obj.delete()
        if not request.user.is_superuser:
            set_user_account_cache(request.user.moderator_account)

    def delete_queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        super().delete_queryset(request, queryset)
        if not request.user.is_superuser:
            set_user_account_cache(request.user.moderator_account)



@admin.register(ExchangeLinkCount)
class ExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    pass
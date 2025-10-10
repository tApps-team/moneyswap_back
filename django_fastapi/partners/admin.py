from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any
from decimal import Decimal

from django_admin_action_forms import action_with_form, AdminActionForm

from django.db import connection
from django.shortcuts import redirect

from django import forms
from django.contrib import admin, messages
from django.db.models import Sum, Value, OuterRef, Subquery, Count
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from general_models.admin import (BaseCommentAdmin,
                                  BaseCommentStacked,
                                  BaseReviewAdmin,
                                  BaseReviewStacked,
                                  BaseAdminCommentStacked,
                                  BaseExchangeLinkCountStacked,
                                  BaseExchangeLinkCountAdmin)
from general_models.utils.admin import ReviewAdminMixin

from partners.utils.endpoints import get_course_count

from no_cash.models import Direction as NoCashDirection

from cash.models import City

from .models import (CountryExchangeLinkCount, Exchange,
                     Direction,
                     CustomUser,
                     PartnerCity,
                     WorkingDay,
                     ExchangeLinkCount,
                     PartnerCountry,
                     CountryDirection,
                     Bankomat,
                     DirectionRate,
                     CountryDirectionRate,
                     NonCashDirection,
                     NonCashDirectionRate,
                     NewPartnerCity,
                     NewPartnerCountry,
                     NewDirection,
                     NewDirectionRate,
                     NewCountryDirection,
                     NewCountryDirectionRate,
                     NewNonCashDirection,
                     NewNonCashDirectionRate,
                     NewBankomat,
                     NewCustomUser,
                     NewExchangeLinkCount,
                     NewCountryExchangeLinkCount,
                     NonCashExchangeLinkCount,
                     NewNonCashExchangeLinkCount)
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
    

@admin.register(NewCustomUser)
class NewUserAdmin(admin.ModelAdmin):
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

    class Meta:
        list_objects = True



@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_direction_course',
        'update_direction_activity'
        )
    
    list_display = (
        'pk',
        'direction',
        'city',
        'exchange_name',
        'is_active',
        'in_count',
        'out_count',

        )
    list_display_links = ('direction',)
    list_editable = (
        'in_count',
        'out_count',
    )
    list_filter = (
        'city__city',
        'city__exchange__name',
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
        print('from save_model...')
        if change:
            # print(connection.queries)
            update_fields = set()
            if not form.cleaned_data.get('id'):
                for key, value in form.cleaned_data.items():
                    if value != form.initial[key]:
                        update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                obj.save(update_fields=update_fields)
            else:
                for key in ('in_count', 'out_count'):
                    if form.cleaned_data[key] != form.initial[key]:
                        # update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                if update_fields:
                    update_field_time_update(obj, update_fields)
                    obj.save(update_fields=update_fields)
            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            # print(len(connection.queries))

        else:
            return super().save_model(request, obj, form, change)


    # Перехватываю list_editable для оптимизации SELECT запросов в один
    def changelist_view(self, request, extra_context=None):
        # print('from changelist view..')
        if request.method == 'POST' and '_save' in request.POST:
            obj_count = int(request.POST['form-TOTAL_FORMS'])
            pks = [int(request.POST[f'form-{i}-id']) for i in range(obj_count)]
            objs = list(Direction.objects.filter(pk__in=pks))  # один SELECT
            obj_dict = {o.pk: o for o in objs}

            time_update = timezone.now()
            update_objs = []

            for i in range(obj_count):
                obj_pk = int(request.POST[f'form-{i}-id'])
                in_count = Decimal(request.POST[f'form-{i}-in_count'])
                out_count = Decimal(request.POST[f'form-{i}-out_count'])
                obj = obj_dict[obj_pk]
                
                if obj.in_count != in_count or obj.out_count != out_count:
                    obj.in_count = in_count
                    obj.out_count = out_count
                    obj.time_update = time_update
                    obj.is_active = True
                    update_objs.append(obj)

            if update_objs:
                update_fields = [
                    'in_count',
                    'out_count',
                    'time_update',
                    'is_active',
                ]
                Direction.objects.bulk_update(update_objs,
                                              fields=update_fields)
                # self.message_user(request, f"{len(update_objs)} записей успешно обновлено!", messages.SUCCESS)
                self.message_user(request, f'Выбранные направления успешно обновлены!({len(update_objs)} шт)', messages.SUCCESS)

            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            return redirect(f"{request.path}?{request.META.get('QUERY_STRING','')}")
            # return redirect(request.path)
            # return super().changelist_view(request, extra_context)

        return super().changelist_view(request, extra_context)

    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            if db_field.name == 'city':
                # account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.select_related('city')
        else:
            if db_field.name == 'city':
                account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.filter(exchange=account.exchange)\
                                                .select_related('city')
        return field

    def exchange_name(self, obj=None):
        if obj.city and obj.city.exchange:
            return obj.city.exchange
        else:
            return 'Нет связааного обменника'
        
    exchange_name.short_description = 'Партнёрский обменник'

    def course(self, obj=None):
        return get_course_count(obj)
    
    course.short_description = 'Курс обмена'

    def saved_partner_course(self, obj=None):
        return get_saved_course(obj)
    
    saved_partner_course.short_description = 'Сохранённый курс'

    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            return False
        else:
            account = get_or_set_user_account_cache(request.user)

            if account.exchange:
                return super().has_add_permission(request)
        

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('city',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city__city',
                                            'city__exchange')

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(city__exchange=account.exchange)

        return queryset

    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_direction_course(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        is_active=True,
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')

    @admin.action(description='Обновить активность выбранных направлений')
    def update_direction_activity(modeladmin, request, queryset):
        time_update = datetime.now()
        queryset.update(is_active=True,
                        time_update=time_update)
        messages.success(request,
                         f'Выбранные направления успешно обновлены!({len(queryset)} шт)')
        

@admin.register(NewDirection)
class NewDirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_direction_course',
        'update_direction_activity'
        )
    
    list_display = (
        'pk',
        'direction',
        'city',
        'exchange_name',
        'is_active',
        'in_count',
        'out_count',

        )
    list_display_links = ('direction',)
    list_editable = (
        'in_count',
        'out_count',
    )
    list_filter = (
        'city__city',
        'city__exchange__name',
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
        print('from save_model...')
        if change:
            # print(connection.queries)
            update_fields = set()
            if not form.cleaned_data.get('id'):
                for key, value in form.cleaned_data.items():
                    if value != form.initial[key]:
                        update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                obj.save(update_fields=update_fields)
            else:
                for key in ('in_count', 'out_count'):
                    if form.cleaned_data[key] != form.initial[key]:
                        # update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                if update_fields:
                    update_field_time_update(obj, update_fields)
                    obj.save(update_fields=update_fields)
            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            # print(len(connection.queries))

        else:
            return super().save_model(request, obj, form, change)


    # Перехватываю list_editable для оптимизации SELECT запросов в один
    def changelist_view(self, request, extra_context=None):
        # print('from changelist view..')
        if request.method == 'POST' and '_save' in request.POST:
            obj_count = int(request.POST['form-TOTAL_FORMS'])
            pks = [int(request.POST[f'form-{i}-id']) for i in range(obj_count)]
            objs = list(NewDirection.objects.filter(pk__in=pks))  # один SELECT
            obj_dict = {o.pk: o for o in objs}

            time_update = timezone.now()
            update_objs = []

            for i in range(obj_count):
                obj_pk = int(request.POST[f'form-{i}-id'])
                in_count = Decimal(request.POST[f'form-{i}-in_count'])
                out_count = Decimal(request.POST[f'form-{i}-out_count'])
                obj = obj_dict[obj_pk]
                
                if obj.in_count != in_count or obj.out_count != out_count:
                    obj.in_count = in_count
                    obj.out_count = out_count
                    obj.time_update = time_update
                    obj.is_active = True
                    update_objs.append(obj)

            if update_objs:
                update_fields = [
                    'in_count',
                    'out_count',
                    'time_update',
                    'is_active',
                ]
                NewDirection.objects.bulk_update(update_objs,
                                              fields=update_fields)
                # self.message_user(request, f"{len(update_objs)} записей успешно обновлено!", messages.SUCCESS)
                self.message_user(request, f'Выбранные направления успешно обновлены!({len(update_objs)} шт)', messages.SUCCESS)

            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            return redirect(f"{request.path}?{request.META.get('QUERY_STRING','')}")
            # return redirect(request.path)
            # return super().changelist_view(request, extra_context)

        return super().changelist_view(request, extra_context)

    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            if db_field.name == 'city':
                # account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.select_related('city')
        else:
            if db_field.name == 'city':
                account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.filter(exchange=account.exchange)\
                                                .select_related('city')
        return field

    def exchange_name(self, obj=None):
        if obj.city and obj.city.exchange:
            return obj.city.exchange
        else:
            return 'Нет связааного обменника'
    
    exchange_name.short_description = 'Партнёрский обменник'

    def course(self, obj=None):
        return get_course_count(obj)
    
    course.short_description = 'Курс обмена'

    def saved_partner_course(self, obj=None):
        return get_saved_course(obj)
    
    saved_partner_course.short_description = 'Сохранённый курс'

    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            return False
        else:
            account = get_or_set_user_account_cache(request.user)

            if account.exchange:
                return super().has_add_permission(request)
        

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('city',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'city__city',
                                            'city__exchange')

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(city__exchange=account.exchange)

        return queryset

    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_direction_course(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        is_active=True,
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')

    @admin.action(description='Обновить активность выбранных направлений')
    def update_direction_activity(modeladmin, request, queryset):
        time_update = datetime.now()
        queryset.update(is_active=True,
                        time_update=time_update)
        messages.success(request,
                         f'Выбранные направления успешно обновлены!({len(queryset)} шт)')


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


@admin.register(PartnerCountry)
class PartnerCountryAdmin(admin.ModelAdmin):
    list_display = (
        'exchange',
        'country',
    )
    fieldsets = [
        (
            None,
            {
                "fields": ['country',
                           ('has_office',
                            'has_delivery'),
                           'time_update',
                           'min_amount',
                           'max_amount',
                           ],
            },
        ),
        (
            "Будние рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'time_from',
                    'time_to',
                ],
            },
        ),
        (
            "Выходные рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'weekend_time_from',
                    'weekend_time_to',
                ],
            },
        ),
        (
            "Рабочие дни",
            {
                "classes": ["wide"],
                "fields": [
                    "working_days",
                           ],
            },
        ),
        (
            "Города на исключение из выдачи страны",
            {
                "classes": ["wide"],
                "fields": [
                    "exclude_cities",
                           ],
            },
        ),

    ]
    filter_horizontal = (
        'working_days',
        'exclude_cities',
        )
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):

        if db_field.name == "exclude_cities":

            obj_id = request.resolver_match.kwargs.get('object_id')

            if obj_id:
                try:
                    partner_country = PartnerCountry.objects.get(pk=obj_id)
                except Exception as ex:
                    print(ex)
                    pass
                else:
                    kwargs["queryset"] = City.objects.filter(is_parse=True,
                                                             country_id=partner_country.country_id)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(NewPartnerCountry)
class NewPartnerCountryAdmin(admin.ModelAdmin):
    list_display = (
        'exchange',
        'country',
    )
    fieldsets = [
        (
            None,
            {
                "fields": ['country',
                           ('has_office',
                            'has_delivery'),
                           'time_update',
                           'min_amount',
                           'max_amount',
                           ],
            },
        ),
        (
            "Будние рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'time_from',
                    'time_to',
                ],
            },
        ),
        (
            "Выходные рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'weekend_time_from',
                    'weekend_time_to',
                ],
            },
        ),
        (
            "Рабочие дни",
            {
                "classes": ["wide"],
                "fields": [
                    "working_days",
                           ],
            },
        ),
        (
            "Города на исключение из выдачи страны",
            {
                "classes": ["wide"],
                "fields": [
                    "exclude_cities",
                           ],
            },
        ),

    ]
    filter_horizontal = (
        'working_days',
        'exclude_cities',
        )
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            return False
        else:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                return super().has_add_permission(request)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):

        if db_field.name == "exclude_cities":

            obj_id = request.resolver_match.kwargs.get('object_id')

            if obj_id:
                try:
                    partner_country = NewPartnerCountry.objects.get(pk=obj_id)
                except Exception as ex:
                    print(ex)
                    pass
                else:
                    kwargs["queryset"] = City.objects.filter(is_parse=True,
                                                             country_id=partner_country.country_id)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(CountryDirection)
class CountryDirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_direction_course',
        'update_direction_activity'
        )
    list_display = (
        'pk',
        'direction',
        'country',
        'exchange_name',
        'is_active',
        'in_count',
        'out_count',
    )
    list_display_links = ('direction',)
    list_filter = (
        'country__country',
        'country__exchange__name',
        'direction',
        )
    list_editable = (
        'in_count',
        'out_count',
    )
    readonly_fields = (
        'exchange_name',
        'time_update',
    )
    fields = (
        'country',
        'direction',
        # 'course',
        'in_count',
        'out_count',
        # 'saved_partner_course',
        'is_active',
        'time_update',
        )

    def exchange_name(self, obj):
        return obj.country.exchange
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if change:
            update_fields = set()
            if not form.cleaned_data.get('id'):
                for key, value in form.cleaned_data.items():
                    if value != form.initial[key]:
                        update_fields.add(key)
    
                update_field_time_update(obj, update_fields)
                obj.save(update_fields=update_fields)
            else:
                for key in ('in_count', 'out_count'):
                    if form.cleaned_data[key] != form.initial[key]:
                        # update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                if update_fields:
                    update_field_time_update(obj, update_fields)
                    obj.save(update_fields=update_fields)
        else:
            return super().save_model(request, obj, form, change)
        
    # Перехватываю list_editable для оптимизации SELECT запросов в один
    def changelist_view(self, request, extra_context=None):
        # print('from changelist view..')
        if request.method == 'POST' and '_save' in request.POST:
            obj_count = int(request.POST['form-TOTAL_FORMS'])
            pks = [int(request.POST[f'form-{i}-id']) for i in range(obj_count)]
            objs = list(CountryDirection.objects.filter(pk__in=pks))  # один SELECT
            obj_dict = {o.pk: o for o in objs}

            time_update = timezone.now()
            update_objs = []

            for i in range(obj_count):
                obj_pk = int(request.POST[f'form-{i}-id'])
                in_count = Decimal(request.POST[f'form-{i}-in_count'])
                out_count = Decimal(request.POST[f'form-{i}-out_count'])
                obj = obj_dict[obj_pk]
                
                if obj.in_count != in_count or obj.out_count != out_count:
                    obj.in_count = in_count
                    obj.out_count = out_count
                    obj.time_update = time_update
                    obj.is_active = True
                    update_objs.append(obj)

            if update_objs:
                update_fields = [
                    'in_count',
                    'out_count',
                    'time_update',
                    'is_active',
                ]
                CountryDirection.objects.bulk_update(update_objs,
                                              fields=update_fields)
                # self.message_user(request, f"{len(update_objs)} записей успешно обновлено!", messages.SUCCESS)
                self.message_user(request, f'Выбранные направления страны успешно обновлены!({len(update_objs)} шт)', messages.SUCCESS)
            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            return redirect(f"{request.path}?{request.META.get('QUERY_STRING','')}")
            # return super().changelist_view(request, extra_context)

        return super().changelist_view(request, extra_context)
        
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('country',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'country__country',
                                            'country__exchange')

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(city__exchange=account.exchange)

        return queryset
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            if db_field.name == 'country':
                field.queryset = field.queryset.select_related('country')
        else:
            if db_field.name == 'country':
                account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.filter(exchange=account.exchange)\
                                                .select_related('country')
        return field
    
    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_direction_course(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        is_active=True,
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')

    @admin.action(description='Обновить активность выбранных направлений')
    def update_direction_activity(modeladmin, request, queryset):
        time_update = datetime.now()
        queryset.update(is_active=True,
                        time_update=time_update)
        messages.success(request,
                         f'Выбранные направления успешно обновлены!({len(queryset)} шт)')
        

@admin.register(NewCountryDirection)
class NewCountryDirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_direction_course',
        'update_direction_activity'
        )
    list_display = (
        'pk',
        'direction',
        'country',
        'exchange_name',
        'is_active',
        'in_count',
        'out_count',
    )
    list_display_links = ('direction',)
    list_filter = (
        'country__country',
        'country__exchange__name',
        'direction',
        )
    list_editable = (
        'in_count',
        'out_count',
    )
    readonly_fields = (
        'exchange_name',
        'time_update',
    )
    fields = (
        'country',
        'direction',
        # 'course',
        'in_count',
        'out_count',
        # 'saved_partner_course',
        'is_active',
        'time_update',
        )

    def exchange_name(self, obj):
        return obj.country.exchange
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if change:
            update_fields = set()
            if not form.cleaned_data.get('id'):
                for key, value in form.cleaned_data.items():
                    if value != form.initial[key]:
                        update_fields.add(key)
    
                update_field_time_update(obj, update_fields)
                obj.save(update_fields=update_fields)
            else:
                for key in ('in_count', 'out_count'):
                    if form.cleaned_data[key] != form.initial[key]:
                        # update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                if update_fields:
                    update_field_time_update(obj, update_fields)
                    obj.save(update_fields=update_fields)
        else:
            return super().save_model(request, obj, form, change)
        
    # Перехватываю list_editable для оптимизации SELECT запросов в один
    def changelist_view(self, request, extra_context=None):
        # print('from changelist view..')
        if request.method == 'POST' and '_save' in request.POST:
            obj_count = int(request.POST['form-TOTAL_FORMS'])
            pks = [int(request.POST[f'form-{i}-id']) for i in range(obj_count)]
            objs = list(NewCountryDirection.objects.filter(pk__in=pks))  # один SELECT
            obj_dict = {o.pk: o for o in objs}

            time_update = timezone.now()
            update_objs = []

            for i in range(obj_count):
                obj_pk = int(request.POST[f'form-{i}-id'])
                in_count = Decimal(request.POST[f'form-{i}-in_count'])
                out_count = Decimal(request.POST[f'form-{i}-out_count'])
                obj = obj_dict[obj_pk]
                
                if obj.in_count != in_count or obj.out_count != out_count:
                    obj.in_count = in_count
                    obj.out_count = out_count
                    obj.time_update = time_update
                    obj.is_active = True
                    update_objs.append(obj)

            if update_objs:
                update_fields = [
                    'in_count',
                    'out_count',
                    'time_update',
                    'is_active',
                ]
                NewCountryDirection.objects.bulk_update(update_objs,
                                              fields=update_fields)
                # self.message_user(request, f"{len(update_objs)} записей успешно обновлено!", messages.SUCCESS)
                self.message_user(request, f'Выбранные направления страны успешно обновлены!({len(update_objs)} шт)', messages.SUCCESS)
            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            return redirect(f"{request.path}?{request.META.get('QUERY_STRING','')}")
            # return super().changelist_view(request, extra_context)

        return super().changelist_view(request, extra_context)
        
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('country',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to',
                                            'country__country',
                                            'country__exchange')

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(city__exchange=account.exchange)

        return queryset
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            if db_field.name == 'country':
                field.queryset = field.queryset.select_related('country')
        else:
            if db_field.name == 'country':
                account = get_or_set_user_account_cache(request.user)
                field.queryset = field.queryset.filter(exchange=account.exchange)\
                                                .select_related('country')
        return field
    
    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_direction_course(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        is_active=True,
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')

    @admin.action(description='Обновить активность выбранных направлений')
    def update_direction_activity(modeladmin, request, queryset):
        time_update = datetime.now()
        queryset.update(is_active=True,
                        time_update=time_update)
        messages.success(request,
                         f'Выбранные направления успешно обновлены!({len(queryset)} шт)')


# Кастомный фильтр для ExchangeDirection для отпимизации sql запросов ( решение для N+1 prodlem ) 
class CustomDirectionFilter(admin.SimpleListFilter):
    title = 'Direction'
    parameter_name = 'direction'

    def lookups(self, request, model_admin):
        # Используйте select_related для оптимизации запроса
        directions = NoCashDirection.objects.select_related('valute_from',
                                                      'valute_to').distinct()
        return [(d.id, str(d)) for d in directions]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(direction__id=self.value())
        return queryset


@admin.register(NonCashDirection)
class NonCashDirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_direction_course',
        'update_direction_activity'
        )
    list_display = (
        'pk',
        'direction',
        'exchange_name',
        'is_active',
        'in_count',
        'out_count',
    )
    list_display_links = ('direction',)
    list_filter = (
        'exchange',
        CustomDirectionFilter,
        )
    list_editable = (
        'in_count',
        'out_count',
    )
    readonly_fields = (
        'time_update',
    )
    fields = (
        'exchange',
        'direction',
        # 'course',
        'in_count',
        'out_count',
        # 'saved_partner_course',
        'is_active',
        'time_update',
        )
    raw_id_fields = ('direction',)

    def exchange_name(self, obj):
        return obj.exchange.name
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if change:
            update_fields = set()
            if not form.cleaned_data.get('id'):
                for key, value in form.cleaned_data.items():
                    if value != form.initial[key]:
                        update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                obj.save(update_fields=update_fields)
            else:
                for key in ('in_count', 'out_count'):
                    if form.cleaned_data[key] != form.initial[key]:
                        # update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                if update_fields:
                    update_field_time_update(obj, update_fields)
                    obj.save(update_fields=update_fields)
        else:
            return super().save_model(request, obj, form, change)
        
    # Перехватываю list_editable для оптимизации SELECT запросов в один
    def changelist_view(self, request, extra_context=None):
        # print('from changelist view..')
        if request.method == 'POST' and '_save' in request.POST:
            obj_count = int(request.POST['form-TOTAL_FORMS'])
            pks = [int(request.POST[f'form-{i}-id']) for i in range(obj_count)]
            objs = list(NonCashDirection.objects.filter(pk__in=pks))  # один SELECT
            obj_dict = {o.pk: o for o in objs}

            time_update = timezone.now()
            update_objs = []

            for i in range(obj_count):
                obj_pk = int(request.POST[f'form-{i}-id'])
                in_count = Decimal(request.POST[f'form-{i}-in_count'])
                out_count = Decimal(request.POST[f'form-{i}-out_count'])
                obj = obj_dict[obj_pk]
                
                if obj.in_count != in_count or obj.out_count != out_count:
                    obj.in_count = in_count
                    obj.out_count = out_count
                    obj.time_update = time_update
                    obj.is_active = True
                    update_objs.append(obj)

            if update_objs:
                update_fields = [
                    'in_count',
                    'out_count',
                    'time_update',
                    'is_active',
                ]
                NonCashDirection.objects.bulk_update(update_objs,
                                              fields=update_fields)
                # self.message_user(request, f"{len(update_objs)} записей успешно обновлено!", messages.SUCCESS)
                self.message_user(request, f'Выбранные направления страны успешно обновлены!({len(update_objs)} шт)', messages.SUCCESS)
            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            return redirect(f"{request.path}?{request.META.get('QUERY_STRING','')}")
            # return super().changelist_view(request, extra_context)

        return super().changelist_view(request, extra_context)
        
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('exchange',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to')

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(exchange=account.exchange)

        return queryset
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
            # if db_field.name == 'country':
            #     field.queryset = field.queryset.select_related('country')
        else:
            # if db_field.name == 'country':
            #     account = get_or_set_user_account_cache(request.user)
            #     field.queryset = field.queryset.filter(exchange=account.exchange)\
            #                                     .select_related('country')
            pass
        return field
    
    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_direction_course(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        is_active=True,
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')

    @admin.action(description='Обновить активность выбранных направлений')
    def update_direction_activity(modeladmin, request, queryset):
        time_update = datetime.now()
        queryset.update(is_active=True,
                        time_update=time_update)
        messages.success(request,
                         f'Выбранные направления успешно обновлены!({len(queryset)} шт)')


@admin.register(NewNonCashDirection)
class NewNonCashDirectionAdmin(admin.ModelAdmin):
    actions = (
        'update_direction_course',
        'update_direction_activity'
        )
    list_display = (
        'pk',
        'direction',
        'exchange_name',
        'is_active',
        'in_count',
        'out_count',
    )
    list_display_links = ('direction',)
    list_filter = (
        'exchange',
        CustomDirectionFilter,
        )
    list_editable = (
        'in_count',
        'out_count',
    )
    readonly_fields = (
        'time_update',
    )
    fields = (
        'exchange',
        'direction',
        # 'course',
        'in_count',
        'out_count',
        # 'saved_partner_course',
        'is_active',
        'time_update',
        )
    raw_id_fields = ('direction',)

    def exchange_name(self, obj):
        return obj.exchange.name
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if change:
            update_fields = set()
            if not form.cleaned_data.get('id'):
                for key, value in form.cleaned_data.items():
                    if value != form.initial[key]:
                        update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                obj.save(update_fields=update_fields)
            else:
                for key in ('in_count', 'out_count'):
                    if form.cleaned_data[key] != form.initial[key]:
                        # update_field_time_update(obj, update_fields)
                        update_fields.add(key)
                if update_fields:
                    update_field_time_update(obj, update_fields)
                    obj.save(update_fields=update_fields)
        else:
            return super().save_model(request, obj, form, change)
        
    # Перехватываю list_editable для оптимизации SELECT запросов в один
    def changelist_view(self, request, extra_context=None):
        # print('from changelist view..')
        if request.method == 'POST' and '_save' in request.POST:
            obj_count = int(request.POST['form-TOTAL_FORMS'])
            pks = [int(request.POST[f'form-{i}-id']) for i in range(obj_count)]
            objs = list(NewNonCashDirection.objects.filter(pk__in=pks))  # один SELECT
            obj_dict = {o.pk: o for o in objs}

            time_update = timezone.now()
            update_objs = []

            for i in range(obj_count):
                obj_pk = int(request.POST[f'form-{i}-id'])
                in_count = Decimal(request.POST[f'form-{i}-in_count'])
                out_count = Decimal(request.POST[f'form-{i}-out_count'])
                obj = obj_dict[obj_pk]
                
                if obj.in_count != in_count or obj.out_count != out_count:
                    obj.in_count = in_count
                    obj.out_count = out_count
                    obj.time_update = time_update
                    obj.is_active = True
                    update_objs.append(obj)

            if update_objs:
                update_fields = [
                    'in_count',
                    'out_count',
                    'time_update',
                    'is_active',
                ]
                NewNonCashDirection.objects.bulk_update(update_objs,
                                              fields=update_fields)
                # self.message_user(request, f"{len(update_objs)} записей успешно обновлено!", messages.SUCCESS)
                self.message_user(request, f'Выбранные направления страны успешно обновлены!({len(update_objs)} шт)', messages.SUCCESS)
            # for query in connection.queries:
            #     print(query)
            #     print('*' * 8)
            return redirect(f"{request.path}?{request.META.get('QUERY_STRING','')}")
            # return super().changelist_view(request, extra_context)

        return super().changelist_view(request, extra_context)
        
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('exchange',
                                            'direction',
                                            'direction__valute_from',
                                            'direction__valute_to')

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            queryset = queryset.filter(exchange=account.exchange)

        return queryset
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
            # if db_field.name == 'country':
            #     field.queryset = field.queryset.select_related('country')
        else:
            # if db_field.name == 'country':
            #     account = get_or_set_user_account_cache(request.user)
            #     field.queryset = field.queryset.filter(exchange=account.exchange)\
            #                                     .select_related('country')
            pass
        return field
    
    @action_with_form(
        ChangeOrderStatusActionForm,
        description="Обновить курс выбранных направлений",
    )
    def update_direction_course(modeladmin, request, queryset, data):
        time_update = datetime.now()

        queryset.update(in_count=data.get('in_count'),
                        out_count=data.get('out_count'),
                        is_active=True,
                        time_update=time_update)

        modeladmin.message_user(request, f'Выбранные направления успешно обновлены!({len(queryset)} шт)')

    @admin.action(description='Обновить активность выбранных направлений')
    def update_direction_activity(modeladmin, request, queryset):
        time_update = datetime.now()
        queryset.update(is_active=True,
                        time_update=time_update)
        messages.success(request,
                         f'Выбранные направления успешно обновлены!({len(queryset)} шт)')


@admin.register(PartnerCity)
class PartnerCityAdmin(admin.ModelAdmin):
    list_display = (
        'city',
        'exchange',
        )   

    fieldsets = [
        (
            None,
            {
                "fields": ['city',
                           ('has_office',
                            'has_delivery'),
                           'time_update',
                           'min_amount',
                           'max_amount',
                           ],
            },
        ),
        (
            "Будние рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'time_from',
                    'time_to',
                ],
            },
        ),
        (
            "Выходные рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'weekend_time_from',
                    'weekend_time_to',
                ],
            },
        ),
        (
            None,
            {
                "fields": [
                    "working_days",
                           ],
            },
        ),
    ]
    inlines = [
        DirectionStacked,
        ]
    filter_horizontal = (
        'working_days',
        )

    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if not change:
            if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                                  'тест',
                                                                                  'СММ группа')).exists()):
                pass
            else:
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

            # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
            #     account = get_or_set_user_account_cache(request.user)
            #     partner_cities = account.exchange.partner_cities\
            #                                         .filter(city=obj.city)\
            #                                         .all()
            #     make_city_active(obj.city)

            #     if partner_cities:
            #         has_office = obj.has_office
            #         has_delivery = obj.has_delivery
            #         obj = partner_cities.get()
            #         obj.has_office = has_office
            #         obj.has_delivery = has_delivery
            #         change = True
            #     else:
            #         obj.exchange = account.exchange
        return super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            return False
        else:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                return super().has_add_permission(request)
        # return False

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #     account = get_or_set_user_account_cache(request.user)
        #     if account.exchange:
        #         return super().has_add_permission(request)
        # return False
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if db_field.name == 'city':
            field.queryset = field.queryset.order_by('name')

        return field
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('city',
                                            'exchange')
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                queryset = queryset.filter(exchange=account.exchange)
            else:
                # вернуть пустой queryset
                queryset = queryset.filter(id=0)
        return queryset

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #     account = get_or_set_user_account_cache(request.user)
        #     if account.exchange:
        #         queryset = queryset.filter(exchange=account.exchange)
        #     else:
        #         # вернуть пустой queryset
        #         queryset = queryset.filter(id=0)
        # return queryset
    
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
    

@admin.register(NewPartnerCity)
class NewPartnerCityAdmin(admin.ModelAdmin):
    list_display = (
        'city',
        'exchange',
        )   

    fieldsets = [
        (
            None,
            {
                "fields": ['city',
                           ('has_office',
                            'has_delivery'),
                           'time_update',
                           'min_amount',
                           'max_amount',
                           ],
            },
        ),
        (
            "Будние рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'time_from',
                    'time_to',
                ],
            },
        ),
        (
            "Выходные рабочие часы",
            {
                "classes": ["wide"],
                "fields": [
                    'weekend_time_from',
                    'weekend_time_to',
                ],
            },
        ),
        (
            None,
            {
                "fields": [
                    "working_days",
                           ],
            },
        ),
    ]
    inlines = [
        # DirectionStacked,
        ]
    filter_horizontal = (
        'working_days',
        )

    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if not change:
            if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                                  'тест',
                                                                                  'СММ группа')).exists()):
                pass
            else:
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

            # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
            #     account = get_or_set_user_account_cache(request.user)
            #     partner_cities = account.exchange.partner_cities\
            #                                         .filter(city=obj.city)\
            #                                         .all()
            #     make_city_active(obj.city)

            #     if partner_cities:
            #         has_office = obj.has_office
            #         has_delivery = obj.has_delivery
            #         obj = partner_cities.get()
            #         obj.has_office = has_office
            #         obj.has_delivery = has_delivery
            #         change = True
            #     else:
            #         obj.exchange = account.exchange
        return super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request: HttpRequest) -> bool:
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            return False
        else:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                return super().has_add_permission(request)
        # return False

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #     account = get_or_set_user_account_cache(request.user)
        #     if account.exchange:
        #         return super().has_add_permission(request)
        # return False
    
    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        
        if db_field.name == 'city':
            field.queryset = field.queryset.order_by('name')

        return field
    
    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)\
                            .select_related('city',
                                            'exchange')
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                queryset = queryset.filter(exchange=account.exchange)
            else:
                # вернуть пустой queryset
                queryset = queryset.filter(id=0)
        return queryset

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #     account = get_or_set_user_account_cache(request.user)
        #     if account.exchange:
        #         queryset = queryset.filter(exchange=account.exchange)
        #     else:
        #         # вернуть пустой queryset
        #         queryset = queryset.filter(id=0)
        # return queryset
    
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


# @admin.register(Comment)
class CommentAdmin(BaseCommentAdmin):
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
                pass
        else:
            account = get_or_set_user_account_cache(request.user)
            if account.exchange:
                queryset = queryset\
                                .select_related('review')\
                                .filter(review__in=account.exchange.reviews.all())
            else:
                queryset = queryset.filter(status='На ожидании')
        return queryset


        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #         account = get_or_set_user_account_cache(request.user)
        #         if account.exchange:
        #             queryset = queryset\
        #                             .select_related('review')\
        #                             .filter(review__in=account.exchange.reviews.all())
        #         else:
        #             queryset = queryset.filter(status='На ожидании')
        # return queryset


#Отображение комментариев на странице связанного отзыва
# class CommentStacked(BaseCommentStacked):
#     model = Comment

#     def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
#         return super().get_queryset(request).select_related('review')


# #Отображение комментариев администрации на странице связанного отзыва
# class AdminCommentStacked(BaseAdminCommentStacked):
#     model = AdminComment


#Отображение отзывов в админ панели
# @admin.register(Review)
# class ReviewAdmin(BaseReviewAdmin):
#     inlines = [
#         CommentStacked,
#         AdminCommentStacked,
#         ]

#     def has_add_permission(self, request: HttpRequest) -> bool:
#         if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
#                                                                               'тест',
#                                                                               'СММ группа')).exists()):
#             return super().has_add_permission(request)
#         else:
#             return False

#         # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
#         #         return False
#         # return super().has_add_permission(request)

#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)

#         if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
#                                                                               'тест',
#                                                                               'СММ группа')).exists()):
#             pass
#         else:
#             account = get_or_set_user_account_cache(request.user)
#             if account.exchange:
#                 queryset = queryset.select_related('exchange')\
#                                     .filter(exchange=account.exchange)
#             else:
#                 queryset = queryset.filter(status='На ожидании')
#         return queryset

#         # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
#         #         account = get_or_set_user_account_cache(request.user)
#         #         if account.exchange:
#         #             queryset = queryset.select_related('exchange')\
#         #                                 .filter(exchange=account.exchange)
#         #         else:
#         #             queryset = queryset.filter(status='На ожидании')
#         # return queryset


# #Отображение отзывов на странице связанного обменника
# class ReviewStacked(BaseReviewStacked):
#     model = Review

#     def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
#         return super().get_queryset(request)\
#                         .select_related('exchange',
#                                         'exchange__account')


# class ExchangeLinkCountStacked(BaseExchangeLinkCountStacked):
#     model = ExchangeLinkCount


@admin.register(Exchange)
class ExchangeAdmin(ReviewAdminMixin, admin.ModelAdmin):
    list_display = (
        'pk',
        'name',
        'en_name',
        'account',
        'is_available',
        'active_status',
        'time_create',
        'time_disable',
        'high_aml',
        )
    list_editable = (
        'high_aml',
    )
    list_display_links = ('name',)
    # readonly_fields = (
    #     'is_available',
    #     )
    list_filter = (
        'name',
    )
    search_fields = (
        'name',
    )
    exclude = (
        'course_count',
        'is_active',
    )
    filter_horizontal = ()

    inlines = [
        PartnerCityStacked,
        # ReviewStacked,
        # ExchangeLinkCountStacked,
        ]

    def is_available(self, obj=None):
        return bool(obj.partner_link and obj.is_active)
    
    is_available.boolean = True
    is_available.short_description = 'Активен'

    def link_count(self, obj):
        # print(obj.__dict__)
        # print(len(connection.queries))

        # link_count = 0
        
        # if obj.count:
        #     link_count += obj.count

        # if obj.country_link_count:
        #     link_count += obj.country_link_count
        return obj.link_count

    def country_link_count(self, obj):
    #     print(len(connection.queries))

    #     # print(obj.__dict__)
    #     # link_count = 0
        
    #     # if obj.count:
    #     #     link_count += obj.count

    #     # if obj.country_link_count:
    #     #     link_count += obj.country_link_count
    #     # # return obj.link_count
    #     # return 1
    #     _count = obj.exchange_country_counts.aggregate(Sum('count')).get('count__sum') or 0
    #     print(len(connection.queries))
    #     print(connection.queries)

        return obj.country_link_count
    
    def get_total_direction_count(self, obj):
        return obj.city_direction_count + obj.country_direction_count
    
    link_count.short_description = 'Счетчик перехода по ссылке'

    country_link_count.short_description = 'Счетчик перехода по ссылке (страны)'

    get_total_direction_count.short_description = 'Кол-во активных направлений'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            readonly_fields = ('time_create', 'get_total_direction_count', ) + readonly_fields
        else:
            readonly_fields = ('partner_link', 'time_create', 'get_total_direction_count',) + readonly_fields

        return readonly_fields + ('link_count', 'country_link_count', 'is_available')

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        # print(len(connection.queries))

        city_direction_count_subquery = Direction.objects.select_related(
            'city',
            'city__exchange',
        ).filter(
            city__exchange__pk=OuterRef('id'),
            is_active=True,
        ).values('city__exchange__pk').annotate(
            direction_count=Coalesce(Count('id'), Value(0))
        ).values('direction_count')

        country_direction_count_subquery = CountryDirection.objects.select_related(
            'country',
            'country__exchange',
        ).filter(
            country__exchange__pk=OuterRef('id'),
            is_active=True,
        ).values('country__exchange__pk').annotate(
            direction_count=Coalesce(Count('id'), Value(0))
        ).values('direction_count')

        # return exchange_list.annotate(city_direction_count=city_direction_count_subquery,
        #                             country_direction_count=country_direction_count_subquery,
        #                             direction_count=Coalesce(F('city_direction_count'), Value(0))+Coalesce(F('country_direction_count'), Value(0)))

        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            queryset = super().get_queryset(request)\
                            .select_related('account', 'account__user')
        else:
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
        # else:
        #     queryset = super().get_queryset(request)\
        #                     .select_related('account', 'account__user')
        
        # queryset = queryset.prefetch_related('exchange_counts',
        #                                  'exchange_country_counts')
        # print(queryset)
        # print(len(connection.queries))
        link_count_subquery = ExchangeLinkCount.objects.filter(
            exchange_id=OuterRef('id')
        ).values('exchange_id').annotate(
            total_count=Coalesce(Sum('count'), Value(0))
        ).values('total_count')

        country_link_count_subquery = CountryExchangeLinkCount.objects.filter(
            exchange_id=OuterRef('id')
        ).values('exchange_id').annotate(
            total_count=Coalesce(Sum('count'), Value(0))
        ).values('total_count')

        # return queryset.annotate(link_count=Sum('exchange_counts__count'))\
        #                 .annotate(country_link_count=Sum('exchange_country_counts__count'))
        return queryset.annotate(link_count=Coalesce(Subquery(link_count_subquery), Value(0)),
                                 country_link_count=Coalesce(Subquery(country_link_count_subquery), Value(0)),
                                 city_direction_count=Coalesce(Subquery(city_direction_count_subquery), Value(0)),
                                 country_direction_count=Coalesce(Subquery(country_direction_count_subquery), Value(0)))
                        # .annotate(link_count=ExpressionWrapper(F('count') + F('country_link_count'),
                        #                                        output_field=IntegerField()))

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #         account = get_or_set_user_account_cache(request.user)
        #         exchange = account.exchange
                
        #         if not exchange:
        #             # вернуть пустой queryset
        #             queryset = super().get_queryset(request)\
        #                             .filter(name='Не выбрано!!!')
        #         # вернуть обменник партнёра
        #         else:
        #             queryset = super().get_queryset(request)\
        #                             .select_related('account',
        #                                             'account__user',
        #                                             'account__exchange')\
        #                             .filter(name=exchange.name)
        # # вернуть все партнёрские обменники
        # else:
        #     queryset = super().get_queryset(request)\
        #                     .select_related('account', 'account__user')
        
        # return queryset.annotate(link_count=Sum('exchange_counts__count'))
    
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
        perms = super().has_add_permission(request)
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            pass
        else:
            account = get_or_set_user_account_cache(request.user)

            if account.exchange:
                return False
        return perms

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groups.all()):
        #     account = get_or_set_user_account_cache(request.user)

        #     if account.exchange:
        #         return False
        # return super().has_add_permission(request)
    
    def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
        if request.user.is_superuser or (request.user.groups.filter(name__in=('Модераторы',
                                                                              'тест',
                                                                              'СММ группа')).exists()):
            if obj.active_status in ('disabled', 'scam', 'skip'):
                obj.is_active = False

            elif obj.active_status == 'active':
                obj.is_active = True

            if obj.active_status == 'disabled':
                if obj.time_disable is None:
                    obj.time_disable = timezone.now()
            else:
                obj.time_disable = None

            return super().save_model(request, obj, form, change)
        else:
            if not change:
                account = get_or_set_user_account_cache(request.user)
                account.exchange = obj
                super().save_model(request, obj, form, change)
                account.save()
                set_user_account_cache(account)
        # else:
        #     return super().save_model(request, obj, form, change)

        # if not request.user.is_superuser or (not 'Модераторы' in request.user.groupse.all()):
        #     if not change:
        #         account = get_or_set_user_account_cache(request.user)
        #         account.exchange = obj
        #         super().save_model(request, obj, form, change)
        #         account.save()
        #         set_user_account_cache(account)
        # else:
        #     return super().save_model(request, obj, form, change)

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
    def get_queryset(self, request):
        return super().get_queryset(request)\
                                    .select_related('exchange',
                                                    'user',
                                                    'exchange_direction',
                                                    'exchange_direction__city')
    pass


@admin.register(NewExchangeLinkCount)
class NewExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request)\
                                    .select_related('exchange',
                                                    'user',
                                                    'exchange_direction',
                                                    'exchange_direction__city')
    pass


@admin.register(CountryExchangeLinkCount)
class CountryExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request)\
                                    .select_related('exchange',
                                                    'user',
                                                    'exchange_direction',
                                                    'exchange_direction__country')
    pass


@admin.register(NewCountryExchangeLinkCount)
class NewCountryExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request)\
                                    .select_related('exchange',
                                                    'user',
                                                    'exchange_direction',
                                                    'exchange_direction__country')
    pass


@admin.register(NonCashExchangeLinkCount)
class NonCashExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request)\
                                    .select_related('exchange',
                                                    'user',
                                                    'exchange_direction',
                                                    'exchange_direction')
    pass


@admin.register(NewNonCashExchangeLinkCount)
class NewNonCashExchangeListCountAdmin(BaseExchangeLinkCountAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request)\
                                    .select_related('exchange',
                                                    'user',
                                                    'exchange_direction',
                                                    'exchange_direction')
    pass


@admin.register(DirectionRate)
class DirectionRateAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'exchange',
        'exchange_direction',
        'min_rate_limit',
    )

    raw_id_fields = ('exchange', 'exchange_direction')


@admin.register(NewDirectionRate)
class NewDirectionRateAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'exchange',
        'exchange_direction',
        'min_rate_limit',
    )

    raw_id_fields = ('exchange', 'exchange_direction')


@admin.register(CountryDirectionRate)
class CountryDirectionRateAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'exchange',
        'exchange_direction',
        'min_rate_limit',
    )

    raw_id_fields = ('exchange', 'exchange_direction')


@admin.register(NewCountryDirectionRate)
class NewCountryDirectionRateAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'exchange',
        'exchange_direction',
        'min_rate_limit',
    )

    raw_id_fields = ('exchange', 'exchange_direction')


@admin.register(NonCashDirectionRate)
class NonCashDirectionRateRateAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'exchange',
        'exchange_direction',
        'min_rate_limit',
    )

    raw_id_fields = ('exchange', 'exchange_direction')


@admin.register(NewNonCashDirectionRate)
class NewNonCashDirectionRateRateAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'exchange',
        'exchange_direction',
        'min_rate_limit',
    )

    raw_id_fields = ('exchange', 'exchange_direction')


#Отображение банкоматов в админ панели
@admin.register(Bankomat)
class BankomatAdmin(admin.ModelAdmin):
    list_display = (
        'name',
    )

    filter_horizontal = (
        'valutes',
    )


@admin.register(NewBankomat)
class NewBankomatAdmin(admin.ModelAdmin):
    list_display = (
        'name',
    )

    filter_horizontal = (
        'valutes',
    )
#Отображение банкоматов в админ панели
# @admin.register(DirectionRate)
# class DirectionRateAdmin(admin.ModelAdmin):
#     list_display = (
#         'exchange',
#         'direction_id',
#         'direction_marker',
#         'min_limit_count',
#     )

    # filter_horizontal = (
    #     'valutes',
    # )
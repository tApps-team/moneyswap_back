from typing import Any

from django.contrib import admin
admin.filters.SimpleListFilter
from general_models.models import BaseExchange, Guest


class ReviewAdminMixin:
        def save_model(self, request: Any, obj: Any, form: Any, change: Any) -> None:
            if not isinstance(obj, BaseExchange):
                obj.moderation = obj.status == 'Опубликован'
            return super().save_model(request, obj, form, change)
        
        def save_formset(self, request: Any, form: Any, formset: Any, change: Any) -> None:
            instances = formset.save(commit=False)
            for instance in instances:
                if hasattr(instance, 'moderation'):
                    instance.moderation = instance.status == 'Опубликован'
                    instance.save()
            return super().save_formset(request, form, formset, change)
        


class DateTimeRangeFilter(admin.SimpleListFilter):
    title = 'Кастомный фильтр UTM'
    parameter_name = 'custom_utm'

    def lookups(self, request, model_admin):
        return (
            ('direct_ar_251224', 'direct_ar_251224'),
            ('direct_indonesia_281224', 'direct_indonesia_281224'),
            ('direct_th_261224', 'direct_th_261224'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'direct_ar_251224':
            # start_date = timezone.now() - timedelta(days=7)
            return queryset.filter(utm_source__startswith='direct_ar_251224')
        if self.value() == 'direct_indonesia_281224':
            # start_date = timezone.now() - timedelta(days=30)
            return queryset.filter(utm_source__startswith='direct_indonesia_281224')
        if self.value() == 'direct_th_261224':
            # start_date = timezone.now().replace(day=1)
            return queryset.filter(utm_source__startswith='direct_th_261224')
        return queryset
    

class UTMSourceFilter(admin.filters.SimpleListFilter):
    title = 'Кастомный UTM фильтр'
    parameter_name = 'utm_source_start'

    def lookups(self, request, model_admin):
        # Получаем уникальные значения начала строки
        # utm_source_start = request.GET.get('utm_source_start')
        # print('lookup',request.GET)
        # if not utm_source_start:
        utm_source = self.value()
        # print(utm_source)
        if not utm_source:
            prefixes = Guest.objects.filter(utm_source__isnull=False)\
                                    .values_list('utm_source', flat=True)\
                                    .distinct()

            unique_prefix =  [('_'.join(prefix.split('_')[:2]), '_'.join(prefix.split('_')[:2])) \
                                for prefix in set(prefixes) if prefix is not None]
            
            return sorted(set(unique_prefix))


            # return [('_'.join(prefix.split('_')[:2]), '_'.join(prefix.split('_')[:2])) \
            #         for prefix in set(prefixes) if prefix is not None]
        else:
            check_value = (utm_source[:2].isdigit()) or (utm_source == '--')
            
            if not check_value:
                prefixes = Guest.objects.filter(utm_source__isnull=False,
                                                utm_source__startswith=utm_source)\
                                        .values_list('utm_source', flat=True)\
                                        .distinct()
                
                unique_prefix = [('_'.join(prefix.split('_')[2:]), '_'.join(prefix.split('_')[2:])) \
                                 for prefix in set(prefixes) if prefix is not None]
                
                return sorted(set(unique_prefix))

                # return [('_'.join(prefix.split('_')[2:]), '_'.join(prefix.split('_')[2:])) \
                #         for prefix in set(prefixes) if prefix is not None]
            else:
                return [('--', '--')]
        # return [(prefix, prefix) for prefix in set(prefixes) if prefix is not None]


    def queryset(self, request, queryset):
        # print(request.GET)
        # utm_source_start = request.GET.get('utm_source_start')
        utm_source = self.value()
        # print(utm_source)
        # print(22)
        if utm_source:
        #     # if not utm_source_start:
            check_value = utm_source[:2].isdigit()
            
            if not check_value:
                queryset = queryset.filter(utm_source__startswith=utm_source,
                                           utm_source__isnull=False)
            else:
                queryset = queryset.filter(utm_source__endswith=utm_source,
                                           utm_source__isnull=False)

                # utm_source_start = utm_source_start[0]
                # queryset = queryset.filter(utm_source__startswith=utm_source_start)
        # print(queryset)
        return queryset


# class UTMSourceSecondPartFilter(admin.SimpleListFilter):
#     title = 'Вторая часть UTM Source'
#     parameter_name = 'utm_source_second_part'

#     def lookups(self, request, model_admin):
#         print('lookup',request.GET)
#         # Получаем уникальные значения начала строки
#         prefixes = Guest.objects.values_list('utm_source', flat=True).distinct()
#         return [(prefix, prefix) for prefix in set(prefixes) if prefix is not None]

#     def queryset(self, request, queryset):

#         print(request.GET)
#         if self.value():
#             return queryset.filter(umt_source__isnull=False,
#                                    utm_source__endswith=self.value()).distinct()
#         return queryset

# @admin.register(YourModel)
# class YourModelAdmin(admin.ModelAdmin):
#     list_filter = (UTMSourceFilter, UTMSourceSecondPartFilter)
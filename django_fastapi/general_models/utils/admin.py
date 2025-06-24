from typing import Any
from datetime import datetime

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
                    
                    if hasattr(instance, 'time_create'):
                        instance.time_create = datetime.now() if instance.time_create is None else instance.time_create
                    
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
        request_session = request.session

        # Получаем уникальные значения начала строки
        print('lookup',request.GET)
        print('request session', request_session.__dict__)

        if request_session.get('prefix_utm') and \
            request_session.get('second_part_utm'):
            print('22')

        utm_source = self.value()
        print(utm_source)
        if not utm_source:
            prefixes = Guest.objects.filter(utm_source__isnull=False)\
                                    .values_list('utm_source', flat=True)\
                                    .distinct()

            unique_prefix =  [('_'.join(prefix.split('_')[:2]), '_'.join(prefix.split('_')[:2])) \
                                for prefix in set(prefixes) if prefix is not None]
            
            request_session['prefix_utm'] = None
            request_session['second_part_utm'] = None

            return sorted(set(unique_prefix))

        else:
            if utm_source[:2].isdigit():
                prefix_utm = request_session.get('prefix_utm')
                prefixes = Guest.objects.filter(utm_source__isnull=False,
                                                utm_source__endswith=utm_source,
                                                utm_source__startswith=prefix_utm)\
                                        .values_list('utm_source', flat=True)\
                                        .distinct()
                
                request.session['second_part_utm'] = utm_source

            check_value = (utm_source[:2].isdigit()) or (utm_source == '--')
            
            if not check_value:
                prefixes = Guest.objects.filter(utm_source__isnull=False,
                                                utm_source__startswith=utm_source)\
                                        .values_list('utm_source', flat=True)\
                                        .distinct()
                
                unique_prefix = [('_'.join(prefix.split('_')[2:]), '_'.join(prefix.split('_')[2:])) \
                                 for prefix in set(prefixes) if prefix is not None]
                
                request.session['prefix_utm'] = utm_source

                if not unique_prefix:
                    return [('--', '--')]
                
                return sorted(set(unique_prefix))

            else:
                return [('--', '--')]


    def queryset(self, request, queryset):
        request_session = request.session
        
        print('q',request.GET)
        print('q','request session', request_session.__dict__)
        print('q',self.value())
        utm_source = self.value()
        if utm_source:
            check_value = utm_source[:2].isdigit()
            
            if not check_value:
                queryset = queryset.filter(utm_source__startswith=utm_source,
                                           utm_source__isnull=False)
            else:
                prefix_utm = request_session.get('prefix_utm')
                if prefix_utm:
                    queryset = queryset.filter(utm_source__startswith=prefix_utm,
                                            utm_source__endswith=utm_source,
                                            utm_source__isnull=False)
                    
        return queryset


class NewUTMSourceFilter(admin.filters.SimpleListFilter):
    title = 'Кастомный UTM фильтр'
    parameter_name = 'utm_source_start'

    def lookups(self, request, model_admin):
        request_session = request.session

        # Получаем уникальные значения начала строки
        print('lookup',request.GET)
        print('request session', request_session.__dict__)

        if request_session.get('prefix_utm') and \
            request_session.get('second_part_utm'):
            print('both active')

        utm_source = self.value()
        print(utm_source)
        if not utm_source:
            prefixes = Guest.objects.filter(utm_source__isnull=False)\
                                    .values_list('utm_source', flat=True)\
                                    .distinct()

            unique_prefix =  [('_'.join(prefix.split('_')[:2]), '_'.join(prefix.split('_')[:2])) \
                                for prefix in set(prefixes) if prefix is not None]
            
            unique_prefix = [('Без UTM метки', 'Без UTM метки'), ] + unique_prefix
            
            request_session['prefix_utm'] = None
            request_session['second_part_utm'] = None

            return sorted(set(unique_prefix))

        else:
            prefix_utm = request_session.get('prefix_utm')

            if not prefix_utm:
                prefixes = Guest.objects.filter(utm_source__isnull=False,
                                                utm_source__startswith=utm_source)\
                                        .values_list('utm_source', flat=True)\
                                        .distinct()

                
                request.session['prefix_utm'] = utm_source

            else:
                prefixes = Guest.objects.filter(utm_source__isnull=False,
                                                utm_source__endswith=utm_source,
                                                utm_source__startswith=prefix_utm)\
                                        .values_list('utm_source', flat=True)\
                                        .distinct()
                request.session['second_part_utm'] = utm_source
            
            unique_prefix = [('_'.join(prefix.split('_')[2:]), '_'.join(prefix.split('_')[2:])) \
                                for prefix in set(prefixes) if prefix is not None]
            
            if not unique_prefix:
                return [('--', '--')]
            
            return sorted(set(unique_prefix))


    def queryset(self, request, queryset):
        request_session = request.session
        
        # print('q',request.GET)
        # print('q','request session', request_session.__dict__)
        # print('q',self.value())
        utm_source = self.value()
        if utm_source:
            prefix_utm = request_session.get('prefix_utm')
            second_part_utm = request_session.get('second_part_utm')
            
            if prefix_utm:
                if prefix_utm == 'Без UTM метки':
                    queryset = queryset.filter(utm_source__isnull=True)
                    request.session['prefix_utm'] = None
                    return queryset
                
                if not second_part_utm:
                    queryset = queryset.filter(utm_source__startswith=prefix_utm,
                                                utm_source__isnull=False)
                else:
                    queryset = queryset.filter(utm_source__startswith=prefix_utm,
                                            utm_source__endswith=utm_source,
                                            utm_source__isnull=False)
                    
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
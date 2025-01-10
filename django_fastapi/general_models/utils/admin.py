from typing import Any

from django.contrib import admin

from general_models.models import BaseExchange


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
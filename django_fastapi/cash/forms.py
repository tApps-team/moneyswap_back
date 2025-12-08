# # app/forms.py
# from django import forms
# from django.contrib.admin.widgets import AutocompleteSelect, AutocompleteSelectMultiple
from django.contrib.admin.widgets import FilteredSelectMultiple
# FilteredSelectMultiple


# from general_models.models import NewValute

# from .models import NewDirection



# class DirectionsBulkCreateForm(forms.Form):
#     valute_from = forms.ModelChoiceField(
#         queryset=NewValute.objects.all(),
#         label="Валюта FROM"
#     )

#     valute_to = forms.ModelMultipleChoiceField(
#         queryset=NewValute.objects.all(),
#         label="Валюты TO",
#         widget=FilteredSelectMultiple(
#             verbose_name="Валюты TO",
#             is_stacked=False,
#             # attrs={"class": "selectfilter"}  # <- здесь важно!
#         )
#     )

#     class Media:
#         css = {
#             "all": ("admin/css/widgets.css",)
#         }
#         js = (
#             "admin/js/core.js",
#             "admin/js/jquery.init.js",
#             "admin/js/SelectBox.js",
#             "admin/js/SelectFilter2.js",
#         )

from django import forms
# from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import NewValute

from django_select2.forms import Select2Widget, Select2MultipleWidget, Select2AdminMixin
from django.contrib.admin.widgets import FilteredSelectMultiple, ManyToManyRawIdWidget

class BulkDirectionForm(forms.Form):
    valute_from = forms.ModelChoiceField(
        queryset=NewValute.objects.all(),
        label="Отдаём",
        # widget=forms.Select  # поиск + красивый select
        widget=Select2Widget(
            attrs={
                "data-theme": "classic",   # или "classic"
            }
        )  # поиск + красивый select

    )

    valute_to = forms.ModelMultipleChoiceField(
        queryset=NewValute.objects.all(),
        label="Получаем",
        widget=forms.CheckboxSelectMultiple  # множественный select с поиском
        # widget=ManyToManyRawIdWidget,  # множественный select с поиском
        # widget=FilteredSelectMultiple(verbose_name="Получаем", is_stacked=False),

    )

    # Переопределяем метод __init__ для valute_to
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # здесь мы задаём, как будет отображаться каждая запись
        self.fields['valute_to'].label_from_instance = lambda obj: f"{obj.name} ({obj.code_name})"

    class Media:
        css = {
            'all': ('admin/css/widgets.css',),
        }
        js = ('admin/js/core.js', 'admin/js/SelectFilter2.js')
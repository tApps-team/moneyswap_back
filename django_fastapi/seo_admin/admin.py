from collections.abc import Callable, Sequence
from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from django_summernote.admin import SummernoteModelAdmin

from general_models.models import MassSendMessage, MassSendImage, MassSendVideo, MassSendFile
from general_models.utils.endpoints import try_generate_icon_url

from .models import SimplePage, FAQCategory, FAQPage


@admin.register(SimplePage)
class SimplePageAdmin(SummernoteModelAdmin):
    summernote_fields = ('upper_content', 'lower_content', )


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(FAQPage)
class FAQPageAdmin(SummernoteModelAdmin):
    list_display = ('question', )
    summernote_fields = ('answer', )


class MassSendImageStacked(admin.StackedInline):
    model = MassSendImage
    extra = 0
    classes = [
        'collapse',
        ]
    readonly_fields = ('image_icon', 'file_id')
    
    def image_icon(self, obj):
        icon_url = try_generate_icon_url(obj)
        icon_url = f'http://localhost:8000/django{obj.image.url}'
        return mark_safe(f"<img src='{icon_url}' width=40")
    
    image_icon.short_description = 'Изображение'
    

class MassSendVideoStacked(admin.StackedInline):
    model = MassSendVideo
    extra = 0
    classes = [
        'collapse',
        ]
    readonly_fields = ('file_id', )


class MassSendFileStacked(admin.StackedInline):
    model = MassSendFile
    extra = 0
    classes = [
        'collapse',
        ]
    readonly_fields = ('file_id', )




@admin.register(MassSendMessage)
class MassSendMessageAdmin(SummernoteModelAdmin):
    summernote_fields = ('content', )
    inlines = [
        MassSendImageStacked,
        MassSendVideoStacked,
        MassSendFileStacked,
    ]
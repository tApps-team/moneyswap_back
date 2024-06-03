from django.contrib import admin

from django_summernote.admin import SummernoteModelAdmin

from general_models.models import MassSendMessage, MassSendImage, MassSendVideo

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
    

class MassSendVideoStacked(admin.StackedInline):
    model = MassSendVideo
    extra = 0
    classes = [
        'collapse',
        ]


@admin.register(MassSendMessage)
class MassSendMessageAdmin(SummernoteModelAdmin):
    summernote_fields = ('content', )
    inlines = [
        MassSendImageStacked,
        MassSendVideoStacked,
    ]
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from cosinnus_marketplace.models import Offer, OfferCategory, OfferCategoryGroup
from cosinnus.admin import BaseTaggableAdmin


class OfferAdmin(BaseTaggableAdmin):
    list_display = BaseTaggableAdmin.list_display + ['is_active', 'type',]
    list_filter = BaseTaggableAdmin.list_filter + ['is_active', 'type',]

admin.site.register(Offer, OfferAdmin)


class OfferCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk', 'category_group')

admin.site.register(OfferCategory, OfferCategoryAdmin)


class OfferCategoryGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_en', 'name_ru', 'name_uk', 'order_key')

admin.site.register(OfferCategoryGroup, OfferCategoryGroupAdmin)

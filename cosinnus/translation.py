# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _


from wagtail_modeltranslation.translator import TranslationOptions
from wagtail_modeltranslation.decorators import register
from models.wagtail_models import DashboardTripleColumnPage, DashboardSingleColumnPage,\
    DashboardDoubleColumnPage, SimpleOnePage, SimpleTwoPage, PortalRootPage


@register(PortalRootPage)
class PortalRootPageTR(TranslationOptions):
    fields = PortalRootPage.translation_fields

@register(DashboardSingleColumnPage)
class DashboardSingleColumnPageTR(TranslationOptions):
    fields = DashboardSingleColumnPage.translation_fields
    
@register(DashboardDoubleColumnPage)
class DashboardDoubleColumnPageTR(TranslationOptions):
    fields = DashboardDoubleColumnPage.translation_fields

@register(DashboardTripleColumnPage)
class DashboardTripleColumnPageTR(TranslationOptions):
    fields = DashboardTripleColumnPage.translation_fields

@register(SimpleOnePage)
class SimpleOnePageTR(TranslationOptions):
    fields = SimpleOnePage.translation_fields
    
@register(SimpleTwoPage)
class SimpleTwoPageTR(TranslationOptions):
    fields = SimpleTwoPage.translation_fields

    
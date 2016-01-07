# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from wagtail.wagtailimages.formats import Format, register_image_format

register_image_format(Format('cosinnus_format_tiny', _('Tiny (50 x *)'), 'richtext-image richtext-image-tiny', 'width-50'))
register_image_format(Format('cosinnus_format_very_small', _('Very Small (100 x *)'), 'richtext-image richtext-image-very-small', 'width-100'))
register_image_format(Format('cosinnus_format_smaller', _('Smaller (150 x *)'), 'richtext-image richtext-image-smaller', 'width-150'))
register_image_format(Format('cosinnus_format_small', _('Small (200 x *)'), 'richtext-image richtext-image-small', 'width-200'))
register_image_format(Format('cosinnus_format_mediumer', _('Medium-small (250 x *)'), 'richtext-image richtext-image-mediumer', 'width-250'))
register_image_format(Format('cosinnus_format_medium', _('Medium (300 x *)'), 'richtext-image richtext-image-medium', 'width-300'))
register_image_format(Format('cosinnus_format_large', _('Large (400 x *)'), 'richtext-image richtext-image-large', 'width-400'))
register_image_format(Format('cosinnus_format_larger', _('Larger (500 x *)'), 'richtext-image richtext-image-larger', 'width-500'))
register_image_format(Format('cosinnus_format_very_large', _('Very large (650 x *)'), 'richtext-image richtext-image-very-large', 'width-650'))
register_image_format(Format('cosinnus_format_extra_large', _('Extra large (800 x *)'), 'richtext-image richtext-image-extra-large', 'width-800'))
register_image_format(Format('cosinnus_format_xxl', _('XXL (1200 x *)'), 'richtext-image richtext-image-xxl', 'width-1200'))


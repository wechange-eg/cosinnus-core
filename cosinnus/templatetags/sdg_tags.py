import json

from django import template
from django.utils.safestring import mark_safe

from cosinnus.models.group import SDG_CHOICES

register = template.Library()


@register.simple_tag
def get_sdg_image(lang, sdg):
    languages_available = ['de', 'en', 'ru', 'fr', 'es']
    if lang not in languages_available:
        lang = 'en'
    return 'images/sdgs/{}_{}.png'.format(lang, str(sdg))


@register.simple_tag(takes_context=True)
def render_sdg_json(context):
    request = context['request']
    lang = request.LANGUAGE_CODE
    sgd_json = []
    for sdg in SDG_CHOICES:
        sgd_json.append(
            {'id': sdg[0],
             'icon': '/static/{}'.format(get_sdg_image(lang, sdg[0])),
             'name': str(sdg[1])
             }
        )
    return mark_safe(json.dumps(sgd_json))

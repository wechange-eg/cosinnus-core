from django import template

register = template.Library()


@register.simple_tag
def get_sdg_image(lang, sdg):
    languages_available = ['de', 'en', 'ru', 'fr', 'es']
    if lang not in languages_available:
        lang = 'en'
    return 'images/sdgs/{}_{}.png'.format(lang, str(sdg))

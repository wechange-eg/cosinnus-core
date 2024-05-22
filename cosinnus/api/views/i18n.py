from django.http import JsonResponse
from django.utils.translation import get_language
from django.views.i18n import JSONCatalog


class Translations(JSONCatalog):
    """Return locale and json catalog"""

    domain = 'djangojs'

    def render_to_response(self, context, **response_kwargs):
        context['locale'] = get_language()

        return JsonResponse(context)


translations = Translations.as_view()

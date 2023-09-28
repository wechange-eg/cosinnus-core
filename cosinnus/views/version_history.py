from django.views.generic.base import TemplateView
from cosinnus.utils.version_history import get_version_history


class VersionHistoryView(TemplateView):
    """ Detailed overview over all version of the version history. """
    template_name = 'cosinnus/version_history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'version_history': get_version_history(),
        })
        return context


version_history = VersionHistoryView.as_view()

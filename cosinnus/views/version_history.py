from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic.base import TemplateView, View

from cosinnus.utils.version_history import get_version_history, mark_version_history_as_read


class VersionHistoryView(TemplateView):
    """Detailed overview over all version of the version history."""

    template_name = 'cosinnus/version_history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'version_history': get_version_history(),
            }
        )
        return context


class VersionHistoryMarkSeenView(LoginRequiredMixin, View):
    """API view for the v2 navbar setting marking the version history as read."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        mark_version_history_as_read(request.user)
        return HttpResponse(status=200)


version_history = VersionHistoryView.as_view()
version_history_mark_read = VersionHistoryMarkSeenView.as_view()

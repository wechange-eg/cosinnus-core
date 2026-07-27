from django.urls import reverse_lazy

from cosinnus.conf import settings
from cosinnus_note.api_frontend.serializers import CosinnusNoteSerializer
from cosinnus_note.models import Note


class CosinnusPersonalDashboardWidget:
    """Personal dashboard widget instance, as used by the personal dashboard API."""

    # widget id
    id = None
    # cosinnus app
    cosinnus_app = None
    # function to get the data for a user
    user_queryset_function = None
    # data serializer class
    serializer_class = None
    # widget api
    api_url = None
    # conf settings
    conf = None

    # profile settings key
    PROFILE_SETTINGS_KEY = 'dashboard_widgets'

    # limit of preloaded widget data
    DATA_LIMIT = 3

    def __init__(self, conf=None):
        self.conf = conf

    def _get_widget_settings(self, profile):
        """Helper to get the user widget settings from the profile settings."""
        return profile.settings.get(self.PROFILE_SETTINGS_KEY, {}).get(self.id, {})

    def _set_widget_setting(self, profile, setting, value):
        """Helper to set the user widget settings to the profile settings."""
        widget_settings = profile.settings.get(self.PROFILE_SETTINGS_KEY, {})
        if self.id not in widget_settings:
            widget_settings[self.id] = {}
        widget_settings[self.id][setting] = value
        profile.settings[self.PROFILE_SETTINGS_KEY] = widget_settings
        type(profile).objects.filter(pk=profile.pk).update(settings=profile.settings)

    def is_enabled(self, user):
        """Allows to disable widgets for users."""
        return True

    def is_active(self, user):
        """Check if the widget is active for the user."""
        widget_settings = self._get_widget_settings(user.cosinnus_profile)
        return widget_settings.get('active', True)

    def set_active(self, user, active):
        """Activate or deactivate this widget for the user."""
        self._set_widget_setting(user.cosinnus_profile, 'active', active)

    def get_display(self, user):
        """Get display settings for this user widget."""
        widget_settings = self._get_widget_settings(user.cosinnus_profile)
        return widget_settings.get('display', {})

    def set_display(self, user, display):
        """Set display settings for this user widget."""
        self._set_widget_setting(user.cosinnus_profile, 'display', display)

    def get_data(self, user):
        """Get initial widget data."""
        if self.user_queryset_function and self.serializer_class and self.is_active(user):
            queryset = self.user_queryset_function(user)[: self.DATA_LIMIT]
            serializer = self.serializer_class(queryset, many=True, context={'user': user})
            return serializer.data
        return []

    def get_conf(self, user):
        return self.conf


class CosinnusPersonalDashboardNewsWidget(CosinnusPersonalDashboardWidget):
    """News/notes widget"""

    id = 'dashboard.news'
    cosinnus_app = 'cosinnus.note'
    user_queryset_function = Note.objects.get_for_user
    serializer_class = CosinnusNoteSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-note-list')


# list of all known widgets
PERSONAL_DASHBOARD_WIDGET_CLASSES = [
    CosinnusPersonalDashboardNewsWidget,
]

# initialized available dashboard widgets
personal_dashboard_widgets = {}


def init_personal_dashboard_widgets():
    """Initialize dashboard widgets."""
    global personal_dashboard_widgets
    for widget_cls in PERSONAL_DASHBOARD_WIDGET_CLASSES:
        if (
            widget_cls.id in settings.COSINNUS_V3_PERSONAL_DASHBOARD_WIDGETS
            and widget_cls.cosinnus_app not in settings.COSINNUS_DISABLED_COSINNUS_APPS
        ):
            # widget enabled
            widget_conf = settings.COSINNUS_V3_PERSONAL_DASHBOARD_WIDGETS.get(widget_cls.id)
            widget = widget_cls(conf=widget_conf)
            personal_dashboard_widgets[widget.id] = widget


def get_personal_dashboard_widgets():
    """Get all available dashboard widgets."""
    if not personal_dashboard_widgets:
        init_personal_dashboard_widgets()
    return personal_dashboard_widgets.values()


def get_personal_dashboard_widget_ids():
    """Get the ids of available dashboard widgest."""
    if not personal_dashboard_widgets:
        init_personal_dashboard_widgets()
    return personal_dashboard_widgets.keys()


def get_personal_dashboard_widget(widget_id):
    """Get dashboard widget by it."""
    if not personal_dashboard_widgets:
        init_personal_dashboard_widgets()
    return personal_dashboard_widgets.get(widget_id)

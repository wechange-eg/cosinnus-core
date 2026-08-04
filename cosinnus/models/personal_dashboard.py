from django.urls import reverse, reverse_lazy

from cosinnus.api_frontend.serializers.group import CosinnusGroupSerializer
from cosinnus.api_frontend.serializers.idea import CosinnusIdeaSerializer
from cosinnus.conf import settings
from cosinnus.models.idea import CosinnusIdea
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_user_can_create_groups
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_event.api_frontend.serializers import CosinnusEventPollSerializer, CosinnusEventSerializer
from cosinnus_event.models import Event
from cosinnus_marketplace.api_frontend.serializers import CosinnusOfferSerializer
from cosinnus_marketplace.models import Offer
from cosinnus_note.api_frontend.serializers import CosinnusNoteSerializer
from cosinnus_note.models import Note
from cosinnus_poll.api_frontend.serializers import CosinnusPollSerializer
from cosinnus_poll.models import Poll


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
    cosinnus_app = 'cosinnus_note'
    user_queryset_function = Note.objects.get_personal_items
    serializer_class = CosinnusNoteSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-note-list')


class CosinnusPersonalDashboardCreateNewWidget(CosinnusPersonalDashboardWidget):
    """News/notes widget"""

    id = 'dashboard.create_new'

    def _get_create_new_urls(self, user):
        create_new_urls = {}
        if not settings.COSINNUS_LIMIT_PROJECT_AND_GROUP_CREATION_TO_ADMINS or user.is_superuser:
            create_new_urls['project'] = reverse('cosinnus:group-add')
            if (
                not settings.COSINNUS_SHOW_MAIN_MENU_GROUP_CREATE_BUTTON_ONLY_FOR_PERMITTED
                or check_user_can_create_groups(user)
            ):
                create_new_urls['group'] = reverse('cosinnus:group__group-add')
        if settings.COSINNUS_IDEAS_ENABLED:
            create_new_urls['idea'] = reverse('cosinnus:idea-create')
        return create_new_urls

    def is_enabled(self, user):
        return bool(self._get_create_new_urls(user))

    def get_conf(self, user):
        data = super().get_conf(user)
        data['create_new_urls'] = self._get_create_new_urls(user)
        return data


class CosinnusPersonalDashboardOffersWidget(CosinnusPersonalDashboardWidget):
    """Marketplace offers widget"""

    id = 'dashboard.offers'
    cosinnus_app = 'cosinnus_marketplace'
    user_queryset_function = Offer.objects.get_personal_items
    serializer_class = CosinnusOfferSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-offer-list')


class CosinnusPersonalGroupsWidget(CosinnusPersonalDashboardWidget):
    """Personal groups and projects widget"""

    id = 'dashboard.my_spaces'
    user_queryset_function = get_cosinnus_group_model().objects.get_personal_items
    serializer_class = CosinnusGroupSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:api-group-personal')


class CosinnusPersonalEventPollsWidget(CosinnusPersonalDashboardWidget):
    """Personal open event polls widget"""

    id = 'dashboard.event_polls'
    cosinnus_app = 'cosinnus_event'
    user_queryset_function = Event.objects.get_personal_open_polls
    serializer_class = CosinnusEventPollSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-event-poll-open')


class CosinnusPersonalTasksWidget(CosinnusPersonalDashboardWidget):
    """Personal deck tasks widget"""

    id = 'dashboard.tasks'
    cosinnus_app = 'cosinnus_deck'

    def is_enabled(self, user):
        return settings.COSINNUS_DECK_ENABLED

    def get_conf(self, user):
        conf = super().get_conf(user)
        if self.is_active(user):
            # add user groups board infos
            boards = []
            user_deck_groups = get_cosinnus_group_model().objects.get_for_user_without_default_groups(user)
            user_deck_groups = [
                group
                for group in user_deck_groups
                if self.cosinnus_app not in group.get_deactivated_apps() and group.nextcloud_deck_board_id
            ]
            for group in user_deck_groups:
                boards.append(
                    {
                        'board_id': group.nextcloud_deck_board_id,
                        'board_url': group_aware_reverse('cosinnus:deck:index', kwargs={'group': group}),
                    }
                )
            conf['boards'] = boards
        return conf


class CosinnusPersonalEventsWidget(CosinnusPersonalDashboardWidget):
    """Personal events widget"""

    id = 'dashboard.events'
    cosinnus_app = 'cosinnus_event'
    user_queryset_function = Event.objects.get_personal_attending_events
    serializer_class = CosinnusEventSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-event-attending')

    def is_enabled(self, user):
        return settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED

    def get_conf(self, user):
        conf = super().get_conf(user)
        if self.is_active(user):
            # add user groups calendar urls
            calendars = []
            user_calendar_groups = get_cosinnus_group_model().objects.get_for_user_without_default_groups(user)
            user_calendar_groups = [
                group
                for group in user_calendar_groups
                if self.cosinnus_app not in group.get_deactivated_apps() and group.nextcloud_calendar_url
            ]
            for group in user_calendar_groups:
                calendars.append(group.nextcloud_calendar_url)
            conf['calendars'] = calendars
        return conf


class CosinnusPersonalPollsWidget(CosinnusPersonalDashboardWidget):
    """Personal polls widget"""

    id = 'dashboard.polls'
    cosinnus_app = 'cosinnus_poll'
    user_queryset_function = Poll.objects.get_personal_open_polls
    serializer_class = CosinnusPollSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-poll-open')


class CosinnusPersonalIdeasWidget(CosinnusPersonalDashboardWidget):
    """Personal ideas widget"""

    id = 'dashboard.ideas'
    user_queryset_function = CosinnusIdea.objects.get_personal_items
    serializer_class = CosinnusIdeaSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-idea-list')

    def is_enabled(self, user):
        return settings.COSINNUS_IDEAS_ENABLED


class CosinnusPersonalLikedIdeasWidget(CosinnusPersonalDashboardWidget):
    """Personal liked ideas widget"""

    id = 'dashboard.liked_ideas'
    user_queryset_function = CosinnusIdea.objects.get_personal_liked_items
    serializer_class = CosinnusIdeaSerializer
    api_url = reverse_lazy('cosinnus:frontend-api:personal-idea-liked')

    def is_enabled(self, user):
        return settings.COSINNUS_IDEAS_ENABLED


# list of all known widgets
PERSONAL_DASHBOARD_WIDGET_CLASSES = [
    CosinnusPersonalDashboardNewsWidget,
    CosinnusPersonalDashboardCreateNewWidget,
    CosinnusPersonalDashboardOffersWidget,
    CosinnusPersonalGroupsWidget,
    CosinnusPersonalEventPollsWidget,
    CosinnusPersonalTasksWidget,
    CosinnusPersonalEventsWidget,
    CosinnusPersonalPollsWidget,
    CosinnusPersonalIdeasWidget,
    CosinnusPersonalLikedIdeasWidget,
]

# initialized available dashboard widgets
personal_dashboard_widgets = {}


def init_personal_dashboard_widgets():
    """Initialize dashboard widgets."""
    global personal_dashboard_widgets
    for widget_cls in PERSONAL_DASHBOARD_WIDGET_CLASSES:
        if widget_cls.id in settings.COSINNUS_V3_PERSONAL_DASHBOARD_WIDGETS and (
            not widget_cls.cosinnus_app or widget_cls.cosinnus_app not in settings.COSINNUS_DISABLED_COSINNUS_APPS
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

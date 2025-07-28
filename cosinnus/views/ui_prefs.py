import logging

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.generic.base import View

logger = logging.getLogger('cosinnus')


class UiPrefIntegerListField(forms.IntegerField):
    """Acts as a wrapper around the fields used here, so integer lists can be stored.
    The validator and field contents will still use a single integer given,
    but the initial value is overridden"""

    def __init__(self, *args, **kwargs):
        actual_initial = kwargs['initial']
        kwargs['initial'] = 0
        super(UiPrefIntegerListField, self).__init__(*args, **kwargs)
        self.initial = actual_initial


USERPROFILE_UI_PREF_KEY = 'ui_pref__%s'


UI_PREF_DASHBOARD_TIMELINE_HIDE_WELCOME_SCREEN = 'timeline__hide_welcome_screen'
UI_PREF_DASHBOARD_TIMELINE_HIDE_WELCOME_WIDGET_BOX = 'timeline__hide_welcome_widget_box'
UI_PREF_DASHBOARD_TIMELINE_MINE_ONLY = 'timeline__only_mine'
UI_PREF_DASHBOARD_TIMELINE_FORUM_ONLY = 'timeline__only_forum'
UI_PREF_DASHBOARD_TIMELINE_PUBLIC_ONLY = 'timeline__only_public'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_PADS = 'dashboard_widgets_sort_key__pads'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_FILES = 'dashboard_widgets_sort_key__files'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_MESSAGES = 'dashboard_widgets_sort_key__messages'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_EVENTS = 'dashboard_widgets_sort_key__events'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_TODOS = 'dashboard_widgets_sort_key__todos'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_POLLS = 'dashboard_widgets_sort_key__polls'
UI_PREF_DASHBOARD_WIDGET_SORT_KEY_OFFERS = 'dashboard_widgets_sort_key__offers'
UI_PREF_DASHBOARD_HIDDEN_ANNOUNCEMENTS = 'dashboard_announcements__hidden'
UI_PREF_DASHBOARD_DECK_MIGRATION_DONE = 'dashboard_deck_migration__hidden'
UI_PREF_GLOBAL_HIDE_FOOTER = 'global_footer__hidden'


ALL_UI_PREFS = {
    UI_PREF_DASHBOARD_TIMELINE_HIDE_WELCOME_SCREEN: forms.BooleanField(initial=False, required=False),
    UI_PREF_DASHBOARD_TIMELINE_HIDE_WELCOME_WIDGET_BOX: forms.BooleanField(initial=False, required=False),
    UI_PREF_DASHBOARD_TIMELINE_MINE_ONLY: forms.BooleanField(initial=True, required=False),
    UI_PREF_DASHBOARD_TIMELINE_FORUM_ONLY: forms.BooleanField(initial=True, required=False),
    UI_PREF_DASHBOARD_TIMELINE_PUBLIC_ONLY: forms.BooleanField(initial=False, required=False),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_PADS: forms.IntegerField(
        initial=1, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_FILES: forms.IntegerField(
        initial=2, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_MESSAGES: forms.IntegerField(
        initial=3, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_EVENTS: forms.IntegerField(
        initial=4, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_TODOS: forms.IntegerField(
        initial=5, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_POLLS: forms.IntegerField(
        initial=6, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_WIDGET_SORT_KEY_OFFERS: forms.IntegerField(
        initial=7, validators=[MinValueValidator(0), MaxValueValidator(100)]
    ),
    UI_PREF_DASHBOARD_HIDDEN_ANNOUNCEMENTS: UiPrefIntegerListField(initial=[]),
    UI_PREF_DASHBOARD_DECK_MIGRATION_DONE: forms.BooleanField(initial=False, required=False),
    UI_PREF_GLOBAL_HIDE_FOOTER: forms.BooleanField(initial=False, required=False),
}


class UIPrefsApiView(View):
    """Saves UI Prefs for a user. Ui prefs will be checked to exist in `ALL_UI_PREFS`
    and the supplied value will be validated against the field in `ALL_UI_PREFS`

    Expected POST params: any number of ui_prefs and their values to be saved:
        - <ui_pref>: <value>,
                - <ui_pref>: resolved name of the ui pref (e.g. 'timeline_mine_only')
                - <value>: any value

    Returns:
        - {'status': 'ok'} if the UIPrefs were saved
        - a HttpResponseBadRequest if any ui_prefs could not be found or their
                values were invalid. No saving happens in that case!
    """

    http_method_names = [
        'post',
    ]

    def post(self, request, *args, **kwargs):
        # require authenticated user
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated.')

        old_ui_prefs = get_ui_prefs_for_user(request.user)

        ui_prefs = {}
        for post_key, raw_value in self.request.POST.items():
            ui_pref = post_key

            field = ALL_UI_PREFS.get(ui_pref, None)
            if not field:
                return HttpResponseBadRequest('ui_pref "%s" not found!' % ui_pref)
            try:
                value = self.get_valid_value(field, raw_value)
                if type(field) is UiPrefIntegerListField:
                    # for list fields, store the value by appending to the existing list
                    ui_prefs[ui_pref] = list(set(old_ui_prefs[ui_pref] + [value]))
                else:
                    ui_prefs[ui_pref] = value

            except ValidationError as e:
                return HttpResponseBadRequest('Validation error for ui_pref "%s": %s' % (ui_pref, str(e)))

        if ui_prefs:
            self.save_ui_prefs(ui_prefs)
        return JsonResponse({'status': 'ok'})

    def get_valid_value(self, field, raw_value):
        """Validate a raw value for a ui_pref using its defined form-field"""
        try:
            val = field.to_python(raw_value)
            field.validate(val)
            field.run_validators(val)
            return val
        except ValidationError as e:
            raise e

    def save_ui_prefs(self, ui_prefs):
        """Saves all given ui_prefs (they must have been validated before!)"""
        for ui_pref, value in ui_prefs.items():
            ui_pref_key = USERPROFILE_UI_PREF_KEY % ui_pref
            profile = self.request.user.cosinnus_profile
            profile.settings[ui_pref_key] = value
        profile.save(update_fields=['settings'])


api_ui_prefs = UIPrefsApiView.as_view()


def get_ui_prefs_for_user(user):
    """Returns all UI-prefs for a given user, providing default (initial) values for the unset ones"""

    if not user.is_authenticated:
        return {}
    settings = user.cosinnus_profile.settings
    ui_prefs = dict(
        (
            (ui_pref, settings.get(USERPROFILE_UI_PREF_KEY % ui_pref, pref_field.initial))
            for ui_pref, pref_field in ALL_UI_PREFS.items()
        )
    )
    return ui_prefs

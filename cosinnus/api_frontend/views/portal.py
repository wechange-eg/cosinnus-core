from copy import copy

from django.core.cache import cache
from django.db.models.aggregates import Count
from django.db.models.query_utils import Q
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from taggit.models import Tag, TaggedItem

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.portal import CosinnusManagedTagSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.conf import settings
from cosinnus.dynamic_fields import dynamic_fields
from cosinnus.dynamic_fields.dynamic_formfields import EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.managed_tags import MANAGED_TAG_LABELS, CosinnusManagedTag
from cosinnus.utils.functions import clean_single_line_text, is_number, update_dict_recursive
from cosinnus.views.common import SwitchLanguageView


class PortalTopicsView(APIView):
    """An endpoint that returns the configured topic choices for this portal"""

    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='A list of objects containing the id for a topic as "value" and its label as "title".',
                examples={
                    'application/json': {
                        'data': [{'value': '0', 'title': 'Mobility'}, {'value': '1', 'title': 'Energy'}],
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        topic_data = []
        for topic_id, topic_label in settings.COSINNUS_TOPIC_CHOICES:
            topic_data.append({'value': force_str(topic_id), 'title': force_str(topic_label)})
        return Response(topic_data)


class PortalTagsView(APIView):
    """An endpoint that returns tags matched for the given "q" parameter."""

    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='A list of strings as the tags matched for the given "q" parameter.',
                examples={
                    'application/json': {
                        'data': [
                            'tag1',
                            'tag2',
                        ],
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        tag_data = []
        term = request.GET.get('q', '').lower().strip()
        limit = request.GET.get('limit', 'invalid')
        if not is_number(limit):
            limit = 10
        limit = int(limit)
        if limit < 0 or limit > 50:
            limit = 10
        print(limit)
        page = 1
        start = (page - 1) * limit
        end = page * limit
        qs = Tag.objects.all()
        TaggedItem
        # TaggedItem.tag
        if term:
            q = Q(name__icontains=term)
            qs = qs.filter(q)
        qs = (
            qs.annotate(num_tagged=Count('taggit_taggeditem_items'))
            .exclude(num_tagged__exact=0)
            .order_by('-num_tagged')
        )
        count = qs.count()
        if count >= start:
            tag_data = qs[start:end].values_list('name', 'num_tagged')
            tag_data = [dict(zip(['value', 'frequency'], data_tup)) for data_tup in tag_data]
        return Response(tag_data)


class PortalManagedTagsView(APIView):
    """An endpoint that returns the managed tags for this portal"""

    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='A list of objects containing the id for a topic as "value" and its label as "title".',
                examples={
                    'application/json': {
                        'data': {
                            'enabled': 'true',
                            'in_signup': 'true',
                            'required': 'true',
                            'multiple': 'false',
                            'title': 'Managed Tag',
                            'title_plural': 'Managed Tags',
                            'icon': 'fa-tags',
                            'managed_tags': [
                                {
                                    'slug': 'mtag1',
                                    'name': 'A fully filled Mtag',
                                    'default': True,
                                    'type': {
                                        'id': 1,
                                        'name': 'A type of tag',
                                        'prefix_label': 'typemtag',
                                        'color': '123455',
                                    },
                                    'description': 'short description here',
                                    'image': (
                                        '/media/cosinnus_portals/portal_wechange/managed_tag_images/images/'
                                        '7e80af5f985f59bd9c186e892782cea4940b9e90.jpg'
                                    ),
                                    'url': 'https://openstreetmap.org',
                                    'search_synonyms': 'wow,cool,awesome',
                                    'group_url': 'http://127.0.0.1:8000/project/exch/',
                                },
                                {
                                    'slug': 'mtag2',
                                    'name': 'Mtag two quite empty',
                                    'default': False,
                                    'type': None,
                                    'description': '',
                                    'image': None,
                                    'url': None,
                                    'search_synonyms': '',
                                    'group_url': None,
                                },
                            ],
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        managed_tag_data = [
            CosinnusManagedTagSerializer(mtag).data for mtag in CosinnusManagedTag.objects.all_in_portal_cached()
        ]
        managed_tag_data = sorted(managed_tag_data, key=lambda tag: tag['default'], reverse=True)
        data = {
            'enabled': settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF,
            'in_signup': settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM,
            'readonly_in_setup': settings.COSINNUS_MANAGED_TAGS_IN_UPDATE_FORM,
            'required': settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED,
            'multiple': settings.COSINNUS_MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED,
            'title': MANAGED_TAG_LABELS.MANAGED_TAG_NAME,
            'title_plural': MANAGED_TAG_LABELS.MANAGED_TAG_NAME_PLURAL,
            'icon': MANAGED_TAG_LABELS.ICON,
            'managed_tags': managed_tag_data,
        }
        return Response(data)


def generate_api_dict_for_dynamic_field(field_name, field_definition_dict, field_option_filter=None):
    """Generates a list of API response dicts for a single dynamic field, given the field name
    and field definitions dict for that field (the dict is usally a reference to the ones defined in
    `COSINNUS_USERPROFILE_EXTRA_FIELDS`.
    @return: an array of dynamic field definition dicts. there can be multiple, e.g. if translateable
        fields are involved."""
    field_data = []

    field_options = field_definition_dict[field_name]
    if field_option_filter and not getattr(field_options, field_option_filter, False):
        return []
    choices = field_options.choices
    if not choices:
        if False and field_options.type == dynamic_fields.DYNAMIC_FIELD_TYPE_DYNAMIC_CHOICES:
            # TODO: for dynamic fields with dynamic choices, an extra select2-style
            # autocomplete endpoint should be created, both in the v3 API and in the formfields!
            # as this doesn't scale well for portals with large numbers of groups!
            choices = '<dynamic-NYI>'
        else:
            formfield = EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS.get(field_options.type)().get_formfield(
                field_name, field_options
            )
            choices = getattr(formfield, 'choices', None)
    # remove the empty choice from choices for multiple fields, as our frontend doesn't need it
    if choices and field_options.multiple is True:
        choices = [(k, v) for (k, v) in choices if k]

    # check if multilanguage is enabled
    is_multi_language_field = (
        settings.COSINNUS_TRANSLATED_FIELDS_ENABLED
        and field_name in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS_TRANSLATED_FIELDS
    )

    current_field_data = {
        'name': field_name,
        'is_multi_language': is_multi_language_field,
        'is_multi_language_sub_field': False,
        'in_signup': field_options.in_signup,
        'hide_in_setup': field_options.hide_in_setup,
        'required': field_options.required,
        'multiple': field_options.multiple,
        'type': field_options.type,
        'label': field_options.label,
        'legend': field_options.legend,
        'header': field_options.header,
        'placeholder': field_options.placeholder,
        'is_group_header': field_options.is_group_header,
        'parent_group_field_name': field_options.parent_group_field_name,
        'display_required_field_names': field_options.display_required_field_names,
        'display_required_managed_tags_slug': field_options.display_required_managed_tags_slug,
        'choices': choices,
        'max_length': field_options.max_length,
    }
    field_data.append(current_field_data)

    # add multilanguage sub fields
    if is_multi_language_field:
        for language_code, language in settings.LANGUAGES:
            multilanguage_field_data = current_field_data.copy()
            multilanguage_field_data.update(
                **{
                    'name': f'{field_name}__{language_code}',
                    'label': language,
                    'is_multi_language_sub_field': True,
                }
            )
            field_data.append(multilanguage_field_data)
    return field_data


class PortalUserprofileDynamicFieldsView(APIView):
    """An endpoint that returns the configured topic choices for this portal"""

    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    # if set on the view, show only dynamic fields that appear in the signup form
    field_option_filter = None
    description = """
        A list of objects containing the field name, meta info and "choices":
        a list of tuples of acceptable key/value pairs (or null if all values are acceptable)
        for each dynamic userprofile field for this portal.

        Field attributes:
        - "name": str, field name
        - "in_signup": bool, whether to show up in the signup form
        - "hide_in_setup": bool, whether to show up in the setup form
        - "required": bool, whether to be required in forms
        - "multiple": bool, for choice fields, if multiple choices are allowed. ignored for other types
        - "type": type of the dynamic field (affects both model and form), see <str type of `DYNAMIC_FIELD_TYPES`>,
        - "label":  i18n str, formfield label
        - "legend": i18n str, legend, a descriptive explanatory text added to the field
        - "header": i18n str, if given, should display a new seperator and header above this field
        - "placeholder": i18n str, formfield placeholder
        - "is_group_header": whether the field is a checkbox field shown as a group header, that shows/hides a field \
                group if checked/unchecked
        - "parent_group_field_name": if this field belongs to a checkbox group, this refers to the parent checkbox \
                field of that group, which needs to have `is_group_header=True`
        - "display_required_field_names": if this field should only be shown if either one of a list of checkbox \
                fields is checked, this is the list field names of checkbox fields of which one is required to be \
                checked
        - "display_required_managed_tags_slug": if this field should only be shown if the user has the managed tag \
                assigned
        - "choices": list or null, the choice tuples of (value, label) for choice fields
    """
    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description=description,
                examples={
                    'application/json': {
                        'data': [
                            {
                                'name': 'institution',
                                'is_multi_language': False,
                                'is_multi_language_sub_field': False,
                                'in_signup': 'true',
                                'hide_in_signup': 'false',
                                'required': 'true',
                                'multiple': 'false',
                                'type': 'text',
                                'label': 'Institution',
                                'placeholder': 'Institution',
                                'choices': 'null',
                            },
                            {
                                'name': 'languages',
                                'is_multi_language': False,
                                'is_multi_language_sub_field': False,
                                'in_signup': 'false',
                                'hide_in_signup': 'false',
                                'required': 'false',
                                'multiple': 'true',
                                'type': 'languages',
                                'label': 'Sprachen',
                                'placeholder': 'Mehrere Auswahlen sind möglich',
                                'choices': [
                                    ['aa', 'Afar'],
                                    ['ab', 'Abkhazian'],
                                    ['af', 'Afrikaans'],
                                ],
                            },
                        ],
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        field_data = []
        for field_name in self.DYNAMIC_FIELD_SETTINGS.keys():
            items_for_field = generate_api_dict_for_dynamic_field(
                field_name, self.DYNAMIC_FIELD_SETTINGS, field_option_filter=self.field_option_filter
            )
            field_data.extend(items_for_field)

        return Response(field_data)


class PortalUserprofileDynamicFieldsSignupView(PortalUserprofileDynamicFieldsView):
    if settings.COSINNUS_USER_SIGNUP_ENABLED:
        # anyone can access this, as it is required for signup
        permission_classes = ()

    # if set on the view, show only dynamic fields that appear in the signup form
    field_option_filter = 'in_signup'
    description = (
        PortalUserprofileDynamicFieldsView.description
        + ' This view shows only dynamic fields that appear in the signup form.'
    )


class PortalSettingsView(APIView):
    """
    An endpoint that returns configured settings for this portal.
    Returns many settings from conf.py for this portal, as well as preformatted dynamic fields.
    This endpoint is called on every page load and is i18n-session sensitive,
    and thus uses language-dependent caching of the entire return value to reduce computational costs.

    Any returned values will be overridden by anything defined in conf dict `COSINNUS_V3_PORTAL_SETTINGS` (uncached).

    A full example string for manually configuarable settings that aren't dynamically taken from the portal config:

    {
        "links": {
            "privacyPolicy": "https://PORTAL/cms/datenschutzerklaerung/",
            "termsOfUse": "https://PORTAL/cms/nutzungsbedingungen/",
            "legalNotice": "https://PORTAL/cms/impressum/",
            "images": {
                "navBarLogo": {
                    "light": "/static/img/frontend/logo.png",
                    "dark": "/static/img/frontend/logo.png"
                },
                "welcome": {
                    "light": "/static/img/frontend/signup/welcome/img.svg",
                    "dark": "/static/img/frontend/signup/welcome/img.svg"
                },
               "verified": {
                    "light": "PATH_TO_VERIFIED",
                    "dark": "PATH_TO_VERIFIED"
                },
                "login": {
                    "light": "/static/img/frontend/login/light.svg",
                    "dark": "/static/img/frontend/login/dark.svg"
                }
            }
        },
        "theme": {
            "loginImage": {
                "variant": "covering|contained"  # default: covering
            },
           "color": "blue",  # exclusive with "brandColors"
           # palette color. can be generated with https://palette.saas-ui.dev/
           "brandColors": {  # exclusive with "color"
               "50": "#ffffff",
               "100": "#ffffff",
               "200": "#ffffff",
               "300": "#ffffff",
               "400": "#ffffff",
               "500": "#ffffff",
               "600": "#ffffff",
               "700": "#ffffff",
               "800": "#ffffff",
               "900": "#ffffff",
           },
           "signalColors": {  # signal highlight colors like unread badges (only to override the frontend defaults)
               "50": "#f50a41",
               "100": "#f50a41",
               "200": "#f50a41",
               "300": "#f50a41",
               "400": "#f50a41",
               "500": "#f50a41",
               "600": "#f50a41",
               "700": "#f50a41",
               "800": "#f50a41",
               "900": "#f50a41",
           },
        },
        "setup": {  # settings for the each of the step pages of the onboarding wizards
            "contact": {
                "description": format_lazy("{} {}", _("Combined"), _("lazy example"))
            },
            "interests": {
                "description": "..."
            }
        },
        "fieldOverrides": {
            "setup": {
                "profile": {
                    # this is an example full overridable field dict. single properties can be overriden as well
                    "first_name": {
                        "name": "first_name",
                        "is_multi_language": False,
                        "is_multi_language_sub_field": False,
                        "in_signup": True,
                        "required": True,
                        "multiple": False,
                        "type": "text",
                        "label": "...",
                        "legend": "...",
                        "placeholder": None,
                        "is_group_header": False,
                        "parent_group_field_name": None,
                        "display_required_field_names": None,
                        "display_required_managed_tags_slug": None,
                        "choices": None,
                        "max_length": None,
                    },
                    ...  # more named field overrides
                }
            },
            "signup": {
                "credentials": {}  # see example above
            },
            "contact": {
                "profile": {}  # see example above
            }
        },
        "signupCredentialsScreenMessage": "..."  # paragraph text under the signup form
    }
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)

    PORTAL_SETTINGS_BY_LANGUAGE_CACHE_KEY = 'cosinnus/core/portal/portalsettings/%s'  # key is language code
    CACHE_TIMEOUT_DEV = 30  # 30 seconds for dev servers
    CACHE_TIMEOUT = 30 * 60  # 30 minutes for production servers

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={
            '200': openapi.Response(
                description='A list of objects containing the id for a topic as "value" and its label as "title".',
                examples={
                    'application/json': {
                        'data': {
                            'example_setting': 'example_value',
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        }
    )
    def get(self, request):
        current_language = get_language()
        settings_dict = cache.get(self.PORTAL_SETTINGS_BY_LANGUAGE_CACHE_KEY % current_language)
        if not settings_dict:
            settings_dict = self.build_settings_dict(request)
            timeout = self.CACHE_TIMEOUT_DEV if settings.COSINNUS_IS_TEST_SERVER else self.CACHE_TIMEOUT
            cache.set(self.PORTAL_SETTINGS_BY_LANGUAGE_CACHE_KEY % current_language, settings_dict, timeout)
        # update any settings delivered from `COSINNUS_V3_PORTAL_SETTINGS` recursively, uncached
        update_dict_recursive(settings_dict, settings.COSINNUS_V3_PORTAL_SETTINGS, extend_lists=True)
        response = Response(settings_dict)
        # set language cookie if not present
        if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            # if we ever wanted to ignore browser language preferences, and force the default portal language,
            # we can replace `get_language()` with `settings.LANGUAGE_CODE` here:
            switch_language_view = SwitchLanguageView()
            switch_language_view.switch_language(get_language(), request, response)
        return response

    def build_settings_dict(self, request):
        """Generates the complete settings dict afresh"""
        portal = CosinnusPortal.get_current()
        privacy_policy_url = clean_single_line_text(
            render_to_string('cosinnus/v2/urls/privacy_policy_url.html', request=request)
        )
        terms_of_use_url = clean_single_line_text(render_to_string('cosinnus/v2/urls/tos_url.html', request=request))
        impressum_url = clean_single_line_text(render_to_string('cosinnus/v2/urls/impressum_url.html', request=request))
        settings_dict = {
            'portalName': settings.COSINNUS_PORTAL_NAME,
            'portalDisplayName': settings.COSINNUS_BASE_PAGE_TITLE_TRANS,
            'hasNewsletter': settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN,
            'links': {
                'privacyPolicy': privacy_policy_url,
                'termsOfUse': terms_of_use_url,
                'legalNotice': impressum_url,
            },
            'cosinnusIsPrivatePortal': settings.COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN,
            'cosinnusIsSignupDisabled': not settings.COSINNUS_USER_SIGNUP_ENABLED,
            'cosinnusIsLoginDisabled': settings.COSINNUS_USER_LOGIN_DISABLED,
            'cosinnusCloudEnabled': settings.COSINNUS_CLOUD_ENABLED,
            'cosinnusCloudNextcloudUrl': settings.COSINNUS_CLOUD_NEXTCLOUD_URL,
            'signupCredentialsScreenMessage': None,
            'usersNeedActivation': portal.users_need_activation,
            'currentLanguage': get_language(),
            'userProfileVisibilityLocked': bool(settings.COSINNUS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED is not None),
            'cosinnusIsSSOLoginEnabled': settings.COSINNUS_IS_OAUTH_CLIENT,
            'cosinnusSSOProvider': settings.COSINNUS_V3_SSO_PROVIDER,
            # 'setup': {'additionalSteps': ... }},  # set manually
            # 'theme': {...},  # set manually. example:
            # "theme": {"color": "blue", "loginImage": {"variant": "contained"}},
            #    ("loginImage" ist optional, values: "covering|contained", defaults zu covering)
        }
        field_overrides = self._build_field_overrides_dict()
        if field_overrides:
            settings_dict['fieldOverrides'] = field_overrides
        return settings_dict

    def _build_field_overrides_dict(self):
        """Build the dict of overriden dynamic fields
        The full overridable field definition looks as follows, and each or any key can be overridden:
        defined_name_field = {
            'name': 'last_name',
            'is_multi_language': False,
            'is_multi_language_sub_field': False,
            'in_signup': True,
            'required': True,
            'multiple': False,
            'type': 'text',
            'label': _('Last name'),
            'legend': None,
            'placeholder': None,
            'is_group_header': False,
            'parent_group_field_name': None,
            'display_required_field_names': None,
            'display_required_managed_tags_slug': None,
            'choices': None,
        }
        """
        field_overrides = {}
        if settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED:
            # for last-name required portals, we make the last name field required and set its label
            defined_name_fields = {
                'last_name': {
                    'name': 'last_name',
                    'is_multi_language': False,
                    'is_multi_language_sub_field': False,
                    'in_signup': True,
                    'required': True,
                    'multiple': False,
                    'type': 'text',
                    'label': _('Last name'),
                    'legend': None,
                    'placeholder': None,
                    'is_group_header': False,
                    'parent_group_field_name': None,
                    'display_required_field_names': None,
                    'display_required_managed_tags_slug': None,
                    'choices': None,
                }
            }
        else:
            # for only-first-name required portals, we change the label of the first name field to "Display name"
            defined_name_fields = {
                'first_name': {
                    'name': 'first_name',
                    'is_multi_language': False,
                    'is_multi_language_sub_field': False,
                    'in_signup': True,
                    'required': True,
                    'multiple': False,
                    'type': 'text',
                    'label': _('Display name'),
                    'legend': _('Help others find you and use your real name.'),
                    'placeholder': None,
                    'is_group_header': False,
                    'parent_group_field_name': None,
                    'display_required_field_names': None,
                    'display_required_managed_tags_slug': None,
                    'choices': None,
                }
            }
        # the field gets added to the signup
        field_overrides['signup'] = {
            'credentials': {
                'email': {
                    'legend': _(
                        'This will be used as your login. '
                        + 'Notification emails will be sent to this address (if you want to receive them).'
                    ),
                },
            },
            'profile': copy(defined_name_fields),
        }
        # and we also add that field in the first setup step again
        # note difference of 'setup' vs 'signup' keys!
        field_overrides['setup'] = {'profile': copy(defined_name_fields)}

        # add a field override managed tags section if they should appear in signup
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM:
            if 'signup' not in field_overrides:
                field_overrides['signup'] = {}
            field_overrides['signup']['managedTagsSection'] = {
                'label': _('fields.managed_tags.label'),
                'description': _('fields.managed_tags.description'),
            }
        return field_overrides

    @classmethod
    def clear_cache(cls):
        """Clears the portal setting dict cache entries for all languages"""
        for language_code, __ in settings.LANGUAGES:
            cache.delete(cls.PORTAL_SETTINGS_BY_LANGUAGE_CACHE_KEY % language_code)

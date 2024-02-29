from copy import copy

from django.utils.encoding import force_str
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.portal import CosinnusManagedTagSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.conf import settings, get_obfuscated_settings_strings
from cosinnus.models.managed_tags import MANAGED_TAG_LABELS, CosinnusManagedTag
from django.db.models.query_utils import Q
from taggit.models import Tag, TaggedItem
from django.http.response import Http404
from cosinnus.utils.functions import is_number
from django.db.models.aggregates import Count
from cosinnus.dynamic_fields.dynamic_formfields import EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS
from cosinnus.dynamic_fields import dynamic_fields


class PortalTopicsView(APIView):
    """ An endpoint that returns the configured topic choices for this portal """
    
    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='A list of objects containing the id for a topic as "value" and its label as "title".',
            examples={
                "application/json": {
                    "data": [
                        {"value": "0", "title": "Mobility"},
                        {"value": "1", "title": "Energy"}
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        topic_data = []
        for topic_id, topic_label in settings.COSINNUS_TOPIC_CHOICES:
            topic_data.append({
                'value': force_str(topic_id),
                'title': force_str(topic_label)
            })
        return Response(topic_data)


class PortalTagsView(APIView):
    """ An endpoint that returns tags matched for the given "q" parameter. """
    
    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='A list of strings as the tags matched for the given "q" parameter.',
            examples={
                "application/json": {
                    "data": [
                        "tag1",
                        "tag2",
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
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
        qs = qs.annotate(num_tagged=Count('taggit_taggeditem_items')).exclude(num_tagged__exact=0).order_by('-num_tagged')
        count = qs.count()
        if count >= start:
            tag_data = qs[start:end].values_list('name', 'num_tagged')
            tag_data = [dict(zip(['value', 'frequency'], data_tup)) for data_tup in tag_data]
        return Response(tag_data)


class PortalManagedTagsView(APIView):
    """ An endpoint that returns the managed tags for this portal """
    
    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='A list of objects containing the id for a topic as "value" and its label as "title".',
            examples={
                "application/json": {
                    "data": {
                        "enabled": "true",
                        "in_signup": "true",
                        "required": "true",
                        "multiple": "false",
                        "title": "Managed Tag",
                        "title_plural": "Managed Tags",
                        "icon": "fa-tags",
                        "managed_tags": [
                            {
                                "slug": "mtag1",
                                "name": "A fully filled Mtag",
                                "default": True,
                                "type": {
                                    "id": 1,
                                    "name": "A type of tag",
                                    "prefix_label": "typemtag",
                                    "color": "123455"
                                },
                                "description": "short description here",
                                "image": "/media/cosinnus_portals/portal_wechange/managed_tag_images/images/7e80af5f985f59bd9c186e892782cea4940b9e90.jpg",
                                "url": "https://openstreetmap.org",
                                "search_synonyms": "wow,cool,awesome",
                                "group_url": "http://127.0.0.1:8000/project/exch/"
                            },
                            {
                                "slug": "mtag2",
                                "name": "Mtag two quite empty",
                                "default": False,
                                "type": None,
                                "description": "",
                                "image": None,
                                "url": None,
                                "search_synonyms": "",
                                "group_url": None
                            }
                        ]
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        managed_tag_data = [
            CosinnusManagedTagSerializer(mtag).data
            for mtag 
            in CosinnusManagedTag.objects.all_in_portal_cached()
        ]
        managed_tag_data = sorted(managed_tag_data, key=lambda tag: tag['default'], reverse=True)
        data = {
            'enabled': settings.COSINNUS_MANAGED_TAGS_ENABLED and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF,
            'in_signup': settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM,
            'required': settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED,
            'multiple': settings.COSINNUS_MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED,
            'title': MANAGED_TAG_LABELS.MANAGED_TAG_NAME,
            'title_plural': MANAGED_TAG_LABELS.MANAGED_TAG_NAME_PLURAL,
            'icon': MANAGED_TAG_LABELS.ICON,
            'managed_tags': managed_tag_data,
        }
        return Response(data)
    

class PortalUserprofileDynamicFieldsView(APIView):
    """ An endpoint that returns the configured topic choices for this portal """
    
    # disallow anonymous users if signup is disabled
    if not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
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
                fields is checked, this is the list field names of checkbox fields of which one is required to be checked
        - "choices": list or null, the choice tuples of (value, label) for choice fields
    """
    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description=description,
            examples={
                "application/json": {
                    "data": [
                        {
                            "name": "institution",
                            "in_signup": "true",
                            "required": "true",
                            "multiple": "false",
                            "type": "text",
                            "label": "Institution",
                            "placeholder": "Institution",
                            "choices": "null"
                        },
                        {
                            "name": "languages",
                            "in_signup": "false",
                            "required": "false",
                            "multiple": "true",
                            "type": "languages",
                            "label": "Sprachen",
                            "placeholder": "Mehrere Auswahlen sind möglich",
                            "choices": [
                                [
                                    "aa",
                                    "Afar"
                                ],
                                [
                                    "ab",
                                    "Abkhazian"
                                ],
                                [
                                    "af",
                                    "Afrikaans"
                                ],
                            ]
                        },
                        
                    ],
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        field_data = []
        for field_name, field_options in self.DYNAMIC_FIELD_SETTINGS.items():
            if self.field_option_filter and not getattr(field_options, self.field_option_filter, False):
                continue
            choices = field_options.choices
            if not choices:
                if False and field_options.type == dynamic_fields.DYNAMIC_FIELD_TYPE_DYNAMIC_CHOICES:
                    # TODO: for dynamic fields with dynamic choices, an extra select2-style 
                    # autocomplete endpoint should be created, both in the v3 API and in the formfields!
                    # as this doesn't scale well for portals with large numbers of groups!
                    choices = '<dynamic-NYI>'
                else:
                    formfield = EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS.get(field_options.type)().get_formfield(
                        field_name,
                        field_options
                    )
                    choices = getattr(formfield, 'choices', None)
            # remove the empty choice from choices for multiple fields, as our frontend doesn't need it
            if choices and field_options.multiple == True:
                choices = [(k, v) for (k, v) in choices if k]
            field_data.append({
                'name': field_name,
                'in_signup': field_options.in_signup,
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
                'choices': choices,
            })
        return Response(field_data)


class PortalUserprofileDynamicFieldsSignupView(PortalUserprofileDynamicFieldsView):
    
    if settings.COSINNUS_USER_SIGNUP_ENABLED:
        # anyone can access this, as it is required for signup
        permission_classes = ()
    
    # if set on the view, show only dynamic fields that appear in the signup form
    field_option_filter = 'in_signup'
    description = PortalUserprofileDynamicFieldsView.description + ' This view shows only dynamic fields that appear in the signup form.'


class PortalSettingsView(APIView):
    """ An endpoint that returns configured settings for this portal.
        Currently simply returns the contents of conf setting `COSINNUS_V3_PORTAL_SETTINGS` """
    
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        responses={'200': openapi.Response(
            description='A list of objects containing the id for a topic as "value" and its label as "title".',
            examples={
                "application/json": {
                    "data": {
                        'example_setting': 'example_value',
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        settings_dict = copy(settings.COSINNUS_V3_PORTAL_SETTINGS)
        settings_dict.update({
            'COSINNUS_CLOUD_ENABLED': settings.COSINNUS_CLOUD_ENABLED,
            'COSINNUS_CLOUD_NEXTCLOUD_URL': settings.COSINNUS_CLOUD_NEXTCLOUD_URL,
        })
        return Response(settings_dict)


class PortalConfigurationView(APIView):
    """ An endpoint that returns the portal configuration. """

    permission_classes = (IsAdminUser,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication, JWTAuthentication)

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'setting', openapi.IN_QUERY, required=False,
                description='Return just the value of this setting variable.',
                type=openapi.TYPE_STRING
            ),
        ],
        responses={'200': openapi.Response(
            description='List all portal settings as sttings with sensible values (e.g. passwords) obfuscated.',
            examples={
                "application/json": {
                    "data": {
                        "ABSOLUTE_URL_OVERRIDES": "{}",
                        "ACCOUNT_ADAPTER": "cosinnus_oauth_client.views.CosinusAccountAdapter",
                        "ADMINS": "()",
                        "ADMIN_URL": "admin/",
                    },
                    "version": COSINNUS_VERSION,
                    "timestamp": 1658414865.057476
                }
            }
        )}
    )
    def get(self, request):
        setting = request.query_params.get('setting')
        obfuscated_settings = get_obfuscated_settings_strings()
        if setting:
            if setting in obfuscated_settings:
                obfuscated_settings = {setting: obfuscated_settings.get(setting)}
            else:
                obfuscated_settings = {}
        return Response(obfuscated_settings)

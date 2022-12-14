from django.utils.encoding import force_text
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.portal import CosinnusManagedTagSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.conf import settings
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
    if settings.COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN or not settings.COSINNUS_USER_SIGNUP_ENABLED:
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
                'value': force_text(topic_id),
                'title': force_text(topic_label)
            })
        return Response(topic_data)


class PortalTagsView(APIView):
    """ An endpoint that returns tags matched for the given "q" parameter. """
    
    # disallow anonymous users if signup is disabled
    if settings.COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN or not settings.COSINNUS_USER_SIGNUP_ENABLED:
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
    if settings.COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN or not settings.COSINNUS_USER_SIGNUP_ENABLED:
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
    if settings.COSINNUS_USER_EXTERNAL_USERS_FORBIDDEN or not settings.COSINNUS_USER_SIGNUP_ENABLED:
        permission_classes = (IsAuthenticated,)
    renderer_classes = (CosinnusAPIFrontendJSONResponseRenderer, BrowsableAPIRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    # if set on the view, show only dynamic fields that appear in the signup form
    field_option_filter = None
    description = 'A list of objects containing the field name, meta info and "choices": a list of tuples of acceptable key/value pairs (or null if all values are acceptable) for each dynamic userprofile field for this portal.'
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
                                    "",
                                    "Keine Auswahl"
                                ],
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
                if field_options.type == dynamic_fields.DYNAMIC_FIELD_TYPE_DYNAMIC_CHOICES:
                    # TODO: for dynamic fields with dynamic choices, an extra select2-style 
                    # autocomplete endpoint must be created, if they are ever needed in the v3 API!
                    choices = '<dynamic-NYI>'
                else:
                    formfield = EXTRA_FIELD_TYPE_FORMFIELD_GENERATORS.get(field_options.type)().get_formfield(
                        field_name,
                        field_options
                    )
                    choices = getattr(formfield, 'choices', None)
            field_data.append({
                'name': field_name,
                'in_signup': field_options.in_signup,
                'required': field_options.required,
                'multiple': field_options.multiple,
                'type': field_options.type,
                'label': field_options.label,
                'placeholder': field_options.placeholder,
                'choices': choices,
            })
        return Response(field_data)


class PortalUserprofileDynamicFieldsSignupView(PortalUserprofileDynamicFieldsView):
    
    # if set on the view, show only dynamic fields that appear in the signup form
    field_option_filter = 'in_signup'
    description = PortalUserprofileDynamicFieldsView.description + ' This view shows only dynamic fields that appear in the signup form.'

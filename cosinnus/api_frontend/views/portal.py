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
        qs = qs.annotate(num_tagged=Count('taggit_taggeditem_items')).order_by('-num_tagged')
        count = qs.count()
        if count >= start:
            tag_data = qs[start:end].values_list('name', flat=True)
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
            'title': MANAGED_TAG_LABELS.MANAGED_TAG_NAME,
            'title_plural': MANAGED_TAG_LABELS.MANAGED_TAG_NAME_PLURAL,
            'icon': MANAGED_TAG_LABELS.ICON,
            'managed_tags': managed_tag_data,
        }
        return Response(data)
    


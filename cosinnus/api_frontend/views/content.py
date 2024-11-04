import logging
import re
from copy import copy
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.core.cache import cache
from django.http import QueryDict
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from announcements.models import Announcement
from cosinnus import VERSION as COSINNUS_VERSION
from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.views.navigation import LanguageMenuItemMixin
from cosinnus.conf import settings
from cosinnus.core.decorators.views import get_group_for_request
from cosinnus.core.middleware.frontend_middleware import FrontendMiddleware
from cosinnus.models import CosinnusPortal
from cosinnus.models.user_dashboard import FONT_AWESOME_CLASS_FILTER, MenuItem
from cosinnus.utils.context_processors import email_verified as email_verified_context_processor
from cosinnus.utils.functions import clean_single_line_text, uniquify_list
from cosinnus.utils.http import add_url_param, remove_url_param
from cosinnus.utils.urls import check_url_v3_everywhere_exempt

logger = logging.getLogger('cosinnus')


# url suffixes for links from the leftnav that should be sorted into the top sidebar list
V3_CONTENT_TOP_SIDEBAR_URL_PATTERNS = [
    '.*/?browse=true$',  # group dashboard
    '.*/microsite/$',
    '.*/members/$',
]
# url suffixes for links from the leftnav that should be sorted into the bottom sidebar list
V3_CONTENT_BOTTOM_SIDEBAR_URL_PATTERNS = [
    '.*/edit/$',
    '.*/delete/$',
    '.*/password_change/$',
    '^/setup/profile/',
    '^/account/deactivate/',
    '^/account/activate/',
    '^#$',
]


class MainContentView(LanguageMenuItemMixin, APIView):
    """v3_content_main

    An endpoint that returns HTML content for any legacy view on the portal.
    Will not work on URL targets that match exemptions defined in
    `COSINNUS_V3_FRONTEND_EVERYWHERE_URL_PATTERN_EXEMPTIONS`

    Return values:
      * `resolved_url`: the resolved URL of the queried `url` parameter where the content HTML is delivered from,
        or if `redirect==True`, the target URL to redirect to
      * `redirect": (bool) whether the target URL was resolved and HTML content is returned in this data package,
        or, if True, the data package is empty and a redirect should be performed to `resolved_url`
      * `status_code`: (int), HTTP status code of the response for the request sent to the `resolved_url`
      * `content_html`: html from the `<div class="container">` frame to be inserted
      * `footer_html`: html from the footer, to be inserted after the content html
      * `head`: object with sub-entries for all content belonging in the head:
        * `js_vendor_urls`: list of vendor JS file URLs to be loaded in, basically all vendor `<script src="..."`
            from the `<head>` tag of that page
        * `js_urls`: list of JS file URLs to be loaded in, basically all non-vendor `<script src="..."` from the
            `<head>` tag of that page. these should be loaded third, after first the `js_vendor_urls``, and then the
            `scripts` JS have been loaded
        * `css_urls`: list of CSS file URLs to be loaded in, basically all stylesheets from the `<head>` tag of that
            page
        * `meta`: add all meta tags from the head
        * `styles`: a list of strings of literal inline styles to be inserted before the HTML content is inserted
      * `script_constants`: a list of literal inline JS code that has JS global definitions that need to be loaded
        before the `js_urls` are inserted (but can be loaded after `js_vendor_urls` are inserted)
      * `scripts`: a list of strings of literal inline JS script code to be executed before (after?) the HTML content
        is inserted
      * `sub_navigation`: sidebar content, includes 3 lists:
        `"sub_navigation" {"top": [...], "middle": [...], "bottom": [...]}`
        * middle is list of the apps that are enabled for the current space
        * each list contains the usual menu items
          * title (will be in current language)
          * url link
          * icon
          * external (bool flag for `target="_blank"`)
        * `sub_navigation` can be `null`, in that case the entire left sidebar is hidden
      * `main_menu`: object with the following sub-entries, signifying how the main dropdown button looks like:
        * `label`: title of the main menu dropdown
        * `icon`: icon of the main menu dropdown, exclusive vs. `main_menu_image`
        * `image`: image of the main menu dropdown, exclusive vs. `main_menu_icon`
      * `announcements`: list of objects that contain data for the announcement banner, if one is active
        * `[]` if None active, else a list `[{"text": "'"<str> Announcement text", "level": "<str> level-code"}, ...]`
        * `level` can take the following values: "debug", "info", "success", "warning", "error". these levels are
            usually reflected in the color of the announcement background
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )

    # endpoint param
    url = None

    # set during processing
    django_request = None
    group = None
    has_leftnav = True  # can be toggled during HTML parsing to determine that this page has no leftnav

    # some return values
    content_html = None
    footer_html = None
    main_menu_label = None
    main_menu_icon = None
    main_menu_image = None

    _data_proto = {
        'resolved_url': None,
        'redirect': False,
        'status_code': 0,
        'content_html': None,
        'footer_html': None,
        'js_vendor_urls': [],
        'js_urls': [],
        'script_constants': [],
        'scripts': [],
        'css_urls': [],
        'meta': None,
        'styles': None,
        'sub_navigation': None,  # can be None if no left navigation should be shown
        'main_menu': {
            'label': None,  # either <name of group>, "personal space", or "community"
            'icon': None,  # exclusive with `main_menu_image`, only one can be non-None!
            'image': None,  # exclusive with `main_menu_icon`, only one can be non-None!
        },
        'announcements': [],
    }

    # todo: generate proper response, by either putting the entire response into a
    #       Serializer, or defining it by hand
    #       Note: Also needs docs on our custom data/timestamp/version wrapper!
    # see:  https://drf-yasg.readthedocs.io/en/stable/custom_spec.html
    # see:  https://drf-yasg.readthedocs.io/en/stable/drf_yasg.html?highlight=Response#drf_yasg.openapi.Schema
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'url',
                openapi.IN_QUERY,
                required=True,
                description='The URL for which the content should be returned.',
                type=openapi.FORMAT_URI,
            ),
        ],
        responses={
            '200': openapi.Response(
                description='WIP: Response info missing. Short example included',
                examples={
                    'application/json': {
                        'data': {
                            'resolved_url': '/project/a-mein-bbb-projekt/?force_payment_popup=1',
                            'redirect': False,
                            'status_code': 200,
                            'content_html': (
                                '<div class="x-v3-container container"> <div class="row app-main"> ... </div></div>'
                            ),
                            'footer_html': '<div class="footer"> ... </div>',
                            'js_vendor_urls': [
                                '/static/js/vendor/less.min.js',
                                '/static/js/vendor/jquery-2.1.0.min.js',
                            ],
                            'js_urls': [
                                'http://localhost:8000/static/js/cosinnus.js?v=1.9.3',
                                'http://localhost:8000/static/js/client.js?v=1.9.3',
                            ],
                            'css_urls': [
                                '/static/css/select2.css',
                                '/static/css/extra.css',
                            ],
                            'script_constants': (
                                'var cosinnus_base_url = "http://localhost:8000/";\n'
                                'var cosinnus_active_group = "a-mein-bbb-projekt";\n ...'
                            ),
                            'scripts': "Backbone.mediator.publish('init:module-full-routed', ...",
                            'meta': (
                                '<meta charset="utf-8"/><meta content="IE=edge" http-equiv="X-UA-Compatible"/>'
                                '<meta content="width=device-width, initial-scale=1" name="viewport"/> ...'
                            ),
                            'styles': (
                                '.my-contribution-badge {min-width: 50px;border-radius: 20px;color: #FFF;font-size: '
                                '12px;padding: 2px 6px; margin-left: 5px;}.my-contribution-badge.red '
                                '{background-color: rgb(245, 85, 0);} ...'
                            ),
                            'sub_navigation': {
                                'top': [
                                    {
                                        'id': 'Sidebar-pws2dgLA',
                                        'icon': 'fa-lightbulb-o',
                                        'label': 'Microsite',
                                        'url': '/project/a-mein-bbb-projekt/microsite/',
                                        'is_external': FONT_AWESOME_CLASS_FILTER,
                                        'image': None,
                                        'badge': None,
                                    }
                                ],
                                'middle': [
                                    {
                                        'id': 'Sidebar-FTZD61ZZ',
                                        'icon': 'fa-th-large',
                                        'label': 'Projektdashboard',
                                        'url': '/project/a-mein-bbb-projekt/?browse=true',
                                        'is_external': False,
                                        'image': None,
                                        'badge': None,
                                    },
                                ],
                                'bottom': [
                                    {
                                        'id': 'Sidebar-6vcO7aYp',
                                        'icon': 'fa-cogs',
                                        'label': 'Einstellungen',
                                        'url': '/project/a-mein-bbb-projekt/edit/',
                                        'is_external': False,
                                        'image': None,
                                        'badge': None,
                                    },
                                ],
                            },
                            'main_menu': {
                                'label': 'A Mein BBB Projekt',
                                'icon': None,
                                'image': (
                                    '/media/cosinnus_portals/portal_saschas_local_dev/avatars/group/xj1VxzF3viA4.jpg'
                                ),
                            },
                            'announcements': [{'text': 'This is an example announcement', 'level': 'warning'}],
                        },
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            )
        },
    )
    def get(self, request):
        self.url = request.query_params.get('url', '').strip()
        self.url = remove_url_param(self.url, 'v', '3')
        self.django_request = copy(request._request)
        if not self.url:
            raise ValidationError('Missing required parameter: url')
        if not self.url.startswith('http'):
            if not self.url.startswith('/'):
                self.url = '/' + self.url
            self.url = CosinnusPortal.get_current().get_domain() + self.url

        # check if the target URL is one exempted for v3 frontend resolution - we do not accept those
        _parsed = urlparse(self.url)
        target_url_path = _parsed.path
        target_url_query = QueryDict(_parsed.query)
        # append slash since with a missing resolver it wouldn't be auto appended and might miss matches
        if not target_url_path.endswith('/'):
            target_url_path += '/'
        if check_url_v3_everywhere_exempt(target_url_path, request):
            return self.build_redirect_response(self.url)

        # check if we have a redirected request where `FrontendMiddleware` saved the response
        cached_response = self._get_valid_cached_response(self.django_request, target_url_path, target_url_query)
        if cached_response:
            # use the response from the cache key
            response = cached_response
            # for some response types like TemplateResponse or HttpResponseForbidden that we receive during `usecached`
            # mode, we patch on properties we expect later on so they can be accessed like a requests response
            if getattr(response, 'url', None) is None:
                setattr(response, 'url', self.url)
            if getattr(response, 'text', None) is None:
                setattr(response, 'text', getattr(response, 'content', ''))
        else:
            # resolve the response by querying with a request, including redirects
            response = self._resolve_url_via_query(self.url, self.django_request, allow_redirects=False)

        # if we have been redirected, return an empty data package with a redirect target url!
        if response.status_code in [301, 302]:
            # remove the v3-exempt parameter from the resolved URL again
            redirect_target_url = remove_url_param(
                response.headers['Location'], FrontendMiddleware.param_key_exempt, FrontendMiddleware.param_value_exempt
            )
            return self.build_redirect_response(redirect_target_url, response)

        # fake our django request to act as if the resolved url was the original one
        self.django_request = self._transform_request_to_resolved(self.django_request, response.url)
        # get the relative resolved url from the target url (following all redirects)
        resolved_url = self.django_request.path
        if self.django_request.GET:
            resolved_url += '?' + self.django_request.GET.urlencode()
            # remove the v3-exempt parameter from the resolved URL again
            resolved_url = remove_url_param(
                self.url, FrontendMiddleware.param_key_exempt, FrontendMiddleware.param_value_exempt
            )
        # remove domain from resolved url
        resolved_url = '/' + '/'.join(resolved_url.split('/')[3:])

        # determine group for request
        self._resolve_request_group(resolved_url, self.django_request)
        # parse the response's html
        html = self._clean_response_html(force_str(response.text))

        # TODO compress html? or do server-side request compression?

        html_soup = BeautifulSoup(html, 'html.parser')  # might try out 'html5lib' as alternate parser but it is slower
        parsed_js_urls = self._parse_js_urls(html_soup)
        js_vendor_urls = [js_url for js_url in parsed_js_urls if '/vendor/' in js_url]
        js_urls = [js_url for js_url in parsed_js_urls if '/vendor/' not in js_url]
        css_urls = self._parse_css_urls(html_soup)
        script_constants = self._parse_inline_tag_contents(html_soup, 'script', class_='v3-constants')
        scripts = self._parse_inline_tag_contents(html_soup, 'script', class_=False)
        meta = self._parse_tags(html_soup, 'meta')
        styles = self._parse_inline_tag_contents(html_soup, 'style')
        sub_navigation = self._parse_leftnav_menu(html_soup)

        html_soup = self._filter_html_view_specific(html_soup, resolved_url)
        # this sets self.content_html and self.footer_html
        self._parse_html_content(html_soup)  # this will destroy the soup, so use it last or on a new soup!

        data = copy(self._data_proto)
        data['resolved_url'] = resolved_url
        data['redirect'] = False
        data['status_code'] = response.status_code
        data['content_html'] = self.content_html
        data['footer_html'] = self.footer_html
        data['js_vendor_urls'] = js_vendor_urls
        data['js_urls'] = js_urls
        data['script_constants'] = script_constants
        data['scripts'] = scripts
        data['css_urls'] = css_urls
        data['meta'] = meta
        data['styles'] = styles
        data['sub_navigation'] = sub_navigation  # can be None if no left navigation should be shown
        data['main_menu'] = {
            'label': self.main_menu_label,  # either <name of group>, "personal space", or "community"
            'icon': self.main_menu_icon,  # exclusive with `main_menu_image`, only one can be non-None!
            'image': self.main_menu_image,  # exclusive with `main_menu_icon`, only one can be non-None!
        }
        data['announcements'] = self._get_announcements(self.django_request)

        # set cookies on rest response from the requests response
        # note: we seem to be losing all meta-infos like max-age here,
        #   but none of the cookies returned through this endpoint should be relevant for this.
        return self.build_data_response(data, response)

    def build_data_response(self, data, resolved_response=None):
        """Build a response from the given data package and set the cookies from the resolved target URL query."""
        rest_response = Response(data)
        if resolved_response is not None:
            for cookie in resolved_response.cookies:
                rest_response.set_cookie(
                    cookie.name,
                    value=cookie.value,
                    expires=cookie.expires,
                    path=cookie.path,
                    domain=cookie.domain,
                    secure=cookie.secure,
                )
        return rest_response

    def build_redirect_response(self, target_url, resolved_response=None):
        """Builds an empty data package with the `redirect` flag set to True and
        `resolved_url` set to the target redirect URL."""
        data = copy(self._data_proto)
        data['resolved_url'] = target_url
        data['redirect'] = True
        data['status_code'] = resolved_response.status_code if resolved_response else 302
        return self.build_data_response(data, resolved_response)

    def _get_valid_cached_response(self, request, target_url_path, target_url_query):
        """Checks if there is a cache id in the GET params, and if the cache packet exists and it is a valid one and
        it matches the request's target URL, return the cached response instead.
        For infos on what this does, check the explanation in `FrontendMiddleware.process_response`."""
        # we accept the cache id as param attached to both the v3 main content api or the target url
        cache_id = request.GET.get(FrontendMiddleware.cached_content_key, None)
        if not cache_id:
            cache_id = target_url_query.get(FrontendMiddleware.cached_content_key, None)
        if not cache_id:
            return None
        cached_response_packet = cache.get(FrontendMiddleware.FRONTEND_V3_POST_CONTENT_CACHE_KEY % cache_id)
        if not cached_response_packet:
            return None
        # check validity: must match session_key and url path
        if not cached_response_packet['session_key'] == request.session.session_key:
            return None
        if not cached_response_packet['target_url_path'] == target_url_path:
            return None
        # delete cache entry, we can only use a response once
        cache.delete(FrontendMiddleware.FRONTEND_V3_POST_CONTENT_CACHE_KEY % cache_id)
        return cached_response_packet['response']

    def _resolve_url_via_query(self, url, request, allow_redirects=False):
        """Resolves the URL via a requests get().
        Cookies from all redirect steps are passed along collectively."""
        # add the v3-exempt parameter to the URL so we do not actually parse the v3-served response
        v3_exempted_url = add_url_param(url, FrontendMiddleware.param_key_exempt, FrontendMiddleware.param_value_exempt)
        session = requests.Session()
        session.headers.update(dict(request.headers))
        session.cookies.update(request.COOKIES)
        response = session.get(v3_exempted_url, allow_redirects=allow_redirects)
        for history_response in response.history:
            response.cookies.update(history_response.cookies)
        return response

    def _transform_request_to_resolved(self, request, url):
        """Fake a given request with a new given url so that it seems that the request aimed
        at the given url."""
        parsed = urlparse(url)
        path = parsed.path
        query = parsed.query
        # fudge request to act like the client sent it to the given URL
        request.path = path
        request.path_info = path
        request.resolver_match
        request.GET = QueryDict(query)
        request.META['PATH_INFO'] = path
        request.META['QUERY_STRING'] = query
        request.environ['PATH_INFO'] = path
        request.environ['QUERY_STRING'] = query
        return request

    def _clean_response_html(self, html):
        html = html.replace('\t', '')
        html = re.sub(r'[ \t]+', ' ', html)
        return html

    def _resolve_request_group(self, url, request):
        """Determine and set the group for the request via the resolved group and url
        and also set properties like main menu label and icon depending on this.
        Sets:
            - self.main_menu_label
            - self.main_menu_icon
            - self.main_menu_image
        """
        try:
            # resolve the group if the requested view is part of one
            group_name = url.split('/')[2]
            self.group = get_group_for_request(group_name, request, fail_silently=True)
        except Exception:
            # this catches short URLs and the Http404 that `get_group_for_request` raised when no group is found
            self.group = None

        # determine menu labels/image
        if self.group:
            self.main_menu_label = self.group['name']
            if self.group.avatar_url:
                self.main_menu_image = self.group.get_avatar_thumbnail_url()
            else:
                self.main_menu_icon = self.group.trans.ICON

        # match personal dashboard
        if not self.main_menu_label and url.startswith(reverse('cosinnus:user-dashboard')):
            self.main_menu_label = _('Personal Dashboard')
            if self.request.user.cosinnus_profile.avatar_url:
                self.main_menu_image = self.request.user.cosinnus_profile.get_avatar_thumbnail_url()
            else:
                self.main_menu_icon = 'fa-user'

        # match map
        if not self.main_menu_label and url.startswith(reverse('cosinnus:map')):
            self.main_menu_label = settings.COSINNUS_V3_MENU_SPACES_MAP_LABEL
            self.main_menu_icon = 'fa-map'

        # match additional community space links
        if not self.main_menu_label and settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS:
            for __, link_label, link_url, link_icon in settings.COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS:
                if url.startswith(str(link_url)):
                    self.main_menu_label = link_label
                    self.main_menu_icon = link_icon

        # unmatched urls get the "Go to" label
        if not self.main_menu_label:
            self.main_menu_label = _('Go To...')
            self.main_menu_icon = 'fa-arrow-right'

    def _filter_html_view_specific(self, html_soup, resolved_url):
        """Will alter the given html soup by specific, hardcoded view/url/page rules,
        for fine-grained control on hiding/modifying elements when displayed in the main content view"""
        # remove params from url for matching
        url = remove_url_param(self.url, None, None)  # noqa
        if self.group:
            # hide appsmenu on specific group pages
            hide_appsmenu_patterns = [
                r'^/(?P<group_type>[^/]+)/(?P<group_slug>[^/]+)/$',  # group dashboard page
                r'^/(?P<group_type>[^/]+)/(?P<group_slug>[^/]+)/microsite/$',  # group  microsite
            ]
            if any([re.match(pattern, resolved_url) for pattern in hide_appsmenu_patterns]):
                appsmenu_tag = html_soup.find('div', class_='x-v3-leftnav')
                if appsmenu_tag:
                    appsmenu_tag.decompose()
            # do not display group dashboard tiles
            hide_dashboard_tiles_patterns = [
                r'^/(?P<group_type>[^/]+)/(?P<group_slug>[^/]+)/$',  # group dashboard page
            ]
            if any([re.match(pattern, resolved_url) for pattern in hide_dashboard_tiles_patterns]):
                tile_tags = html_soup.find_all('div', class_='dashboard-header-link')
                for tile_tag in tile_tags:
                    tile_tag.decompose()

        return html_soup

    def _parse_html_content(self, destructible_html_soup):
        """Parses the content frame of the full html that can be put into any other part of the site.
        May do some reformatting for full-page views to transform the body tag into a div.
        Also parses the footer html content.
        Sets:
            - self.has_leftnav
            - self.content_html
            - self.footer_html
        Note: this will permanently alter the soup given!"""
        soup = destructible_html_soup
        # remove all tags we never want to see in the content, like inline scripts and styles
        for bad_tag_literal in ['nav', 'script', 'style']:
            for bad_tag in soup.find_all(bad_tag_literal):
                bad_tag.decompose()

        # parse footer and remove it
        footer = soup.find('div', class_='x-v3-footer')
        if footer:
            self.footer_html = str(footer.decode_contents()).strip()
            footer.decompose()

        # try to extract our page's inner container, below the breadcrumb
        content = soup.find('div', class_='x-v3-content')
        if not content:
            # if that doesn't exist, try to extract the outer container
            content = soup.find('div', class_='x-v3-container')

        if content:
            self.content_html = str(content or '').strip()
        else:
            # if even that doesn't exist, return the content of the body tag, minus all <nav> tags
            self.has_leftnav = False
            content = soup.find('body')
            if content:
                self.content_html = str(content.decode_contents()).strip()
            else:
                content = soup
                self.content_html = str(content or '').strip()

        # if the report modal is not in the content (i.e. because we extracted only the x-v3-content or a part where
        # the report modal isn't contained), add it from the main soup
        if not content.find('div', class_='x-v3-report-modal'):
            modal_content = soup.find('div', class_='x-v3-report-modal')
            if modal_content:
                self.content_html += '\n' + str(modal_content or '').strip()

        # add any modal boxes from the leftnav to the main content html
        if self.has_leftnav:
            leftnav = soup.find('div', class_='x-v3-leftnav')
            if leftnav:
                popup_modals = [
                    pop for pop in leftnav.find_all('div') if pop.get('class') and 'modal' in pop.get('class')
                ]
                for popup_modal in popup_modals:
                    self.content_html += '\n' + str(popup_modal)

    def _extract_fa_icon(self, tag):
        """Extracts the actual font-awesome icon class name from the first i tag within the given tag tree"""
        fa_class = 'fa-group'  # fallback for icons that do not have one
        # TODO: add a better fallback! for example http://localhost:8000/api/v3/content/main/?url=http://localhost:8000/group/forum/event/list/
        # on the leftnav is missing icons for links with numbers in them!
        fa_i = tag.find('i')
        if fa_i:
            fa_class = ' '.join(
                [subclass for subclass in fa_i.get('class') if subclass.lower() not in FONT_AWESOME_CLASS_FILTER]
            )
        return fa_class

    def _create_menu_items_from_html(self, html_soup):
        """Extracts a menu_item from all proper links contained in the given HTML soup,
        with a heuristic for icons/labels.
        Possible HTML properties on buttons that are v3-specific and change button behaviour:
            - attribute "data-v3-id": if present the button needs to href to be included and its returned id property
                is set to it
            - attribute "data-toggle" in combination with "data-target": bootstrap modal buttons are included and
                these two attributes are passed along in the "attributes" attribute
            - CSS classes "x-v3-leftnav-action-button", "x-v3-leftnav-action-target-active-app",
                and "x-v3-leftnav-action-target-active-subitem" signify that these leftnav items are action buttons
                that appear as context menu buttons on another leftnav button.
                - "x-v3-leftnav-action-target-active-app" directs that the action button should be rendered on the
                    current active app's app button in the v3 frontend
                - "x-v3-leftnav-action-target-active-subitem" directs the target button id on which the context menu
                    should be rendered in the v3 frontend
            - attribute "data-v3-parent": only in conjunction with CSS class "x-v3-leftnav-action-target-active-subitem"
                (see above)
        """
        if not html_soup:
            return []
        menu_items = []
        for leftnav_link in html_soup.find_all(['a', 'button']):
            attributes = {}
            # detect bootstrap-modal attribues
            if leftnav_link.get('data-toggle') and leftnav_link.get('data-target'):
                attributes.update(
                    {'data-toggle': leftnav_link.get('data-toggle'), 'data-target': leftnav_link.get('data-target')}
                )
            # extract v3-specific id if present
            v3_id = leftnav_link.get('data-v3-id', None)
            # skip link-less buttons (like the dropdown trigger), unless they have modal data attributes
            href = leftnav_link.get('href')
            if not href and not attributes and not v3_id:
                continue
            # ignore some links depending on their class
            if leftnav_link.get('class') and any(
                [blacklisted_class in leftnav_link.get('class') for blacklisted_class in ['fadedown-clickarea']]
            ):
                continue
            link_label = '(Link)'
            text_source = leftnav_link.find('div', class_='media-body') or leftnav_link
            if text_source:
                parsed_label = text_source.text.strip().replace('/n', '')
                if not parsed_label:
                    # check for an additional span within the media-body
                    parsed_label = text_source.get('title')
                    if parsed_label:
                        parsed_label = parsed_label.strip().replace('/n', '')
                if parsed_label:
                    link_label = parsed_label
            link_label = clean_single_line_text(link_label)

            # a button counts as selected item if there is an `<i class="fa fa-caret-right"></i>` in it
            selected = (
                len(
                    [
                        lnk
                        for lnk in leftnav_link.find_all('i')
                        if lnk.get('class') and 'fa-caret-right' in lnk.get('class')
                    ]
                )
                > 0
            )
            # we initialize a sub_item list for other buttons to be sorted in if the link is an <a.active> tag from the
            # appsmenu
            sub_items = None
            if (
                leftnav_link.name == 'a'
                and leftnav_link.parent
                and leftnav_link.parent.get('class')
                and 'active' in leftnav_link.parent.get('class')
            ):
                sub_items = []

            menu_item = None
            # create a hardcoded menu item for specific `data-v3-id` values
            if v3_id:
                menu_item = self._generate_hardcoded_menu_item_by_id(v3_id)
            # create menu item for the link
            if not menu_item:
                menu_item = MenuItem(
                    link_label,
                    url=href if href else None,
                    icon=self._extract_fa_icon(leftnav_link),  # TODO. filter/map-convert these icons to frontend icons?
                    id=v3_id or ('Sidebar-' + get_random_string(8)),
                    is_external=bool(leftnav_link.get('target', None) == '_blank'),
                    sub_items=sub_items,
                    selected=selected,
                    attributes=attributes if attributes else None,
                )
            # attach the id, CSS classes, and data-target to the menu item for internal use
            setattr(menu_item, '_original_id', leftnav_link.get('id', None))
            setattr(menu_item, '_original_css_class', leftnav_link.get('class', []))
            setattr(menu_item, '_original_data_target', leftnav_link.get('data-target', None))
            setattr(menu_item, '_original_data_parent', leftnav_link.get('data-v3-parent', None))
            menu_items.append(menu_item)
        return menu_items

    def _generate_hardcoded_menu_item_by_id(self, v3_id):
        """For some leftnav menu items, we set a placeholder in the leftnav html with a specific
        e.g. `data-v3-id="ChangeLanguage"` and instead of parsing them from the HTML, we generate them
        pythonically in this method, depending on their v3-id.
        @return a `MenuItem` if the supplied v3_id is known, None if not.
        """
        # generate "Change Language" Button with a submenu from mixin `LanguageMenuItemMixin`
        if v3_id == 'ChangeLanguage':
            return self.get_language_menu_item(self.django_request)
        return None

    def _parse_leftnav_menu(self, html_soup):
        """Tries to parse from the leftnav all links to show in the left sub navigation.
        Can return None if the sidebar should not be shown at all."""
        if not self.has_leftnav:
            return None

        leftnav = html_soup.find('div', class_='x-v3-leftnav')
        leftnav_appsmenu = None
        leftnav_buttons = None
        if leftnav:
            leftnav_appsmenu = leftnav.find('div', class_='x-v3-leftnav-appsmenu')
            leftnav_buttons = leftnav.find('div', class_='x-v3-leftnav-buttons')
        if not leftnav_appsmenu and not leftnav_buttons:
            self.has_leftnav = False
            return None

        # TODO: extract appsmenu buttons and detect which one is active, then extract the buttons-area buttons into
        # that button as sub_items.

        top = []
        middle = []
        bottom = []
        middle_from_buttons_area = []

        # extract appsmenu links (<a>) AND leftnav elements (<button>) from the leftnav,
        # because the beautifulsoup filters apply to both
        appsmenu_items = self._create_menu_items_from_html(leftnav_appsmenu)
        buttons_items = self._create_menu_items_from_html(leftnav_buttons)

        # find the first appsmenu menu_item with sub_items initialized (the active menu item):
        active_menu_item = next((item for item in appsmenu_items if item.get('sub_items') is not None), None)
        # if no selected item has been marked in the buttons area items (the one carrying a caret-right),
        # mark the active appsmenu item active if it exists
        selected_menu_item = next((item for item in buttons_items if item.get('selected', False)), None)
        if not selected_menu_item and active_menu_item:
            active_menu_item['selected'] = True

        # deduplicate menu items by removing all elements beyond the first that have the same label+href
        label_href_hashes = []

        def _check_unique_and_remember(menu_item):
            hash = (
                menu_item['label'] + '|' + (menu_item.get('url') or getattr(menu_item, '_original_data_target') or '-')
            )
            if hash in label_href_hashes:
                return False
            label_href_hashes.append(hash)
            return True

        appsmenu_items = [item for item in appsmenu_items if _check_unique_and_remember(item)]
        buttons_items = [item for item in buttons_items if _check_unique_and_remember(item)]

        # sort items from the two leftnav areas into the three v3 leftnav areas
        def _sort_menu_items(menu_items, default_target):
            # picks a spot for the given items, with a given default target if no other rules apply
            for menu_item in menu_items:
                target_subnav = default_target
                # select the proper subnav for this menu to go to, by type of URL
                if 'x-v3-leftnav-action-button' in [
                    subclass for subclass in getattr(menu_item, '_original_css_class', [])
                ]:
                    # action menu buttons are sorted into the actions sublist of a menu item depending on their target
                    if 'x-v3-leftnav-action-target-active-app' in [
                        subclass for subclass in getattr(menu_item, '_original_css_class', [])
                    ]:
                        active_menu_item['actions'] = active_menu_item.get(
                            'actions', []
                        )  # make sure actions list exists
                        target_subnav = active_menu_item['actions']
                    elif 'x-v3-leftnav-action-target-active-subitem' in [
                        subclass for subclass in getattr(menu_item, '_original_css_class', [])
                    ]:
                        # find the MenuItem from the buttons_items menu that has the original html id of this
                        # action button target (for example, the Etherpad folder button as parent for its "edit folder"
                        # action context button)
                        action_target_parent_id = getattr(menu_item, '_original_data_parent', None)
                        if action_target_parent_id:
                            for find_target_button in buttons_items:
                                if getattr(find_target_button, '_original_id', None) == action_target_parent_id:
                                    find_target_button['actions'] = find_target_button.get(
                                        'actions', []
                                    )  # make sure actions list exists
                                    target_subnav = find_target_button['actions']
                elif not menu_item['url']:
                    # non url buttons like help popups go in the bottom list
                    target_subnav = bottom
                elif any(re.match(pattern, menu_item['url']) for pattern in V3_CONTENT_BOTTOM_SIDEBAR_URL_PATTERNS):
                    target_subnav = bottom
                elif any(re.match(pattern, menu_item['url']) for pattern in V3_CONTENT_TOP_SIDEBAR_URL_PATTERNS):
                    target_subnav = top
                target_subnav.append(menu_item)

        _sort_menu_items(appsmenu_items, middle)
        _sort_menu_items(buttons_items, middle_from_buttons_area)

        # special case: if we have an active navigation item in the appsmenu, we are in a subpage of that area,
        #     so we sort all links from the leftnav buttons area as sub items for that navigation item
        #     otherwise we just list them after the other middle items
        if active_menu_item:
            active_menu_item['sub_items'].extend(middle_from_buttons_area)
        else:
            middle.extend(middle_from_buttons_area)

        # add sidebar third party tools if it exists in group data
        if self.group and self.group.third_party_tools:
            for third_party_tool in self.group.third_party_tools:
                try:
                    middle.append(
                        MenuItem(
                            third_party_tool['label'],
                            third_party_tool['url'],
                            icon='fa-external-link',
                            id='Sidebar-Thirdparty-' + get_random_string(8),
                            is_external=True,
                        )
                    )
                except Exception as e:
                    logger.warning('Error converting a thirdparty group menu item to MenuItem', extra={'exc': e})

        if not top and not middle and not bottom:
            return None
        sub_nav = {
            'top': top,
            'middle': middle,
            'bottom': bottom,
        }
        return sub_nav

    def _parse_css_urls(self, html_soup):
        css_links = html_soup.find_all('link', rel='stylesheet')
        css_urls = [link.get('href') for link in css_links]
        css_urls = [self._format_static_link(link) for link in css_urls]
        css_urls = uniquify_list(css_urls)
        return css_urls

    def _parse_js_urls(self, html_soup):
        # this
        js_links = html_soup.find_all('script', src=True)
        js_urls = [link.get('src') for link in js_links]
        js_urls = [self._format_static_link(link) for link in js_urls]
        js_urls = uniquify_list(js_urls)
        return js_urls

    def _parse_tags(self, html_soup, tag_name):
        """Parses all tags of a given tag name and returns them, including their tag definition,
        as a concatenated string"""
        tags = html_soup.find_all(tag_name)
        tag_str = '\n'.join([str(tag).strip() for tag in tags])
        return tag_str

    def _parse_inline_tag_contents(self, html_soup, tag_name, class_=False):
        """Parses all contents of tags of a given tag name and returns it as a concatenated string"""
        # and this
        tags = html_soup.find_all(tag_name, src=False, rel=False, class_=class_)
        liss = [tag.decode_contents().strip() for tag in tags]
        tag_contents = '\n'.join(liss)
        return tag_contents

    def _format_static_link(self, link):
        domain = CosinnusPortal.get_current().get_domain()
        link = (domain if not link.startswith('http') else '') + link
        if '?v=' in link:
            link = link[: link.find('?v=')]
        return link

    def _get_announcements(self, request):
        announcements = []
        for announcement in Announcement.objects.active():
            announcements.append(
                {
                    'text': announcement.translated_text or announcement.text,
                    'level': announcement.level,
                }
            )
        # check extra email-verified and guest user announcements
        context = email_verified_context_processor(request)
        if 'email_not_verified_announcement' in context:
            announcements.append(context['email_not_verified_announcement'])
        if 'user_guest_announcement' in context:
            announcements.append(context['user_guest_announcement'])
        return announcements

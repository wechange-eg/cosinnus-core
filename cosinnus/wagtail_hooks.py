# -*- coding: utf-8 -*-

from builtins import str
from builtins import object
from django.conf.urls import url
from django.urls import reverse
from django.utils.html import format_html

from wagtail.core import hooks
from wagtail.core.whitelist import attribute_rule
from django.conf import settings
from django.templatetags.static import static

from wagtail.admin.rich_text.converters.editor_html import WhitelistRule
from wagtail.core.whitelist import allow_without_attributes
from wagtail.admin.menu import MenuItem

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from cosinnus.utils.import_utils import csv_import_projects,\
    EmptyOrUnreadableCSVContent, UnexpectedNumberOfColumns,\
    GROUP_IMPORT_RESULTS_CACHE_KEY, GROUP_IMPORT_RUNNING_CACHE_KEY,\
    GROUP_IMPORT_PROGRESS_CACHE_KEY, ImportAlreadyRunning
    
import logging
from django.core.cache import cache
from cosinnus.utils.permissions import check_user_portal_admin
from django.http.response import HttpResponseForbidden
from django.core.exceptions import ImproperlyConfigured
logger = logging.getLogger('cosinnus')

# swap this to re-enable translating these internal strings
# (we didn't do this to save translator work for admin pages)
#from django.utils.translation import gettext_lazy as _
dotrans_ = str



@hooks.register('insert_editor_js')
def enable_source():
    return format_html(
        """
        <script>
          registerHalloPlugin('hallojustify');
          registerHalloPlugin('hallohtml');
          // replaces non-existant HTML button icon
          $('body').on('halloactivated', function(){{ 
              $('.icon-list-alt').addClass('icon-code').removeClass('icon-list-alt'); 
          }});
        </script>
        """
    )

@hooks.register('insert_editor_css')
def editor_css():
    css_string = '<link rel="stylesheet" href="%s">' % static('css/vendor/font-awesome.min.css')
    if settings.DEBUG:
        css_string += '<link rel="stylesheet/less" href="%s">' % static('less/cosinnus.less')
        css_string += '<script src="%s"></script>' % static('js/vendor/less.min.js')
    else:
        css_string += '<link rel="stylesheet" href="%s">' % static('css/cosinnus.css')
    return format_html(css_string)

def allow_all_attributes(attribute_value):
    class Fn_get_true(object):
        def get(self, *args, **kwargs):
            return True
    return attribute_rule(Fn_get_true())


@hooks.register('register_rich_text_features')
def all_tags_features(features):

    allowed_tags = ['iframe',
        'small',
        '[document]',
        'a',
        'b',
        'br',
        'div',
        'em',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'hr',
        'i',
        'img',
        'li',
        'ol',
        'p',
        'strong',
        'sub',
        'sup',
        'ul',
    ]
    
    for html_tag in allowed_tags:
        # register a feature 'blockquote' which whitelists the <blockquote> element
        features.register_converter_rule('editorhtml', html_tag, [
            WhitelistRule(html_tag, allow_without_attributes),
        ])
        # add 'blockquote' to the default feature set
        features.default_features.append(html_tag)



if settings.COSINNUS_IMPORT_PROJECTS_PERMITTED:
    
    @csrf_protect
    def import_project_view(request):
        if not (request.user.is_superuser or check_user_portal_admin(request.user)):
            return HttpResponseForbidden()
        
        debug = '-'
        import_running = cache.get(GROUP_IMPORT_RUNNING_CACHE_KEY)
        import_results = cache.get(GROUP_IMPORT_RESULTS_CACHE_KEY)
            
        
        if not import_running and request.method == 'POST':
            if request.POST.get('trigger_new_import', False):
                cache.delete(GROUP_IMPORT_RESULTS_CACHE_KEY)
                return redirect(reverse('import-projects'))
            elif import_results:
                messages.success(request, dotrans_('An import has just finished. Please click the "Start a new import" button to start a new one!'))
            else:
                csv_file_groups = request.FILES.get('csv_upload_groups', None)
                csv_file_users = request.FILES.get('csv_upload_users', None)
                
                if csv_file_groups and csv_file_users:
                    messages.error(request, dotrans_('You uploaded a CSV file for both projects/groups AND users! Please only upload one file to import at a time!'))
                elif not (csv_file_groups or csv_file_users):
                    messages.error(request, dotrans_('You did not upload a CSV file or something went wrong during the upload!'))
                else:
                    csv_file = csv_file_groups or csv_file_users
                    import_type = 'groups' if csv_file_groups else 'users'
                    
                    encoding = request.POST.get('encoding', "utf-8")
                    delimiter = request.POST.get('delimiter', ',')
                    delimiter = str(delimiter)[0]
                    
                    try:
                        debug = csv_import_projects(csv_file, request=request, encoding=encoding, delimiter=delimiter, import_type=import_type)
                        messages.success(request, dotrans_('The CSV file was read successfully! You will be notified by email when it completes.'))
                        import_running = True
                    except (UnicodeDecodeError, UnicodeError):
                        messages.error(request, dotrans_('The CSV file you supplied is not formatted in the proper encoding (%s)!' % encoding))
                    except EmptyOrUnreadableCSVContent:
                        messages.error(request, dotrans_('The CSV file you supplied was empty or not formatted in the proper encoding (%(encoding)s) or with a wrong delimiter (%(delimiter)s)!' % {'encoding':encoding, 'delimiter':delimiter}))
                    except UnexpectedNumberOfColumns as e:
                        messages.error(request, dotrans_('One or more rows in the CSV file you supplied contained less columns than expected (%s)! Either the file was read in a wrong encoding, or the file was using a different format than the server expected.' % str(e)))
                    except ImportAlreadyRunning:
                        messages.error(request, dotrans_('Another import is currently running! Please wait till that one is finished.'))
                    except ImproperlyConfigured as e:
                        messages.error(request, dotrans_('A CSV configuration error occured, has the CSV format changed?. Message was: %s') % str(e))
                    except Exception as e:
                        messages.error(request, dotrans_('There was an unexpected error when reading the CSV file! Please make sure the file is properly formatted. If the problem persists, please contact an administrator!'))
                        logger.warn('A CSV file uploaded for import encountered an unexpected error! The exception was: "%s"' % str(e), extra={'encoding_used': encoding, 'delimiter_used': delimiter})
                        if getattr(settings, 'DEBUG_LOCAL', False):
                            raise
        
        context = {
            'site_name': settings.WAGTAIL_SITE_NAME,
            'panels': [],
            'user': request.user,
        }
        if import_running and request.GET.get('force_stop', None):
            # enables clearing the cache if the thread has stopped, like after a server reboot during import
            import_running = False
            cache.delete(GROUP_IMPORT_RUNNING_CACHE_KEY)
            template = "cosinnus/wagtail/wagtailadmin/import_projects.html"
        if import_running:
            import_progress = cache.get(GROUP_IMPORT_PROGRESS_CACHE_KEY, 0)
            context.update({'import_progress': import_progress})
            template = "cosinnus/wagtail/wagtailadmin/import_projects_running.html"
        elif import_results:
            context.update({'import_results': import_results})
            template = "cosinnus/wagtail/wagtailadmin/import_projects_results.html"
        else:
            template = "cosinnus/wagtail/wagtailadmin/import_projects.html"
            
        return render(request, template, context)
    
    @hooks.register('register_admin_urls')
    def urlconf_time():
        return [
            url(r'^import_projects/$', import_project_view, name='import-projects' ),
        ]
    
    class ImportProjectsMenutItem(MenuItem): 
        def is_shown(self, request):
            return settings.COSINNUS_IMPORT_PROJECTS_PERMITTED
        
    @hooks.register('register_admin_menu_item')
    def register_import_menu_item():
        return ImportProjectsMenutItem(dotrans_('Import'), reverse('import-projects'), classnames='icon icon-plus', order=1005)


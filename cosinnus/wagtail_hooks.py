# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.utils.html import format_html

from wagtail.wagtailcore import hooks
from wagtail.wagtailcore.whitelist import attribute_rule
from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static


from wagtail.wagtailadmin.menu import MenuItem

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
#from django.utils.translation import ugettext_lazy as _
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

@hooks.register('construct_whitelister_element_rules')
def whitelister_element_rules():
    return {
        'iframe': allow_all_attributes,
        'small': allow_all_attributes,
        
        '[document]': allow_all_attributes,
        'a': allow_all_attributes,
        'b': allow_all_attributes,
        'br': allow_all_attributes,
        'div': allow_all_attributes,
        'em': allow_all_attributes,
        'h1': allow_all_attributes,
        'h2': allow_all_attributes,
        'h3': allow_all_attributes,
        'h4': allow_all_attributes,
        'h5': allow_all_attributes,
        'h6': allow_all_attributes,
        'hr': allow_all_attributes,
        'i': allow_all_attributes,
        'img': allow_all_attributes,
        'li': allow_all_attributes,
        'ol': allow_all_attributes,
        'p': allow_all_attributes,
        'strong': allow_all_attributes,
        'sub': allow_all_attributes,
        'sup': allow_all_attributes,
        'ul': allow_all_attributes,
    }


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
                    delimiter = request.POST.get('delimiter', b',')
                    delimiter = str(delimiter)[0]
                    
                    try:
                        debug = csv_import_projects(csv_file, request=request, encoding=encoding, delimiter=delimiter, import_type=import_type)
                        messages.success(request, dotrans_('The CSV file was read successfully! You will be notified by email when it completes.'))
                        import_running = True
                    except (UnicodeDecodeError, UnicodeError):
                        messages.error(request, dotrans_('The CSV file you supplied is not formatted in the proper encoding (%s)!' % encoding))
                    except EmptyOrUnreadableCSVContent:
                        messages.error(request, dotrans_('The CSV file you supplied was empty or not formatted in the proper encoding (%(encoding)s) or with a wrong delimiter (%(delimiter)s)!' % {'encoding':encoding, 'delimiter':delimiter}))
                    except UnexpectedNumberOfColumns, e:
                        messages.error(request, dotrans_('One or more rows in the CSV file you supplied contained less columns than expected (%s)! Either the file was read in a wrong encoding, or the file was using a different format than the server expected.' % str(e)))
                    except ImportAlreadyRunning:
                        messages.error(request, dotrans_('Another import is currently running! Please wait till that one is finished.'))
                    except ImproperlyConfigured, e:
                        messages.error(request, dotrans_('A CSV configuration error occured, has the CSV format changed?. Message was: %s') % str(e))
                    except Exception, e:
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


# -*- coding: utf-8 -*-

from django.conf.urls import url
from django.core.urlresolvers import reverse
from django.utils.html import format_html

from wagtail.wagtailcore import hooks
from wagtail.wagtailcore.whitelist import attribute_rule
from django.conf import settings
from django.contrib.staticfiles.templatetags.staticfiles import static


from wagtail.wagtailadmin.menu import MenuItem

from django.utils.translation import ugettext_lazy as _
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
logger = logging.getLogger('cosinnus')


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
                messages.success(request, _('An import has just finished. Please click the "Start a new import" button to start a new one!'))
            else:
                csv_file = request.FILES.get('csv_upload', None)
                if not csv_file:
                    messages.error(request, _('You did not upload a CSV file or something went wrong during the upload!'))
                else:
                    encoding = request.POST.get('encoding', "utf-8")
                    delimiter = request.POST.get('delimiter', b',')
                    delimiter = str(delimiter)[0]
                    expected_columns = settings.COSINNUS_CSV_IMPORT_DEFAULT_EXPECTED_COLUMNS
                    
                    try:
                        debug = csv_import_projects(csv_file, request=request, encoding=encoding, delimiter=delimiter, expected_columns=expected_columns)
                        messages.success(request, _('The CSV file was read successfully! You will be notified by email when it completes.'))
                        import_running = True
                    except UnicodeDecodeError:
                        messages.error(request, _('The CSV file you supplied is not formatted in the proper encoding (%s)!' % encoding))
                    except EmptyOrUnreadableCSVContent:
                        messages.error(request, _('The CSV file you supplied was empty or not formatted in the proper encoding (%s) or with a wrong delimiter (%s)!' % (encoding, delimiter)))
                    except UnexpectedNumberOfColumns:
                        messages.error(request, _('The CSV file you supplied contained a different number columns than expected (%s)! Either the file was read in a wrong encoding, or the file was using a different format than the server expected.' % str(expected_columns)))
                    except ImportAlreadyRunning:
                        messages.error(request, _('Another import is currently running! Please wait till that one is finished.'))
                    except Exception, e:
                        messages.error(request, _('There was an unexpected error when reading the CSV file! Please make sure the file is properly formatted. If the problem persists, please contact an administrator!'))
                        logger.warn('A CSV file uploaded for import encountered an unexpected error! The exception was: "%s"' % str(e), extra={'encoding_used': encoding, 'delimiter_used': delimiter})
                        if getattr(settings, 'DEBUG_LOCAL', False):
                            raise
        
        context = {
            'site_name': settings.WAGTAIL_SITE_NAME,
            'panels': [],
            'user': request.user,
        }
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
        return ImportProjectsMenutItem(_('Import'), reverse('import-projects'), classnames='icon icon-plus', order=1005)


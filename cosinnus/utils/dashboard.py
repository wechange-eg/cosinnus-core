# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six


from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.decorators import classonlymethod
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.compat import atomic
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from django.contrib.auth import get_user_model
from cosinnus.forms.dashboard import InfoWidgetForm, DashboardWidgetForm,\
    EmptyWidgetForm
from cosinnus.models.tagged import AttachedObject, BaseTagObject
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.core.signals import group_object_ceated, userprofile_ceated
from django.dispatch.dispatcher import receiver
from cosinnus.core.registries.widgets import widget_registry
from cosinnus.models.profile import get_user_profile_model



class DashboardWidget(object):

    app_name = None
    widget_name = None
    form_class = DashboardWidgetForm
    # the template for the widget itself (header, buttons, etc)
    widget_template_name = 'cosinnus/widgets/base_widget.html'
    # the template for the rendereable content of the widget
    template_name = None
    group_model_attr = 'group'
    model = None
    user_model_attr = 'owner'
    allow_on_user = True
    allow_on_group = True

    def __init__(self, request, config_instance):
        self.request = request
        self.config = config_instance
        self.group = self.config.group

    @classonlymethod
    def create(cls, request, group=None, user=None, widget_type=WidgetConfig.TYPE_DASHBOARD):
        from cosinnus.models.widget import WidgetConfig
        config = WidgetConfig.objects.create(app_name=cls.get_app_name(),
            widget_name=cls.get_widget_name(), group=group, user=user, type=widget_type)
        return cls(request, config)

    @classmethod
    def get_app_name(cls):
        if not cls.app_name:
            raise ImproperlyConfigured('%s must defined an app_name' % cls.__name__)
        return cls.app_name

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        raise NotImplementedError("Subclasses need to implement this method.")

    def get_queryset(self, skipFilter=False):
        """ @param skipFilter: If true, the filtering for user will be skipped, so it can be done at a later (MRO) time. """
        if not self.model:
            raise ImproperlyConfigured('%s must define a model', self.__class__.__name__)
        qs = self.model._default_manager.filter(**self.get_queryset_filter())
        if not skipFilter:
            qs = filter_tagged_object_queryset_for_user(qs, self.request.user)
        return qs

    def get_queryset_filter(self, **kwargs):
        if self.config.group:
            return self.get_queryset_group_filter(**kwargs)
        else:
            return self.get_queryset_user_filter(**kwargs)

    def get_queryset_group_filter(self, **kwargs):
        """Defines filter arguments if the widget is used on a group dashboard"""
        if self.group_model_attr:
            kwargs.update({self.group_model_attr: self.config.group})
        return kwargs

    def get_queryset_user_filter(self, **kwargs):
        """Defines filter arguments if the widget is used on a user dashboard"""
        if self.user_model_attr:
            kwargs.update({self.user_model_attr: self.config.user})
        return kwargs

    @classmethod
    def get_setup_form_class(cls):
        return cls.form_class

    @classmethod
    def get_widget_name(cls):
        if not cls.widget_name:
            raise ImproperlyConfigured('%s must defined a widget_name' % cls.__name__)
        return cls.widget_name
    
    @classmethod
    def get_widget_title(cls):
        if not cls.title:
            raise ImproperlyConfigured('%s must defined a title' % cls.__name__)
        return cls.title
    
    @property
    def id(self):
        return self.config.pk

    def save_config(self, items):
        committed = True
        with atomic():
            self.config.items.all().delete()
            for k, v in six.iteritems(items):
                if hasattr(self.config, k):
                    setattr(self.config, k, v)
                    committed = False
                # config items are saved in the WidgetConfig.__setitem__() method!
                self.config[k] = v
            if not committed:    
                self.config.save()
    
    def render(self, **kwargs):
        context = dict(**kwargs)
        context.update({
            'widget_conf_id': self.id,
            'app_name': self.app_name,
            'widget_title': self.config.get('widget_title', None),
            'widget_icon': self.config.get('widget_icon', None),
            'link_label':self.config.get('link_label', None),
            'sort_field': self.config.sort_field,
        })
        return render_to_string(self.widget_template_name, context)
    
    @property
    def title(self):
        return ''

    @property
    def title_url(self):
        if self.config.type == WidgetConfig.TYPE_MICROSITE:
            return ''
        
        if self.config.group:
            return group_aware_reverse('cosinnus:%s:index' % self.app_name,
                           kwargs={'group': self.config.group})
        # return '#' as default url to prevent firefox dropping the <a> tag content
        return '#'
    
    def attached_objects_from_field(self, field):
        """ Resolves attached BaseTaggableObjects from a widget config field that contains
            ids of AttachableObject connector objects """
        if field:
            attached_ids = [int(val) for val in field.split(',')]
            return AttachedObject.objects.filter(id__in=attached_ids)
        return []

class GroupDescriptionForm(DashboardWidgetForm):
    """
    This is an incomplete start to making the group description editable in the
    widget itself.
    """

    # TODO: Continue working on this if the feature is needed.

    # description = forms.CharField(widget=TinyMCE(attrs={'cols': 8, 'rows': 10}), initial='//group.description//')
    # def clean(self):
    #     cleaned_data = super(GroupDescriptionForm, self).clean()
    #     # TODO: save group.description to CosinnusGroup here!
    #     return cleaned_data
    pass


class GroupDescriptionWidget(DashboardWidget):

    app_name = 'cosinnus'
    model = CosinnusGroup
    title = _('Team Description')
    user_model_attr = None
    widget_name = 'group_description'
    allow_on_user = False

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        group = self.config.group
        if group is None:
            return ''
        data = {
            'group': group,
        }
        return (render_to_string('cosinnus/widgets/group_description.html', data), 0, False)
    
    @property
    def title_url(self):
        return ''
    

class GroupMembersWidget(DashboardWidget):

    app_name = 'cosinnus'
    model = CosinnusGroup
    user_model_attr = None
    widget_name = 'group_members'
    allow_on_user = False
    widget_template_name = 'cosinnus/widgets/group_members_widget.html'
    # disabled so it doesn't show up in the widget chooser yet
    #template_name = 'cosinnus/widgets/group_members.html' 
    
    @property
    def title(self):
        member_count = getattr(self, 'member_count', None)
        if member_count is not None:
            return (_('Members') + ' (%d)' % self.member_count) 
        return _('Members')

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        group = self.config.group
        if group is None:
            return ''
        
        # how many members display. it's -1 because the last tile is always the "+72 members"
        count = getattr(settings, 'COSINNUS_GROUP_MEMBER_WIDGET_USER_COUNT', 15)
        
        admin_ids = CosinnusGroupMembership.objects.get_admins(group=group)
        member_ids = CosinnusGroupMembership.objects.get_members(group=group)
        all_ids = set(admin_ids + member_ids)
        
        userprofile_table = get_user_profile_model()._meta.db_table
        qs = get_user_model()._default_manager.filter(is_active=True) \
            .exclude(last_login__exact=None) \
            .filter(cosinnus_profile__settings__contains='tos_accepted') \
            .select_related('cosinnus_profile') \
            .extra(select={
                'has_avatar': 'LENGTH(%s.avatar) > 0' % userprofile_table
            }) \
            .order_by('-has_avatar', 'first_name', 'last_name') 
        qs = qs.filter(id__in=all_ids)
        
        self.member_count = qs.count()
        hidden_member_count = 0
        
        is_member_of_this_group = self.request.user.pk in all_ids
        if not self.request.user.is_authenticated():
            visibility_level = BaseTagObject.VISIBILITY_ALL
        elif not is_member_of_this_group:
            visibility_level = BaseTagObject.VISIBILITY_GROUP
        else:
            visibility_level = -1
        
        # show VISIBILITY_ALL users to anonymous users, VISIBILITY_GROUP to logged in users, 
        # and all members to group-members
        if visibility_level != -1:
            qs = qs.filter(cosinnus_profile__media_tag__visibility__gte=visibility_level)
            hidden_member_count = self.member_count - len(qs)
        
        has_more = len(qs) > offset+count or hidden_member_count > 0
        more_count = max(0, len(qs) - (offset+count)) + hidden_member_count
        
        if count != 0:
            qs = qs[offset:offset+count]      
        
        data = {
            'group': group,
            'members':qs,
            'has_more': has_more,
            'more_count': more_count,
        }
        return (render_to_string('cosinnus/widgets/group_members.html', data), len(qs), has_more)

    @property
    def title_url(self):
        if self.config.type == WidgetConfig.TYPE_MICROSITE:
            return '#'
        if self.config.group:
            return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.config.group})
        return '#'


class GroupProjectsWidget(DashboardWidget):

    app_name = 'cosinnus'
    model = CosinnusGroup
    title = _('Projects')
    user_model_attr = None
    widget_name = 'group_projects'
    allow_on_user = False
    widget_template_name = 'cosinnus/widgets/group_projects_widget.html'
    
    widget_content_template_name = 'cosinnus/widgets/group_projects.html'
    
    # disabled so it doesn't show up in the widget chooser yet
    #template_name = 'cosinnus/widgets/group_members.html' 
    
    def get_groups(self, group):
        """ Can be overridden to show specific groups in this widget """
        return group.get_children()
    
    def sanity_check(self, group):
        """ Check if this widget should exist. If not, deletes itself and returns False """
        if group.type != CosinnusGroup.TYPE_SOCIETY:
            # sanity check: after a group has been converted to a group, these widget configs still exist,
            # but are not valid anymore since we now have a project. therefore, delete it.
            self.config.delete()
            return False
        return True
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        group = self.config.group
        if group is None:
            return ('', 0, False)
        if not self.sanity_check(group):
            return ('', 0, False)
        
        #count = int(self.config.get('amount', 24))
        # FIXME: hardcoded widget item count for now
        count = 99
        groups = self.get_groups(group)
        
        has_more = len(groups) > offset+count
        more_count = max(0, len(groups) - (offset+count))
        
        if count != 0:
            groups = groups[offset:offset+count]      
        
        data = {
            'group': group,
            'groups': groups,
            'has_more': has_more,
            'more_count': more_count,
        }
        return (render_to_string(self.widget_content_template_name, data), len(groups), True) # more (create) button always shown

    @property
    def title_url(self):
        return '#'
    

class RelatedGroupsWidget(GroupProjectsWidget):
    
    model = CosinnusGroup
    title = _('Related Projects/Groups')
    widget_name = 'related_groups'
    widget_template_name = 'cosinnus/widgets/related_groups_widget.html'
    widget_content_template_name = 'cosinnus/widgets/related_groups.html'
    
    def get_groups(self, group):
        # overriding the base function
        return group.related_groups.all()
    
    def sanity_check(self, group):
        # overriding the base function
        return True
    

class InfoWidget(DashboardWidget):
    """ An extremeley simple info widget displaying text.
        The text is saved in the widget config
    """

    app_name = 'cosinnus'
    widget_template_name = 'cosinnus/widgets/info_widget.html'
    template_name = 'cosinnus/widgets/info_widget_content.html'
    model = None
    title = _('About Us')
    form_class = InfoWidgetForm
    user_model_attr = None
    widget_name = 'info_widget'
    allow_on_user = True
    
    @property
    def attached_images(self):
        images = []
        for att_obj in self.attached_objects_from_field(self.config['images']):
            if att_obj.model_name == "cosinnus_file.FileEntry" and att_obj.target_object.is_image:
                images.append(att_obj.target_object)
        return images
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
        """
        """
        group = self.config.group
        if group is None:
            return ''
        data = {
            'group': group,
        }
        """
        images = self.attached_images
        
        context = {
            'text': self.config['text'],
            'images': images,
        }
        
        return (render_to_string(self.template_name, context), 0, True)
    
    @property
    def title_url(self):
        return ''
    
    def get_queryset(self):
        return None
    
class MetaAttributeWidget(DashboardWidget):
    """ An extremeley simple info widget displaying text.
        The text is saved in the widget config
    """

    app_name = 'cosinnus'
    widget_template_name = 'cosinnus/widgets/meta_attribute_widget.html'
    template_name = ''
    model = None
    title = _('Informations')
    form_class = EmptyWidgetForm
    user_model_attr = None
    widget_name = 'meta_attr_widget'
    allow_on_user = False
    
    
    def get_data(self, offset=0):
        # return (no data, no rows, no More button)
        return ('', 0, False)
    
    @property
    def title_url(self):
        return ''
    
    def get_queryset(self):
        return None


def ensure_group_widget(group, app_name, widget_name, widget_type, options):
    """ Checks if a widget exists, and if not, creates it """
    widget_check = WidgetConfig.objects.filter(group_id=group.pk, app_name=app_name, widget_name__in=[widget_name, widget_name.replace('_', ' ')], type=widget_type)
    if widget_check.count() <= 0:
        widget_class = widget_registry.get(app_name, widget_name, None)
        if widget_class:
            widget = widget_class.create(None, group=group, user=None, widget_type=widget_type)
            widget.save_config(options)
    
@receiver(group_object_ceated)
def create_initial_group_widgets(sender, group, **kwargs):
    """ Function responsible for creating the initial widgets of CosinnusGroups
    (and subtypes) upon creation. Will create all group dashboard and microsite widgets 
    that are defined in:
        ``settings.COSINNUS_INITIAL_GROUP_WIDGETS`` and
        ``settings.COSINNUS_TYPE_DEPENDENT_GROUP_WIDGETS`` and
        ``settings.COSINNUS_INITIAL_GROUP_MICROSITE_WIDGETS``
    """
    # TODO: this should also delete all superfluous widgets for this group 
    # that exist, but are not listed in any of their settings
    
    for app_name, widget_name, options in settings.COSINNUS_INITIAL_GROUP_WIDGETS:
        ensure_group_widget(group, app_name, widget_name, WidgetConfig.TYPE_DASHBOARD, options)
    
    if group.type in settings.COSINNUS_TYPE_DEPENDENT_GROUP_WIDGETS:
        for app_name, widget_name, options in settings.COSINNUS_TYPE_DEPENDENT_GROUP_WIDGETS[group.type]:
            ensure_group_widget(group, app_name, widget_name, WidgetConfig.TYPE_DASHBOARD, options)
            
    for app_name, widget_name, options in settings.COSINNUS_INITIAL_GROUP_MICROSITE_WIDGETS:
        ensure_group_widget(group, app_name, widget_name, WidgetConfig.TYPE_MICROSITE, options)


@receiver(userprofile_ceated)
def create_initial_user_widgets(sender, profile, **kwargs):
    """ Function responsible for creating the initial widgets of the UserDashboard
    upon user creation. Will create widgets that are defined in:
        ``settings.COSINNUS_INITIAL_USER_WIDGETS``
    """
    for app_name, widget_name, options in settings.COSINNUS_INITIAL_USER_WIDGETS:
        widget_class = widget_registry.get(app_name, widget_name, None)
        if widget_class:
            widget = widget_class.create(None, group=None, user=profile.user)
            widget.save_config(options)
    
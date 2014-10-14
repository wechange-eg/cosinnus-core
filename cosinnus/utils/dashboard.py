# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six


from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.decorators import classonlymethod
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.compat import atomic
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from django.contrib.auth import get_user_model
from cosinnus.forms.dashboard import InfoWidgetForm, DashboardWidgetForm,\
    EmptyWidgetForm
from cosinnus.models.tagged import AttachedObject
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.urls import group_aware_reverse



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

    def get_queryset(self):
        if not self.model:
            raise ImproperlyConfigured('%s must define a model', self.__class__.__name__)
        qs = self.model._default_manager.filter(**self.get_queryset_filter())
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
                           kwargs={'group': self.config.group.slug})
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
    title = _('Group Description')
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
    title = _('Network')
    user_model_attr = None
    widget_name = 'group_members'
    allow_on_user = False
    widget_template_name = 'cosinnus/widgets/group_members_widget.html'
    # disabled so it doesn't show up in the widget chooser yet
    #template_name = 'cosinnus/widgets/group_members.html' 

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        group = self.config.group
        if group is None:
            return ''
        
        #count = int(self.config.get('amount', 24))
        # FIXME: hardcoded widget item count for now
        count = 23
        
        admin_ids = CosinnusGroupMembership.objects.get_admins(group=group)
        member_ids = CosinnusGroupMembership.objects.get_members(group=group)
        all_ids = set(admin_ids + member_ids)
        qs = get_user_model()._default_manager.order_by('first_name', 'last_name') \
                             .select_related('cosinnus_profile')
        qs = qs.filter(id__in=all_ids)
        
        has_more = len(qs) > offset+count
        more_count = max(0, len(qs) - (offset+count))
        
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
        return '#'
    
    
    

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
    
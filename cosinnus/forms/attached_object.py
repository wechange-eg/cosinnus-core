# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from builtins import object
from django.apps import apps

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django_select2 import (HeavyModelSelect2MultipleChoiceField)
from django.core.exceptions import ValidationError

from cosinnus.models.tagged import AttachedObject
from cosinnus.views.attached_object import AttachableObjectSelect2View,\
    build_attachment_field_result
from cosinnus.core.registries import attached_object_registry
from django.urls import reverse
from django_select2.util import JSFunction
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.conf import settings
from annoying.functions import get_object_or_None
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.models.group import CosinnusPortal

import logging
logger = logging.getLogger('cosinnus')

class FormAttachableMixin(object):
    """
    Used together with AttachableViewMixin.

    Extending this form will automatically add fields for all attachable
    cosinnus models (as configured in `settings.COSINNUS_ATTACHABLE_OBJECTS`)
    to a form. Even though there is a different field for each attachable
    model, this form handles saving all selected objects to the object's
    `attached_objects` M2M field.
    """
    def __init__(self, *args, **kwargs):
        super(FormAttachableMixin, self).__init__(*args, **kwargs)
        
        # retrieve the attached objects ids to select them in the update view
        preresults = []
        if self.instance and self.instance.pk:
            for attached in self.instance.attached_objects.all():
                if attached and attached.target_object:
                    obj = attached.target_object
                    text_only = (attached.model_name+":"+str(obj.id), "%s" % (obj.title),)
                    #text_only = (attached.model_name+":"+str(obj.id), "&lt;i&gt;%s&lt;/i&gt; %s" % (attached.model_name, obj.title),)  
                    # TODO: sascha: returning unescaped html here breaks the javascript of django-select2
                    html = build_attachment_field_result(attached.model_name, obj) 
                    preresults.append(text_only)
                    
        # add a field for each model type of attachable file provided by cosinnus apps
        # each field's name is something like 'attached:cosinnus_file.FileEntry'
        # and fill the field with all available objects for that type (this is passed from our view)
        source_model_id = self._meta.model._meta.app_label + '.' + self._meta.model._meta.object_name

        # get target groups to add newly attached files to        
        target_group = getattr(self, 'group', None)
        if not target_group:
            # if this form's model has no group, it may be a global object that can still have attachments,
            # so fall back to the forum group to add attached objects to. if this doesn't exist, attaching in not possible.
            forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
            if forum_slug:
                target_group = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current())
                    
        """ Add attachable objects field if this model is configured in settings.py to have objects that can be attached to it """
        if target_group and attached_object_registry.get_attachable_to(source_model_id):
            self.fields['attached_objects'] = AttachableObjectSelect2MultipleChoiceField(
                label=_("Attachments"), 
                help_text=_("Type the title and/or type of attachment"), 
                data_url=group_aware_reverse('cosinnus:attached_object_select2_view', kwargs={'group': target_group, 'model':source_model_id}),
                required=False
            )
            # we need to cheat our way around select2's annoying way of clearing initial data fields
            self.fields['attached_objects'].choices = preresults #((1, 'hi'),)
            self.fields['attached_objects'].initial = [key for key,val in preresults] #[1]
            setattr(self, 'target_group', target_group)

    def save_attachable(self):
        """ Called by `AttachableViewMixin.form_valid()`
            For some reason, this field is not being saved automatically,
            even though field and model field are named the same.
            We also run this on any instances in `self.extra_instances, because sometimes
            like in postman, forms save aways more than one instance.`
             """
        instances = [self.instance]
        if getattr(self, 'extra_instances', []):
            instances.extend(self.extra_instances)
        for instance in instances:
            instance.attached_objects.clear()
            for attached_obj in self.cleaned_data.get('attached_objects', []):
                instance.attached_objects.add(attached_obj)
                # set the visibility of the attached object to that of the parent object,
                # Note: this may make existing attached_objects public even though they were previously not!
                try:
                    if getattr(self.instance, 'media_tag', None) is not None:
                        target_object_mt = attached_obj.target_object.media_tag
                        target_object_mt.visibility = self.instance.media_tag.visibility
                        target_object_mt.save(update_fields=['visibility'])
                except Exception as e:
                    logger.warning('Could not set the visibility of an attached object to that of its parent!', extra={'exception': e})
                    if settings.DEBUG:
                        raise
                
            # safely invalidate the cached properties first
            try:
                del instance.attached_image
            except:
                pass
            try:
                del instance.attached_images
            except:
                pass
            # then update the instance's index after attaching objects
            if hasattr(instance, 'update_index'):
                instance.update_index()
                

class AttachableObjectSelect2MultipleChoiceField(HeavyModelSelect2MultipleChoiceField):
    queryset = AttachedObject
    data_view = AttachableObjectSelect2View
    
    def __init__(self, *args, **kwargs):
        """ Enable returning HTML formatted results in django-select2 return views!
            Note: You are responsible for cleaning the content, i.e. with  django.utils.html.escape()! """
        super(AttachableObjectSelect2MultipleChoiceField, self).__init__(*args, **kwargs)
        self.widget.options['escapeMarkup'] = JSFunction('function(m) { return m; }')
    
    def clean(self, value):
        """ We organize the ids gotten back from the recipient select2 field.
            This is a list of mixed ids which could either be groups or users.
            See cosinnus_messages.views.UserSelect2View for how these ids are built.
            
            Example for <value>: [u'cosinnus_event.Event:1', u'cosinnus_file.FileEntry:1'] 
        """
                
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        
        attached_objects = []   
        if value: 
            for attached_obj_str in value:
                if not attached_obj_str:
                    continue
                """ expand id and model type to real AO """
                obj_type, _, object_id = str(attached_obj_str).partition(':')
                app_label, _, model = obj_type.rpartition('.')
                content_type = ContentType.objects.get_for_model(apps.get_model(app_label, model))
                (ao, _) = AttachedObject.objects.get_or_create(content_type=content_type, object_id=object_id)
                attached_objects.append(ao)
        
        return attached_objects


class AttachableWidgetSelect2Field(AttachableObjectSelect2MultipleChoiceField):
    
    def __init__(self, *args, **kwargs):
        """ Enable returning HTML formatted results in django-select2 return views!
            Note: You are responsible for cleaning the content, i.e. with  django.utils.html.escape()! """
        super(AttachableWidgetSelect2Field, self).__init__(*args, **kwargs)
        
        # retrieve the attached objects ids to select them in the update view
        preresults = []
        
        if self.initial:
            attached_ids = [int(val) for val in self.initial.split(',')]
            for attached in AttachedObject.objects.filter(id__in=attached_ids):
                if attached and attached.target_object:
                    obj = attached.target_object
                    text_only = (attached.model_name+":"+str(obj.id), "%s" % (obj.title),)
                    #text_only = (attached.model_name+":"+str(obj.id), "&lt;i&gt;%s&lt;/i&gt; %s" % (attached.model_name, obj.title),)  
                    # TODO: sascha: returning unescaped html here breaks the javascript of django-select2
                    #html = build_attachment_field_result(attached.model_name, obj) 
                    preresults.append(text_only)
                    
        # we need to cheat our way around select2's annoying way of clearing initial data fields
        self.choices = preresults #((1, 'hi'),)
        self.initial = [key for key,val in preresults] #[1]
    
    
    
    def clean(self, value):
        cleaned_objects = super(AttachableWidgetSelect2Field, self).clean(value)
        obj_string = ",".join(["%d" % (att_obj.id) for att_obj in cleaned_objects])
        return obj_string

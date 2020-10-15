from django_select2 import (HeavyModelSelect2MultipleChoiceField)
from django.core.exceptions import ValidationError
from cosinnus.conf import settings
from django.http.response import Http404
from cosinnus.models.group import CosinnusGroup
from django_select2.util import JSFunction
from django.contrib.auth import get_user_model
from cosinnus.utils.user import filter_active_users

User = get_user_model()

class UserSelect2MultipleChoiceField(HeavyModelSelect2MultipleChoiceField):
    
    queryset = User.objects
    search_fields = ['username__icontains', ]
    data_view = None # set at init time
    
    def __init__(self, *args, **kwargs):
        """ Enable returning HTML formatted results in django-select2 return views!
            Note: You are responsible for cleaning the content, i.e. with  django.utils.html.escape()! """
        from cosinnus.views.user import UserSelect2View
        self.data_view = UserSelect2View
        super(UserSelect2MultipleChoiceField, self).__init__(*args, **kwargs)
        self.widget.options['escapeMarkup'] = JSFunction('function(m) { return m; }')
        # this doesn't seem to help in removing the <div> tags
        #self.widget.options['formatResult'] = JSFunction('function(data) { return data.text; }')
        #self.widget.options['formatSelection'] = JSFunction('function(data) { return data.text; }')
    
    def get_user_and_group_ids_for_value(self, value, intify=True):
        user_ids = []
        group_ids = []
        for val in value:
            if not val:
                continue
            value_type, value_id = val.split(':')
            if value_type == 'user':
                if intify:
                    value_id = int(value_id)
                user_ids.append(value_id)
            elif value_type == 'group':
                if intify:
                    value_id = int(value_id)
                group_ids.append(value_id)
            else:
                if settings.DEBUG:
                    raise Http404("Programming error: message recipient field contained unrecognised id '%s'" % val)
        return user_ids, group_ids
    
    def clean(self, value):
        """ We organize the ids gotten back from the recipient select2 field.
            This is a list of mixed ids which could either be groups or users.
            See cosinnus.views.user.UserSelect2View for how these ids are built.
            
            Example for <value>: [u'user:1', u'group:4'] 
        """
                
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])
        
        user_ids, group_ids = self.get_user_and_group_ids_for_value(value)
        
        # add group members to the list
        groups = CosinnusGroup.objects.get_cached(pks=group_ids)
        recipients = set()
        for group in groups:
            group_members = get_user_model().objects.filter(id__in=group.members)
            recipients.update(filter_active_users(group_members))
            
        # combine the groups users with the directly selected users
        recipients.update(filter_active_users(User.objects.filter(id__in=user_ids)))

        return list(recipients)
    
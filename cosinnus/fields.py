from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django_select2.fields import HeavySelect2MultipleChoiceField
from django_select2.util import JSFunction

from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.user import filter_active_users

User = get_user_model()


class Select2MultipleChoiceField(HeavySelect2MultipleChoiceField):
    select_type = 'user'
    model = None

    def __init__(self, *args, **kwargs):
        """Enable returning HTML formatted results in django-select2 return views!
        Note: You are responsible for cleaning the content, i.e. with  django.utils.html.escape()!"""
        super(Select2MultipleChoiceField, self).__init__(*args, **kwargs)
        self.widget.options['escapeMarkup'] = JSFunction('function(m) { return m; }')
        # this doesn't seem to help in removing the <div> tags
        # self.widget.options['formatResult'] = JSFunction('function(data) { return data.text; }')
        # self.widget.options['formatSelection'] = JSFunction('function(data) { return data.text; }')

    def get_ids_for_value(self, value, intify=True):
        ids = {}
        for val in value:
            if not val:
                continue
            value_type, value_id = val.split(':')
            if intify:
                value_id = int(value_id)
            if value_type not in ids:
                ids[value_type] = []
            ids[value_type].append(value_id)
        return ids

    def clean(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])

        ids = self.get_ids_for_value(value)
        return self.model.objects.filter(id__in=ids[self.select_type])


class UserSelect2MultipleChoiceField(Select2MultipleChoiceField):
    model = get_user_model()
    search_fields = [
        'username__icontains',
    ]
    data_view = ''

    def clean(self, value):
        """We organize the ids gotten back from the recipient select2 field.
        This is a list of mixed ids which could either be groups or users.
        See cosinnus.views.user.UserSelect2View for how these ids are built.

        Example for <value>: [u'user:1', u'group:4']
        """

        if self.required and not value:
            raise ValidationError(self.error_messages['required'])

        ids = self.get_ids_for_value(value)

        # Add group members to the list
        recipients = set()
        if 'group' in ids:
            groups = CosinnusGroup.objects.get_cached(pks=ids['group'])
            for group in groups:
                group_members = get_user_model().objects.filter(id__in=group.members)
                recipients.update(filter_active_users(group_members))

        # combine the groups users with the directly selected users
        if 'user' in ids:
            recipients.update(filter_active_users(User.objects.filter(id__in=ids['user'])))

        return list(recipients)


class UserIDSelect2MultipleChoiceField(UserSelect2MultipleChoiceField):
    """Like UserSelect2MultipleChoiceField, but persists values as list of int ids instead of
    list of users"""

    def clean(self, *args, **kwargs):
        user_list = super(UserIDSelect2MultipleChoiceField, self).clean(*args, **kwargs)
        return [user.id for user in user_list]


class GroupSelect2MultipleChoiceField(Select2MultipleChoiceField):
    model = get_cosinnus_group_model()
    search_fields = [
        'name__icontains',
    ]
    data_view = ''
    select_type = 'group'

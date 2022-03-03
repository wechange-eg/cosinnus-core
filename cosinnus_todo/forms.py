# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form, BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.widgets import DateTimeL10nPicker

from cosinnus_todo.models import TodoEntry, TodoList, Comment
from cosinnus.forms.attached_object import FormAttachableMixin


class TodoEntryForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                    FormAttachableMixin, BaseTaggableObjectForm):

    class Meta(object):
        model = TodoEntry
        fields = ('title', 'due_date', 'assigned_to', 'completed_by',
                  'completed_date', 'priority', 'note')
        widgets = {
            'due_date': DateTimeL10nPicker(),
            'completed_date': DateTimeL10nPicker(),
        }

    def __init__(self, *args, **kwargs):
        super(TodoEntryForm, self).__init__(*args, **kwargs)

        field = self.fields.get('todolist', None)
        if field:
            field.queryset = TodoList.objects.filter(group_id=self.group.id).all()
            
        field = self.fields.get('assigned_to', None)
        if field:
            field.queryset = self.group.actual_members
            field.required = False
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                can_assign = instance.can_user_assign(self.user)
                if not can_assign:
                    field.widget.attrs['disabled'] = 'disabled'

        field = self.fields.get('completed_by', None)
        if field:
            field.queryset = self.group.actual_members

    def clean_assigned_to(self):
        assigned_to = self.cleaned_data['assigned_to']
        instance = getattr(self, 'instance', None)
        if not instance or not instance.pk:
            return assigned_to

        if instance.can_user_assign(self.user):
            return assigned_to

        if assigned_to != instance.assigned_to:  # trying to cheat!
            raise ValidationError(
                _('You are not allowed to assign this Todo entry.'),
                code='can_not_assign'
            )
        return assigned_to

    def clean(self):
        new_list = self.cleaned_data.get('new_list', None)
        todolist = self.cleaned_data.get('todolist', None)
        if new_list and todolist:
            del self.cleaned_data['todolist']  # A new list name has been defined
        
        return self.cleaned_data


class _TodoEntryAddForm(TodoEntryForm):

    new_list = forms.CharField(label='New list name', required=False)
    due_date = forms.DateField(required=False)

    class Meta(object):
        model = TodoEntry
        fields = ('title', 'note', 'due_date', 'new_list', 'todolist', 'assigned_to', 'priority')
        widgets = {
            'due_date': DateTimeL10nPicker(),
            'completed_date': DateTimeL10nPicker(),
        }
        
    def clean(self):
        super(_TodoEntryAddForm, self).clean()
        # hack to circumvent django still throwing validation errors in my face on a blank select
        # even though the field is required=False
        if self.cleaned_data.get('assigned_to', None) is None:
            self.instance.assigned_to = None
            del self._errors['assigned_to']
        return self.cleaned_data


TodoEntryAddForm = get_form(_TodoEntryAddForm)


class _TodoEntryUpdateForm(_TodoEntryAddForm):
    
    class Meta(_TodoEntryAddForm.Meta):
        fields = ('title', 'note', 'due_date', 'new_list', 'todolist', 'assigned_to',
                  'completed_by', 'completed_date', 'priority')
        widgets = {
            'due_date': DateTimeL10nPicker(),
            'completed_date': DateTimeL10nPicker(),
        }

TodoEntryUpdateForm = get_form(_TodoEntryUpdateForm)


class TodoEntryAssignForm(TodoEntryForm):

    class Meta(object):
        model = TodoEntry
        fields = ('assigned_to',)


class TodoEntryCompleteForm(TodoEntryForm):

    class Meta(object):
        model = TodoEntry
        fields = ('completed_by', 'completed_date',)
        widgets = {
            'completed_date': DateTimeL10nPicker(),
        }


class TodoEntryNoFieldForm(TodoEntryForm):

    class Meta(object):
        model = TodoEntry
        fields = ()


class TodoListForm(GroupKwargModelFormMixin, forms.ModelForm):

    class Meta(object):
        model = TodoList
        fields = ('title', 'slug', )
        

class CommentForm(forms.ModelForm):

    class Meta(object):
        model = Comment
        fields = ('text',)

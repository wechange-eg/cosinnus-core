# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random

from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import MaxLengthValidator
from django.forms.models import ModelMultipleChoiceField
from django.utils.translation import gettext_lazy as _
from django_select2.widgets import Select2MultipleWidget

from cosinnus.forms.translations import TranslatedFieldsFormMixin
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.managed_tags import CosinnusManagedTag
from cosinnus.models.newsletter import GroupsNewsletter, Newsletter
from cosinnus.utils.group import get_cosinnus_group_model


class UserWelcomeEmailForm(TranslatedFieldsFormMixin, forms.ModelForm):
    class Meta:
        model = CosinnusPortal
        fields = ['welcome_email_active', 'welcome_email_text']


class CustomSelectMultiple(ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class NewsletterForManagedTagsForm(forms.ModelForm):
    managed_tags = CustomSelectMultiple(queryset=CosinnusManagedTag.objects.all(), widget=forms.CheckboxSelectMultiple)

    class Meta(object):
        model = Newsletter
        fields = ['subject', 'body', 'managed_tags']


class NewsletterForGroupsForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=get_cosinnus_group_model().objects.none(), widget=Select2MultipleWidget
    )

    class Meta(object):
        model = GroupsNewsletter
        fields = ['subject', 'body', 'groups']

    def __init__(self, instance, *args, **kwargs):
        super().__init__(instance=instance, *args, **kwargs)

        if 'groups' in self.fields:
            self.fields['groups'] = ModelMultipleChoiceField(
                queryset=get_cosinnus_group_model().objects.all_in_portal(),
                widget=Select2MultipleWidget,
                initial=[] if not instance else [rel_group.pk for rel_group in instance.groups.all()],
            )


class UserAdminForm(forms.ModelForm):
    email = forms.EmailField(label=_('email address'), required=True, validators=[MaxLengthValidator(220)])
    first_name = forms.CharField(label=_('first name'), required=True)

    class Meta(object):
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not self.instance.pk:
            email_exists = get_user_model().objects.filter(email__iexact=email).exists()
        else:
            email_exists = get_user_model().objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists()
        if email_exists:
            raise forms.ValidationError(_('This email address already has a registered user!'))
        else:
            return email.lower()

    def save(self, commit=True):
        if not self.instance.pk:
            self.instance.username = str(random.randint(100000000000, 999999999999))
            user = super().save()
            user.username = str(user.id)
            user.is_active = True
            user.save()
        else:
            user = super().save()
        return user

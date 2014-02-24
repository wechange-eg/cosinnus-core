# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.views.generic import CreateView
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.hierarchy import AddFolderForm
from cosinnus.views.mixins.group import (RequireWriteMixin, FilterGroupMixin)
from cosinnus.views.mixins.tagged import HierarchyPathMixin


class AddFolderView(RequireWriteMixin, FilterGroupMixin,
        HierarchyPathMixin, CreateView):
    """
    View to add folders in the hierarchy

    Child classes are required to define attributes 'model' and 'appname'
    """
    template_name = 'cosinnus/hierarchy/add_folder.html'

    def __init__(self, *args, **kwargs):
        if not self.appname:
            raise ImproperlyConfigured(_('No appname given for adding folders.'))
        super(AddFolderView, self).__init__(*args, **kwargs)

    def get_success_url(self):
        return reverse('cosinnus:%s:list' % self.appname,
                       kwargs={'group': self.group.slug})

    def get_form(self, form_class):
        """Override get_form to use model-specific form"""
        class ModelAddFolderForm(AddFolderForm):
            class Meta(AddFolderForm.Meta):
                model = self.model
        form_class = ModelAddFolderForm
        return super(AddFolderView, self).get_form(form_class)

    def form_valid(self, form):
        """
        If the form is valid, we need to do the following:
        - Set instance's isfolder to True
        - Set the instance's group
        - Set the path again once the slug has been established
        """
        form.instance.isfolder = True
        form.instance.group = self.group
        ret = super(AddFolderView, self).form_valid(form)

        # only after this save do we know the final slug
        # we still must add it to the end of our path if we're saving a folder
        self.object.path += self.object.slug + '/'
        self.object.save()

        return ret

    def get_context_data(self, *args, **kwargs):
        context = super(AddFolderView, self).get_context_data(*args, **kwargs)
        context['cancel_url'] = reverse('cosinnus:%s:list' % self.appname,
            kwargs={'group': self.group.slug})
        return context

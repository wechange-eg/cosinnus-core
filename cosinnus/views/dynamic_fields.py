from django.views.generic.base import TemplateView
from django.shortcuts import redirect, render
from django.utils.translation import ugettext as _

from cosinnus.forms.dynamic_fields import *
from cosinnus.models import CosinnusPortal


class DynamicFieldFormView(TemplateView):
    template_name = 'cosinnus/dynamic_fields/dynamic_field_form.html'
    form_class = DynamicFieldForm

    # TODO change method to get the default portal
    default_portal = CosinnusPortal.objects.first()

    def get(self, request, *args, **kwargs):
        form = self.form_class(cosinnus_portal=self.default_portal, dynamic_field_name='faechergruppe')
        return render(request, template_name=self.template_name, context={'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(cosinnus_portal=self.default_portal, dynamic_field_name='faechergruppe', data=request.POST)

        if form.is_valid():
            form.save()

        return render(request, template_name=self.template_name, context={'form': form})

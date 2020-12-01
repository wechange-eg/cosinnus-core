from django.views.generic.base import TemplateView
from django.shortcuts import redirect, render
from django.utils.translation import ugettext as _
from django.contrib import messages

from cosinnus.forms.dynamic_fields import *
from cosinnus.models import CosinnusPortal


class DynamicFieldFormView(TemplateView):
    template_name = 'cosinnus/dynamic_fields/dynamic_field_form.html'
    form_generator_class = DynamicFieldFormGenerator

    # TODO change method to get the default portal
    default_portal = CosinnusPortal.objects.first()

    def get(self, request, *args, **kwargs):
        generator = self.form_generator_class(cosinnus_portal=self.default_portal)
        forms = generator.get_forms()

        return render(request, template_name=self.template_name, context={'forms': forms})

    def post(self, request, *args, **kwargs):
        generator = self.form_generator_class(cosinnus_portal=self.default_portal, data=request.POST)
        forms = generator.get_forms()

        generator.try_save()
        if generator.saved:
            messages.success(self.request, _("Your data was set successfully!"))

        return render(request, template_name=self.template_name, context={'forms': forms})

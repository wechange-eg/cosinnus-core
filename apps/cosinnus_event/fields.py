from django.db import models
from django.core import validators
from django.forms.fields import URLField as FormURLField


class RTMPURLFormField(FormURLField):
    """ A form URLField with a validator that also supports `rtmp` as scheme. """
    default_validators = [validators.URLValidator(schemes=['rtmp', 'http', 'https'])]


class RTMPURLField(models.URLField):  
    """ A URLField with a validator that also supports `rtmp` as scheme. """
    '''URL field that accepts URLs that start with ssh:// only.'''  
    default_validators = [validators.URLValidator(schemes=['rtmp', 'http', 'https'])]  

    def formfield(self, **kwargs):
        return super(RTMPURLField, self).formfield(**{
            'form_class': RTMPURLFormField,
        })
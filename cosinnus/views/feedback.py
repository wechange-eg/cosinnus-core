# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http.response import HttpResponseNotAllowed, HttpResponseForbidden
from cosinnus.utils.http import JSONResponse
from django.views.decorators.csrf import csrf_protect
from cosinnus.models.feedback import CosinnusReportedObject
from django.contrib.contenttypes.models import ContentType
from django.db.models import get_model

@csrf_protect
def report_object(request):
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated():
        return HttpResponseForbidden('Not authenticated.')
    
    cls = request.POST.get('cls', None)  # expects 'cosinnus_note.Note'
    obj_id = request.POST.get('id', None)
    text = request.POST.get('text', None)
    
    if not cls and obj_id and text:
        raise ValueError('Incomplete data submitted.')
    
    app_label, model = cls.split('.')
    
    content_type = ContentType.objects.get_for_model(get_model(app_label, model))
    reported_obj = CosinnusReportedObject.objects.create(content_type=content_type, object_id=obj_id, text=text, creator=request.user)
    
    # TODO: notification to portal admins
    
    """
    data = {
        'status': 'error',
    }
    """
    
    data = {
        'status': 'success',
    }
    return JSONResponse(data, safe=False)
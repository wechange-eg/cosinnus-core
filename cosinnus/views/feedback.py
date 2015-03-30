# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http.response import HttpResponseNotAllowed
from cosinnus.utils.http import JSONResponse
from django.views.decorators.csrf import csrf_protect


@csrf_protect
def report_object(request):
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    cls = request.POST.get('cls', None)
    obj_id = request.POST.get('id', None)
    text = request.POST.get('text', None)
    
    if not cls and obj_id and text:
        raise ValueError('Incomplete data submitted.')
    
    print ">>> got", cls, obj_id, text
    
    data = {
        'status': 'error',
    }
    data = {
        'status': 'success',
    }
    
    return JSONResponse(data, safe=False)
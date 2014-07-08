# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.views.mixins.tagged import HierarchyTreeMixin
from django.shortcuts import get_object_or_404
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from django.http.response import Http404

class HierarchicalListCreateViewMixin(HierarchyTreeMixin):
    """ Hybrid view for hierarchic items.
        If allow_deep_hierarchy==True: Allows creation of folders inside other folders,
        else only allows creating them on the root level.
     """
    allow_deep_hierarchy = True
    
    def get_context_data(self, *args, **kwargs):
        # on form invalids, we need to retrieve the objects
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
            
        context = super(HierarchicalListCreateViewMixin, self).get_context_data(**kwargs)
        path = None
        slug = self.kwargs.pop('slug', None)
        if slug:
            try:
                path = self.object_list.get(slug=slug).path
            except self.model.DoesNotExist:
                raise Http404()
        root = path or '/'
        # assemble container and current hierarchy objects.
        # recursive must be =True, or we don't know how the size of a folder
        root_folder_node = self.get_tree(self.object_list, '/', include_containers=True, include_leaves=True, recursive=True)
        """ traverse tree and find the folder node which points to the given root """
        current_folder_node = root_folder_node
        for subfolder_name in root.split('/')[1:-1]:
            for find_folder in current_folder_node['containers']:
                if find_folder['path'].split('/')[-2] == subfolder_name:
                    current_folder_node = find_folder
        
        # we always show the folders from root if we only have 1 hierarchy level
        if self.allow_deep_hierarchy:
            folders = current_folder_node['containers']
        else:
            folders = root_folder_node['containers']
            
        objects = current_folder_node['objects']
        current_folder = current_folder_node['container_object']
        if current_folder is None:
            # insert logic for "this folder doesn't exist" here
            pass
        
        context.update({
            'current_folder': current_folder, 
            'object_list': objects, 
            'objects': objects, 
            'folders': folders,
            'is_deep_hierarchy': self.allow_deep_hierarchy,
        })
        return context
    


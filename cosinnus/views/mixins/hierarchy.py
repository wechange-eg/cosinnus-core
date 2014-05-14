# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.views.mixins.tagged import HierarchyTreeMixin, TaggedListMixin

class HierarchicalListCreateViewMixin(TaggedListMixin, HierarchyTreeMixin):
    
    def get_context_data(self, *args, **kwargs):
        # on form invalids, we need to retrieve the objects
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
            
        context = super(HierarchicalListCreateViewMixin, self).get_context_data(**kwargs)
        
        path = self.kwargs.pop('slug', None)
        root = '/' + path + '/' if path else '/'
        # assemble container and current hierarchy objects.
        # recursive must be =True, or we don't know how the size of a folder
        current_folder_node = self.get_tree(self.object_list, root, include_containers=True, include_leaves=True, recursive=True)
        root_folder_node = self.get_tree(self.object_list, '/', include_containers=True, include_leaves=True, recursive=True)
        
        # we always show the folders from root, as we only have 1 hierarchy level
        folders = root_folder_node['containers']
        objects = current_folder_node['objects']
        current_folder = current_folder_node['container_object']
        if current_folder is None:
            # insert logic for "this folder doesn't exist" here
            pass
        
        context.update({'current_folder':current_folder, 'object_list': objects, 'objects':objects, 'folders':folders})
        return context
    


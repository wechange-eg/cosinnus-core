# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.http.response import Http404
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from cosinnus.views.mixins.tagged import HierarchyTreeMixin
from django.utils.encoding import force_text
from cosinnus.models.group import CosinnusGroup

# this reads the environment and inits the right locale
import locale
try:
    locale.setlocale(locale.LC_ALL, ("de_DE", "utf8"))
except:
    locale.setlocale(locale.LC_ALL, "")


class HierarchicalListCreateViewMixin(HierarchyTreeMixin):
    """ Hybrid view for hierarchic items.
        If allow_deep_hierarchy==True: Allows creation of folders inside other folders,
        else only allows creating them on the root level.
     """
    allow_deep_hierarchy = True
    # if False, we will manually sort the list if no ordering param is present
    strict_default_sort = False
    
    def get_context_data(self, *args, **kwargs):
        # on form invalids, we need to retrieve the objects
        self.queryset = getattr(self, 'queryset', None) or self.get_queryset()
            
        context = super(HierarchicalListCreateViewMixin, self).get_context_data(**kwargs)
        path = None
        slug = self.kwargs.pop('slug', None)
        if slug:
            try:
                path = self.queryset.get(slug=slug).path
            except self.model.DoesNotExist:
                raise Http404()
        root = path or '/'
        
        # convert qs to list
        sorted_object_list = list(self.queryset)
        # sort case insensitive by title, ignoring umlauts unless we already have a filter in place
        if not self.request.GET.get('o', '') and not self.strict_default_sort:
            sorted_object_list.sort(cmp=locale.strcoll, key=lambda x: x.title)
        
        # assemble container and current hierarchy objects.
        # recursive must be =True, or we don't know how the size of a folder
        root_folder_node = self.get_tree(sorted_object_list, '/', include_containers=True, include_leaves=True, recursive=True)
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
        
        # sort folders alphabetically
        folders.sort(cmp=locale.strcoll, key=lambda container: (container['container_object'].title))
        # and then sort folders so that special folders are always on top
        folders.sort(cmp=locale.strcoll, key=lambda container: (container['container_object'].special_type or 'zzzzz'))
        
        objects = current_folder_node['objects']
        current_folder = current_folder_node['container_object']
        
        group = getattr(self, 'group', None)
        if not group and sorted_object_list:
            group = getattr(sorted_object_list[0], 'group', None)
        if not group and 'group__slug' in kwargs:
            # this is a bit dodgy, but sometimes we get passed the group__slug kwarg when 
            # abusing this mixin from a cosinnus app's Renderer directly (that's also when self.group is None)
            try:
                group = CosinnusGroup.objects.get_cached(slugs=kwargs.get('group__slug'))
            except CosinnusGroup.DoesNotExist:
                pass
        
        # we can only collect folder information for the whole group if we know which one it is
        if group:
            if current_folder is None:
                # sanity check: there might be no current folder because no root folder has been created
                # make sure to create one (backwards compatibility, should never happen on newer cosinnus systems)
                obj, created = self.model.objects.get_or_create(group=group, slug='_root_', title='_root_', path='/', is_container=True)
                current_folder = obj
            
            """ Collect a JSON list of all folders for this group
                Format: [{ "id" : "slug1", "parent" : "#", "text" : "Simple root node" }, 
                        { "id" : "slug2", "parent" : "slug1", "text" : "Child 1" },] """
                        
            # TODO: this needs optimization (caching, or fold the DB call into the main folder-get call)
            all_folders = self.model.objects.filter(group=group, is_container=True)
            folders_only = self.get_tree(all_folders, '/', include_containers=True, include_leaves=False, recursive=True)
            all_folder_json = []
            if folders_only and folders_only.get('container_object', None):
                def collect_folders(from_folder, folder_id='#'):
                    cur_id = from_folder['container_object'].slug
                    if from_folder['container_object'].is_container and from_folder['container_object'].path == '/':
                        folder_title = force_text(_('Root Folder'))
                    else:
                        folder_title = escape(from_folder['container_object'].title or force_text(_('<Root folder>')))
                        if from_folder['container_object'].special_type:
                            folder_title = force_text(pgettext_lazy('special_folder_type', folder_title))
                    all_folder_json.append( {'id': cur_id, 'parent': folder_id, 'a_attr': {'target_folder':from_folder['container_object'].id}, 'text': folder_title} )
                    for lower_folder in from_folder['containers']:
                        collect_folders(lower_folder, cur_id)
                collect_folders(folders_only)
        
        context.update({
            'current_folder': current_folder, 
            'object_list': objects, 
            'objects': objects, 
            'folders': folders,
            'is_deep_hierarchy': self.allow_deep_hierarchy,
            'all_folder_json': mark_safe(json.dumps(all_folder_json)),
        })
        return context
    


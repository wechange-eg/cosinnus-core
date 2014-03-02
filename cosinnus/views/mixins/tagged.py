# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict
from os.path import basename, dirname

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404

from taggit.models import Tag, TaggedItem


class TaggedListMixin(object):

    def dispatch(self, request, *args, **kwargs):
        tag_slug = kwargs.get('tag', None)
        if tag_slug:
            self.tag = get_object_or_404(Tag, slug=tag_slug)
        else:
            self.tag = None
        return super(TaggedListMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TaggedListMixin, self).get_context_data(**kwargs)
        ct = ContentType.objects.get_for_model(self.model)
        tag_ids = TaggedItem.objects.filter(content_type=ct,
                                            object_id__in=self.object_list) \
                                    .select_related('tag') \
                                    .values_list('tag_id', flat=True)
        context.update({
            'tag': self.tag,
            'tags': Tag.objects.filter(pk__in=tag_ids).order_by('name').all(),
        })
        return context

    def get_queryset(self):
        qs = super(TaggedListMixin, self).get_queryset() \
                                         .prefetch_related('tags')
        if self.tag:
            qs = qs.filter(tags=self.tag)
        return qs


class HierarchyTreeMixin(object):
    """
    This mixin can be used in apps' list views to generate a tree-like object
    structure. It implements just one method get_tree which can be called with
    a list of objects as argument to be displayed as a tree.
    """

    def get_tree(self, object_list):
        """
        Create a node/children tree structure containing app objects. We
        assume that ALL (!) pathnames end with a '/'. A container has a
        pathname of ``/path/to/container/containername/`` the last path part is
        the container itself!
        """
        # saves all container paths that have been created
        container_dict = {}

        def get_or_create_container(path, container_object, special_name=None):
            if path in container_dict.keys():
                container_entry = container_dict[path]
                # attach the container's object if we were passed one
                if container_object is not None:
                    container_entry['container_object'] = container_object
                return container_entry
            name = special_name if special_name else basename(path[:-1])
            new_container = defaultdict(dict, (
                ('objects', []),
                ('containers', []),
                ('name', name),
                ('path', path),
                ('container_object', container_object),))
            container_dict[path] = new_container
            if path != '/':
                attach_to_parent_container(new_container)
            return new_container

        def attach_to_parent_container(container):
            parent_path = dirname(container['path'][:-1])
            if parent_path[-1] != '/':
                parent_path += '/'
            if parent_path not in container_dict.keys():
                parent_container = get_or_create_container(parent_path, None)
            else:
                parent_container = container_dict[parent_path]
            parent_container['containers'].append(container)

        root = get_or_create_container('/', None)
        for obj in object_list:
            if obj.is_container:
                get_or_create_container(obj.path, obj)
            else:
                filescontainer = get_or_create_container(obj.path, None)
                filescontainer['objects'].append(obj)

        return root


class HierarchyPathMixin(object):
    """
    This mixin can be used in add/edit views. It sets up the path of the
    hierarchy for an object in forms.
    """

    def get_initial(self):
        """
        Supports calling /add under other objects,
        which creates a new object under the given object/container's path
        """
        initial = super(HierarchyPathMixin, self).get_initial()

        # if a slug is given in the URL, we check if its a container, and if so,
        # let the user create an object under that path
        # if it is an object, we let the user create a new object on the same level
        if 'slug' in self.kwargs.keys():
            container = get_object_or_404(self.model, slug=self.kwargs.get('slug'))
            initial.update({'path': container.path})
        return initial

    def form_valid(self, form):
        """
        If the form is valid, we need to do pass the path retrieved from the
        slug over to the non-editable field
        """
        path = form.initial.get('path', None)
        if path:
            form.instance.path = path
        return super(HierarchyPathMixin, self).form_valid(form)

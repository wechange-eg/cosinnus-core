# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from collections import defaultdict
from itertools import chain
from os.path import basename, dirname
import urllib.request, urllib.parse, urllib.error

from django.apps import apps
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic.list import MultipleObjectMixin

from cosinnus.core.registries import attached_object_registry as aor
from cosinnus.forms.hierarchy import AddContainerForm
from taggit.models import Tag, TaggedItem

from cosinnus.utils.permissions import check_object_write_access, filter_tagged_object_queryset_for_user
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from django.contrib.auth.models import AnonymousUser
from cosinnus.utils.functions import resolve_attributes
from cosinnus.conf import settings

import logging
logger = logging.getLogger('cosinnus')


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


class BaseListMixin(MultipleObjectMixin):
    """
    A base view for displaying a list of objects.
    """
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        return super(BaseListMixin, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super(BaseListMixin, self).get_context_data(
            object_list=self.object_list, **kwargs)


class HierarchyTreeMixin(object):
    """
    This mixin can be used in apps' list views to generate a tree-like object
    structure. It implements just one method get_tree which can be called with
    a list of objects as argument to be displayed as a tree.
    """

    def get_tree(self, object_list, root='/', include_containers=True,
                 include_leaves=True, recursive=True):
        """
        Create a node/children tree structure containing app objects. We
        assume that ALL (!) pathnames end with a '/'. A container has a
        pathname of ``/path/to/container/containername/`` the last path part is
        the container itself!
        @param object_list: All model objects that should be included in the tree
        @param root: The root path from which the tree should start out
        @param include_containers: should the tree contain folders?
        @param include_leaves: should the tree contain the model objects?
        @param recursive: Should folder levels below the given root path be included?
                          Note: Setting recursive=True and include_containers=False
                                really doesn't make any sense, and will result in a 
                                garbled nonsensical tree structure!
        """
        # saves all container paths that have been created
        container_dict = {}
        root = urllib.parse.unquote(root)

        def get_or_create_container(path, container_object, special_name=None):
            if path in list(container_dict.keys()):
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
            if parent_path not in list(container_dict.keys()):
                parent_container = get_or_create_container(parent_path, None)
            else:
                parent_container = container_dict[parent_path]
            parent_container['containers'].append(container)

        
        root_container = get_or_create_container(root, None)
        
        for obj in object_list:
            if obj.is_container:
                if obj.path == root:
                    root_container['container_object'] = obj
                # should we retrieve containers?
                if not include_containers or (not recursive and obj.path != root+obj.slug+'/'):
                    continue 
                get_or_create_container(obj.path, obj)
            else:
                # should we retrieve leaves?
                if not include_leaves or (not recursive and obj.path != root):
                    continue 
                # this object will be attached to its parent in the tree by calling get_or_create_container(...)
                filescontainer = get_or_create_container(obj.path, None)
                filescontainer['objects'].append(obj)
            
        return root_container


class HierarchyPathMixin(object):
    """
    This mixin can be used in a hybrid add item + add container view.
    Not recommended to use in edit/delete views.
    """
    
    container_form_class = AddContainerForm
    container_form_prefix = 'container'
    
    # do we allow creating and showing folders beyond the root level?
    allow_deep_hierarchy = True
    
    def _apply_container_nature(self, container_form):
        """ Make necessary application to the passing form so that it is considered a container """
        container_form.instance.is_container = True
        container_form.instance.group = self.group

    def get_initial(self):
        """
        Supports calling /add under other objects,
        which creates a new object under the given object/container's path
        """
        initial = super(HierarchyPathMixin, self).get_initial()

        # if a slug is given in the URL, we check if its a container, and if so,
        # let the user create an object under that path
        # if it is an object, we let the user create a new object on the same level
        if 'slug' in list(self.kwargs.keys()):
            container = self.get_queryset().get(group=self.group, slug=self.kwargs.get('slug'))
            initial.update({'path': container.path})
        return initial

    def get(self, request, *args, **kwargs):
        """ Dual form splitting and initialization """
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        container_form_class = self.get_container_form_class()
        container_form = self.get_container_form(container_form_class)
        return super(HierarchyPathMixin, self).render_to_response(self.get_context_data(form=form, container_form=container_form))

    def post(self, request, *args, **kwargs):
        self.object = None

        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        container_form_class = self.get_container_form_class()
        self.container_form = self.get_container_form(container_form_class)
        
        if 'create_container' in request.POST:
            # The container_form needs a submit button with name="create_container"
            self._apply_container_nature(self.container_form)
            if self.container_form.is_valid():
                return self.container_form_valid(self.container_form)
            else:
                return self.container_form_invalid(self.container_form)
        else:
            if self.form.is_valid():
                return self.form_valid(self.form)
            else:
                return self.form_invalid(self.form)

    def get_container_form(self, container_form_class):
        class ModelAddContainerForm(container_form_class):
            class Meta(container_form_class.Meta):
                model = self.model
        return ModelAddContainerForm(**self.get_container_form_kwargs())

    def get_container_form_class(self):
        if self.container_form_class:
            return self.container_form_class
        raise AttributeError("container_form_class must not be None")

    def get_container_form_kwargs(self):
        kwargs = {'prefix': self.container_form_prefix}
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
            })
        return kwargs
    
    def form_valid(self, form):
        """
        Form for adding model objects.
        If the form is valid, we need to do pass the path retrieved from the
        slug over to the non-editable field
        """
        path = form.initial.get('path', None)
        if path:
            form.instance.path = path
        return super(HierarchyPathMixin, self).form_valid(form)
    
    def container_form_valid(self, container_form):
        """
        Form for adding hierarchy container objects.
        If the form is valid, we need to do the following:
        - Set instance's is_container to True
        - Set the instance's group
        - Set the path again once the slug has been established
        """
        path = self.form.initial.get('path', None)
        if path:
            container_form.instance.path = path
        
        self.object = container_form.save()
        # only after this save do we know the final slug
        # we still must add it to the end of our path if we're saving a container
        self.object.path += self.object.slug + '/'
        self.object.save()
        
        return HttpResponseRedirect(self.get_success_url())

    def container_form_invalid(self, container_form):
        # analog zu form_invalid()
        return self.render_to_response(self.get_context_data(container_form=container_form))

    def get_context_data(self, **kwargs):
        context = super(HierarchyPathMixin, self).get_context_data(**kwargs)
        if 'form' not in context and hasattr(self, 'form'):
            # if container_form_invalid() is called, the 'normal form'
            # is not defined in the rendering context.
            context['form'] = self.form
        if 'container_form' not in context and hasattr(self, 'container_form'):
            # if form_invalid() is called, the 'container form'
            # is not defined in the rendering context.
            context['container_form'] = self.container_form
        return context
    

class HierarchyDeleteMixin(object):
    """
    This mixin can be used in delete views. It deletes an object or container
    and all objects and containers inside.
    """

    def _get_objects_in_path(self, path):
        return self.model.objects.filter(path__startswith=path, group=self.group)

    def _delete_object(self, obj, request):
        """
        Sanity check: only delete a container if it is empty
        (there should only be one object (the container itself) with the
        path, because we have deleted all its objects before it!

        Returns 1 if given object could be deleted, 0 otherwise. That's handy
        for accumulating the sum of deleted objects
        """
        if obj.is_container:
            container_objects = self._get_objects_in_path(obj.path)
            if len(container_objects) > 1:
                msg = _('Container "%(title)s" could not be deleted because it contained objects that could not be deleted.') % {
                    'title': obj.title,
                }
                messages.error(request, msg)
                return 0
            
        if not check_object_write_access(obj, request.user):
            messages.error(request, _('You do not have permissions to delete "%(title)s".') % {'title': obj.title})
            return 0
        
        deleted_pk = obj.pk
        obj.delete()
        # check if deletion was successful
        try:
            check_obj = self.model.objects.get(pk=deleted_pk)
            msg = _('Object "%(title)s" could not be deleted.') % {
                'title': check_obj.title,
            }
            messages.error(request, msg)
            return 0
        except self.model.DoesNotExist:
            return 1

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.is_container and self.object.path == "/":
            raise PermissionDenied("The root file object cannot be deleted!")
        
        if self.object.is_container:
            del_list = list(self._get_objects_in_path(self.object.path))
        else:
            del_list = [self.object]

        # for a clean deletion, sort so that subelements are always before
        # their parents and objects always before containers on the same level
        del_list.sort(key=lambda o: len(o.path) + (0 if o.is_container else 1), reverse=True)

        total_objects = len(del_list)
        deleted_count = 0
        for obj in del_list:
            deleted_count += self._delete_object(obj, request)

        if deleted_count > 0:
            if deleted_count > 1 and deleted_count == total_objects:
                msg = _('%(numobjects)d objects were deleted successfully.') % {
                    'numobjects': deleted_count,
                }
                messages.success(request, msg)
            elif deleted_count == 1 and total_objects == 1:
                msg = _('Object "%(title)s" was deleted successfully.') % {
                    'title': obj.title,
                }
                messages.success(request, msg)
            else:
                msg = _('%(numobjects)d other objects were deleted.') % {
                    'numobjects': deleted_count,
                }
                messages.success(request, msg)

        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(HierarchyDeleteMixin, self).get_context_data(**kwargs)
        del_obj = kwargs.get('object', None)

        del_list = []
        if del_obj:
            if del_obj.is_container:
                # special handling for containers being deleted:
                path_objects = self._get_objects_in_path(del_obj.path)
                del_list.extend(path_objects)
            else:
                del_list.append(del_obj)

        context['objects_to_delete'] = del_list
        return context


class DisplayTaggedObjectsMixin(object):
    
    def get_object_querysets(self, group, cosinnus_apps=None, user=None):
        """ Returns all (still-lazy) querysets for BaseTaggableObjects in cosinnus apps.
            Can be filtered to be viewable by a certain user, or only publicly viewable,
            and can be filtered for a certain group only.
            @param cosinnus_apps: Returns objects for these models, or for all registered models if None 
                - example: ['cosinnus_etherpad.Etherpad', 'cosinnus_event.Event', 'cosinnus_file.FileEntry']
            @param group: Filter the objects to belong to this group, or any group if None
            @param user: Filter the objects to be viewable by this user, or an anonymous user if None """
            
        if user is None:
            user = AnonymousUser()
            
        querysets = []
        for registered_model in aor:
            app_label, model_name = registered_model.split('.')
            app_is_active = app_label not in group.get_deactivated_apps()
            
            # filter out unwanted model types if set in the Stream
            if not app_is_active or cosinnus_apps is not None and app_label not in cosinnus_apps:
                continue
            
            model_class = apps.get_model(app_label, model_name)
            
            # only use basic tagged models, not extending ones (to avoid duplicates)
            bases_modules = [base.__module__ for base in model_class.__bases__]
            if not 'cosinnus.models.tagged' in bases_modules:
                continue
            
            if hasattr(model_class, 'get_current'):
                # get a pre-filtered user-specific recent set for this model
                queryset = model_class.get_current(group, user)
            else:
                # get base collection of models for that type
                queryset = model_class._default_manager.all()
                # filter for read permissions for user
                queryset = filter_tagged_object_queryset_for_user(queryset, user)
                # filter folders
                if BaseHierarchicalTaggableObjectModel in model_class.__bases__:
                    queryset = model_class._default_manager.filter(is_container=False)
            
            querysets.append(queryset)
            
        return querysets
    
    def sort_and_limit_querysets(self, querysets, item_limit=10):
        """ Takes a list of querysets of tagged objects (like generated by ```self.get_object_querysets()``
            and returns a single list of sorted items, with ``item_limit`` number of items """
        
        items = sorted(chain(*querysets), key=lambda instance: getattr(instance, 'sort_key', 0), reverse=True) 
        items = items[:item_limit]
        return items
    
    def sort_and_limit_single_queryset(self, queryset, item_limit=10):
        return self.sort_and_limit_querysets([queryset], item_limit)


class EditViewWatchChangesMixin():
    """ A mixin for an EditView that handles watching the object and alerting
        any changes to watched attributed after a successful save. 
        In your view, define `changed_attr_watchlist` and `on_save_changed_attrs()` """
    
    # a list of attribute names for the view's object to be watched for changes
    # dotted attributes will be resolved (ie 'media_tag.location')
    changed_attr_watchlist = []
    
    watched_attr_vals = None
    edit_successful = False
    
    def __init__(self, *args, **kwargs):
        self.watched_attr_vals = {}
        return super(EditViewWatchChangesMixin, self).__init__(*args, **kwargs)
    
    def on_save_changed_attrs(self, obj, changed_attr_dict):
        """ Stub, implement this in your view 
            @param obj: The newly saved object.
            @param changed_attr_dict: k,v dict with k: changed attribue name, v: old value
        """
        pass
    
    def _compare_changed_obj(self, obj):
        changed_attrs = []
        for prop in self.changed_attr_watchlist:
            if self.watched_attr_vals[prop] != resolve_attributes(obj, prop):
                changed_attrs.append(prop)
        return changed_attrs
    
    def get_object(self, *args, **kwargs):
        obj = super(EditViewWatchChangesMixin, self).get_object(*args, **kwargs)
        if self.request.method.upper() == 'POST' and not self.watched_attr_vals:
            for prop in self.changed_attr_watchlist:
                self.watched_attr_vals[prop] = resolve_attributes(obj, prop)
        return obj
    
    def post(self, *args, **kwargs):
        ret = super(EditViewWatchChangesMixin, self).post(*args, **kwargs)
        if self.edit_successful:
            changed_attrs = self._compare_changed_obj(self.object)
            if changed_attrs:
                changed_attr_dict = dict([(prop, self.watched_attr_vals[prop]) for prop in changed_attrs])
                self.on_save_changed_attrs(self.object, changed_attr_dict)
        return ret
    
    def form_valid(self, form):
        ret = super(EditViewWatchChangesMixin, self).form_valid(form)
        self.edit_successful = True
        return ret
    
    def forms_valid(self, form, inlines):
        ret = super(EditViewWatchChangesMixin, self).forms_valid(form, inlines)
        self.edit_successful = True
        return ret
    
    def form_invalid(self, form):
        ret = super(EditViewWatchChangesMixin, self).form_invalid(form)
        self.edit_successful = False
        return ret
    
    def forms_invalid(self, form, inlines):
        ret = super(EditViewWatchChangesMixin, self).forms_invalid(form, inlines)
        self.edit_successful = False
        return ret


class RecordLastVisitedMixin(object):
    """ Mixin for views of models that use the `LastVisitedMixin`.
        While this view is used, any successful call to `render_to_response`
        will cause a LastVisited record to be created for the  """
    
    def render_to_response(self, *args, **kwargs):
        response = super(RecordLastVisitedMixin, self).render_to_response(*args, **kwargs)
        self.mark_visited()
        return response
    
    def mark_visited(self):
        if settings.DEBUG and getattr(self, 'object', None) is None:
            raise ImproperlyConfigured('A view with `RecordLastVisitedMixin`' +\
                'was trying to log a LastVisit, but no `self.object` could be found!')
        if self.request.user.is_authenticated and getattr(self, 'object', None) is not None:
            self.object.mark_visited(self.request.user)
    
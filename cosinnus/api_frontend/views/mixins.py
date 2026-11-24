from rest_framework.response import Response


class ViewSetActionMixin:
    """Viewset mixin for generic viewset action processing."""

    def detail_action_response(self, request, action_serializer, partial=False, response_serializer=None):
        """
        Return viewset detail action response using the action_serializer.
        :param request: request
        :param action_serializer: serializer class
        :param partial: do a partial serialization
        :param response_serializer: Serializer for the updated instance after a post. Useful if a viewset
            action should return the serialized instance instead of the action-serializer data, e.g. when posting a
            NoteComment we want the serialized Note instead of the comment to be returned.
        @return: serialized data
        """
        instance = self.get_object()
        serializer_context = self.get_serializer_context()
        if request.method == 'GET':
            serializer = action_serializer(instance, context=serializer_context)
        else:
            serializer = action_serializer(instance, data=request.data, partial=partial, context=serializer_context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            if response_serializer:
                serializer = response_serializer(instance, context=serializer_context)
        return Response(serializer.data)

    def list_action_response(self, request, action_serializer, queryset=None):
        """
        Returns a paginated response for the queryset serialized with action_serializer.
        :param request: request
        :param action_serializer: serializer class to use
        :param queryset: data queryset or list
        @return: serialized data
        """
        serializer_context = self.get_serializer_context()
        if request.method == 'GET':
            # handle get list
            page = self.paginate_queryset(queryset)
            if page is not None:
                # return paginated response
                serializer = action_serializer(page, many=True, context=serializer_context)
                return self.get_paginated_response(serializer.data)
            # return non-paginated response
            serializer = action_serializer(queryset, many=True, context=serializer_context)
        else:
            # create object on post
            serializer = action_serializer(data=request.data, context=serializer_context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

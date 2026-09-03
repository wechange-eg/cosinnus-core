from rest_framework.response import Response


class ViewSetActionMixin:
    """Viewset mixin for generic viewset action processing."""

    def detail_action_response(self, request, partial=False):
        """
        Return viewset detail action response using the serializer set in get_serializer_class.
        @return: serialized data
        """
        instance = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
        else:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

    def list_action_response(self, queryset):
        """Returns a paginated response for the queryset."""
        page = self.paginate_queryset(queryset)
        if page is not None:
            # return paginated response
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        # return non-paginated response
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

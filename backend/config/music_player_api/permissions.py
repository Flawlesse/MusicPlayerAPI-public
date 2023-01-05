from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSameUserOrReadonly(BasePermission):
    """Used for models with 'added_by' field present."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user == obj.added_by
        )

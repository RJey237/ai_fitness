from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    message = 'Adding customers not allowed.'

    def has_permission(self, request, view):
        
        if request.user.is_authenticated:
            return request.user.user_type == 'owner'
        
        return False

from rest_framework.permissions import BasePermission

class IsGuestUser(BasePermission):
    """
    request.user가 존재하고 익명(Anonymous) 유저가 아닌지 확인
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
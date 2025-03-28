from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='admin').exists()
    
class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='teacher').exists()

class CanViewCBC(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name__in=['admin', 'teacher', 'student']).exists()

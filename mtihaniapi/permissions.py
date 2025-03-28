from rest_framework.permissions import BasePermission

adminRole = 'admin'
teacherRole = 'teacher'
studentRole ='student'

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name=adminRole).exists()
    
class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name=teacherRole).exists()

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name=studentRole).exists()

class CanViewCBC(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name__in=[adminRole, teacherRole, studentRole]).exists()

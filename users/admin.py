from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    model = User

    list_display = ('username', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'name')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'role', 'name')}),
        ('학생 정보', {'fields': ('major',)}),
        ('교수 정보', {'fields': ('department',)}),
        ('권한 설정', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('로그 기록', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'name', 'major', 'department'),
        }),
    )

admin.site.register(User, UserAdmin)
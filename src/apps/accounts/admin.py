from django.contrib import admin
from django.contrib.auth import admin as auth_admin

from accounts.models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    model = User
    add_form_template = ''
    inlines = [ProfileInline]
    search_fields = ['email', 'first_name', 'surname']
    list_filter = ['is_superuser', 'is_staff', 'is_active']
    list_display = ['email', 'first_name', 'surname', 'is_active', 'is_staff']
    list_display_links = ['email']
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['email']
    fieldsets = (
        (
            'Informações de login',
            {
                'fields': (
                    'email',
                    'password',
                )
            },
        ),
        (
            'Informações pessoais',
            {
                'fields': (
                    'first_name',
                    'surname',
                )
            },
        ),
        (
            'Permissões',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                ),
            },
        ),
        (
            'Datas importantes',
            {
                'fields': (
                    'last_login',
                    'date_joined',
                )
            },
        ),
    )
    add_fieldsets = (
        (
            'Informações de importantes',
            {
                'fields': (
                    'email',
                    'first_name',
                    'surname',
                    'password1',
                    'password2',
                ),
            },
        ),
    )

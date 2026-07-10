from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.models import AuditLog, LoginLog, Permission, RefreshToken, Role, User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "mfa_enabled")
    search_fields = ("username", "email", "first_name", "last_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("SGHL", {"fields": ("phone", "mfa_enabled", "must_change_password", "last_login_ip")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "name", "module")
    list_filter = ("module",)
    search_fields = ("codename", "name")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ("username_attempt", "status", "ip_address", "created_at")
    list_filter = ("status",)
    readonly_fields = ("user", "username_attempt", "status", "ip_address", "user_agent", "failure_reason", "created_at")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action_type", "resource_type", "resource_id")
    list_filter = ("action_type", "resource_type")
    readonly_fields = (
        "timestamp", "user", "ip_address", "action_type",
        "resource_type", "resource_id", "old_value", "new_value", "metadata",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "revoked", "expires_at", "created_at")
    list_filter = ("revoked",)

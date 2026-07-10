import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class TimestampedModel(models.Model):
    """Mixin created_at / updated_at."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OptimisticLockMixin(models.Model):
    """Verrouillage optimiste pour dossiers critiques."""

    version = models.PositiveIntegerField(default=1)

    class Meta:
        abstract = True


class User(AbstractUser):
    """Utilisateur SGHL avec support MFA."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("email", unique=True)
    phone = models.CharField(max_length=20, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True)
    must_change_password = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username

    def has_perm_code(self, codename: str) -> bool:
        if self.is_superuser:
            return True
        return self.roles.filter(
            is_active=True,
            role__permissions__permission__codename=codename,
        ).exists()

    def get_role_codes(self) -> list[str]:
        return list(
            self.roles.filter(is_active=True).values_list("role__code", flat=True)
        )

    def get_permission_codes(self) -> list[str]:
        if self.is_superuser:
            from core.services.rbac import DEFAULT_PERMISSIONS

            return [p[0] for p in DEFAULT_PERMISSIONS]
        return list(
            self.roles.filter(is_active=True)
            .values_list("role__permissions__permission__codename", flat=True)
            .distinct()
        )


class Role(TimestampedModel):
    """Profil RBAC : Admin, Secrétaire, Médecin, etc."""

    ADMIN = "ADMIN"
    SECRETARY = "SECRETARY"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    BIOLOGIST = "BIOLOGIST"
    PHARMACIST = "PHARMACIST"
    ACCOUNTANT = "ACCOUNTANT"
    PATIENT = "PATIENT"

    ROLE_CHOICES = [
        (ADMIN, "Administrateur"),
        (SECRETARY, "Secrétaire"),
        (ACCOUNTANT, "Comptable"),
        (DOCTOR, "Médecin"),
        (NURSE, "Infirmier(ère)"),
        (BIOLOGIST, "Biologiste"),
        (PHARMACIST, "Pharmacien"),
        (PATIENT, "Patient"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, choices=ROLE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "rôle"
        verbose_name_plural = "rôles"

    def __str__(self):
        return self.name


class Permission(TimestampedModel):
    """Permission granulaire du système."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    module = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "permission"
        verbose_name_plural = "permissions"
        ordering = ["module", "codename"]

    def __str__(self):
        return f"{self.module}.{self.codename}"


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )

    class Meta:
        unique_together = [("role", "permission")]


class UserRole(TimestampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
    )

    class Meta:
        unique_together = [("user", "role")]


class RefreshToken(TimestampedModel):
    """Refresh token JWT avec rotation et révocation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)
    replaced_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
    )
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "refresh token"
        verbose_name_plural = "refresh tokens"


class LoginLog(TimestampedModel):
    """Journal des connexions."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    LOGOUT = "LOGOUT"

    STATUS_CHOICES = [
        (SUCCESS, "Succès"),
        (FAILURE, "Échec"),
        (LOGOUT, "Déconnexion"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_logs",
    )
    username_attempt = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "journal de connexion"
        verbose_name_plural = "journaux de connexion"
        ordering = ["-created_at"]


class AuditLog(models.Model):
    """Livre-journal immuable — append-only."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    READ = "READ"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VALIDATE = "VALIDATE"
    PUBLISH = "PUBLISH"
    TRANSFER = "TRANSFER"

    ACTION_CHOICES = [
        (CREATE, "Création"),
        (UPDATE, "Modification"),
        (DELETE, "Suppression"),
        (READ, "Consultation"),
        (LOGIN, "Connexion"),
        (LOGOUT, "Déconnexion"),
        (VALIDATE, "Validation"),
        (PUBLISH, "Publication"),
        (TRANSFER, "Transfert"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.CharField(max_length=64, blank=True, db_index=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "audit log"
        verbose_name_plural = "audit logs"
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("Les entrées d'audit sont immuables.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Les entrées d'audit ne peuvent pas être supprimées.")


class EmailOTP(TimestampedModel):
    """Code OTP email à usage unique (inscription patient, etc.)."""

    REGISTRATION = "REGISTRATION"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_otps")
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=32, default=REGISTRATION)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "code OTP email"
        ordering = ["-created_at"]

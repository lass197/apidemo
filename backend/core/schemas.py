from datetime import date, datetime
from typing import Optional
from uuid import UUID

from ninja import Schema


class LoginIn(Schema):
    username: str
    password: str
    mfa_code: Optional[str] = None


class PatientRegisterIn(Schema):
    email: str
    password: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str = ""
    username: Optional[str] = None


class RegisterPendingOut(Schema):
    detail: str
    email: str
    user_id: UUID
    otp_sent: bool


class VerifyEmailOtpIn(Schema):
    email: str
    code: str
    password: str


class ResendOtpIn(Schema):
    email: str


class MfaSetupOut(Schema):
    secret: str
    provisioning_uri: str


class MfaConfirmIn(Schema):
    code: str


class RefreshIn(Schema):
    refresh_token: str


class LogoutIn(Schema):
    refresh_token: Optional[str] = None


class UserOut(Schema):
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str
    roles: list[str]
    permissions: list[str]
    mfa_enabled: bool
    email_verified: bool = False


class TokenOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserOut


class RefreshOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class MessageOut(Schema):
    detail: str


class HealthOut(Schema):
    status: str
    version: str
    database: str
    timestamp: datetime


class ErrorOut(Schema):
    detail: str

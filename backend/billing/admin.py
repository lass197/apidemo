from django.contrib import admin

from billing.models import (
    AccountingEntry,
    InsuranceProvider,
    Invoice,
    InvoiceLine,
    PatientInsurance,
    Payment,
    ServicePrice,
)


@admin.register(InsuranceProvider)
class InsuranceProviderAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "coverage_rate", "is_active")


@admin.register(PatientInsurance)
class PatientInsuranceAdmin(admin.ModelAdmin):
    list_display = ("patient", "provider", "policy_number", "is_primary")


@admin.register(ServicePrice)
class ServicePriceAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "service_type", "unit_price")
    list_filter = ("service_type",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "patient", "status", "patient_amount", "paid_amount")
    list_filter = ("status",)


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "total")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "paid_at")
    list_filter = ("method",)


@admin.register(AccountingEntry)
class AccountingEntryAdmin(admin.ModelAdmin):
    list_display = ("entry_date", "account_code", "label", "entry_type", "amount")
    readonly_fields = ("entry_date", "account_code", "label", "entry_type", "amount", "invoice", "created_by")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin

from laboratory.models import LabOrder, LabResult, LabSample, LabTestType


@admin.register(LabTestType)
class LabTestTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "price", "sample_type", "is_active")
    search_fields = ("code", "name")


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    list_display = ("patient", "test_type", "status", "priority", "created_at")
    list_filter = ("status", "priority")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LabSample)
class LabSampleAdmin(admin.ModelAdmin):
    list_display = ("lab_order", "barcode", "collected_at")


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ("lab_order", "is_abnormal", "locked", "entered_at")
    readonly_fields = ("locked",)

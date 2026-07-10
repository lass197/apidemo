from django.contrib import admin

from clinical.models import (
    Bed,
    Building,
    CarePlan,
    CareTask,
    Consultation,
    Department,
    Hospitalization,
    ICD10Code,
    InterHospitalTransfer,
    PartnerHospital,
    Patient,
    PatientMovementHistory,
    Prescription,
    PrescriptionItem,
    Room,
    TransferLog,
    VitalSign,
)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "date_of_birth", "phone", "is_active")
    search_fields = ("last_name", "first_name", "email", "phone")


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("building", "code", "name", "is_active")
    list_filter = ("building",)


class BedInline(admin.TabularInline):
    model = Bed
    extra = 0


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("department", "number", "floor", "is_active")
    inlines = [BedInline]


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ("room", "label", "status", "is_active")
    list_filter = ("status",)


@admin.register(Hospitalization)
class HospitalizationAdmin(admin.ModelAdmin):
    list_display = ("patient", "bed", "referring_doctor", "admission_date", "status")
    list_filter = ("status",)
    readonly_fields = ("version",)


admin.site.register(ICD10Code)
admin.site.register(Consultation)
admin.site.register(Prescription)
admin.site.register(PrescriptionItem)
admin.site.register(CarePlan)
admin.site.register(CareTask)
admin.site.register(VitalSign)
admin.site.register(TransferLog)


@admin.register(PartnerHospital)
class PartnerHospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "available_beds", "total_beds", "accepts_transfers", "is_active")
    list_filter = ("is_active", "accepts_transfers")


@admin.register(InterHospitalTransfer)
class InterHospitalTransferAdmin(admin.ModelAdmin):
    list_display = ("hospitalization", "partner_hospital", "status", "requested_by", "validated_at")
    list_filter = ("status",)


@admin.register(PatientMovementHistory)
class PatientMovementHistoryAdmin(admin.ModelAdmin):
    list_display = ("event_type", "patient", "event_at", "performed_by", "document")
    list_filter = ("event_type",)
    readonly_fields = ("created_at", "updated_at")

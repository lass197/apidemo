from django.contrib import admin

from hr.models import Appointment, ChatMessage, DoctorAvailability, MedicationReminder, Shift


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("staff", "department_code", "start_at", "end_at")


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "start_at", "end_at", "is_bookable")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "scheduled_at", "status")
    list_filter = ("status",)


admin.site.register(ChatMessage)
admin.site.register(MedicationReminder)

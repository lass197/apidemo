from django.contrib import admin

from pharmacy.models import Medicine, StockLot, StockMovement


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "unit_price", "reorder_threshold", "is_active")
    search_fields = ("code", "name")


@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ("medicine", "lot_number", "quantity", "expiry_date")
    list_filter = ("expiry_date",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("lot", "movement_type", "quantity", "created_at")
    list_filter = ("movement_type",)

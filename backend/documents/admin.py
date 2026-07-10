from django.contrib import admin

from documents.models import Document, DocumentAccessLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "patient", "document_type", "mime_type", "created_at")
    list_filter = ("document_type",)
    search_fields = ("title", "patient__last_name")


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = ("document", "user", "action", "accessed_at")
    readonly_fields = ("document", "user", "accessed_at", "ip_address", "action")

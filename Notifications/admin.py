from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "application", "message", "channel", "status", "created_at")
    search_fields = ("user", "message")
    list_filter = ("user", "created_at")




from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "application", "amount", "payment_method", "payment_date")
    search_fields = ("transaction_id", "application__reference_no")
    list_filter = ("payment_method", "payment_date")

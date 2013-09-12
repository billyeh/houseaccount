from brothers.models import Brother, HouseAccount, Payment, PaymentDue
from django.contrib import admin

class PaymentInline(admin.TabularInline):
  model = Payment
  extra = 1

class BrotherAdmin(admin.ModelAdmin):
  fieldsets = [
    (None, {'fields': ['name', 'user']}),
    ('Date Information', {'fields': ['created_date'], 'classes': ['collapse']}),
  ]
  inlines = [PaymentInline]
  list_display = ('name', 'created_date')
  search_fields = ['name']

admin.site.register(Brother, BrotherAdmin)
admin.site.register(Payment)
admin.site.register(HouseAccount)
admin.site.register(PaymentDue)

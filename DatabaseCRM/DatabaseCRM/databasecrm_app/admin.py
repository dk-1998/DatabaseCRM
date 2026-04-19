from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Client, Order

# Prilagođeni prikaz User modela
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email")  # samo username i email
    list_filter = ()  # ukloni filtere ako ne želiš dodatne
    search_fields = ("username", "email")  # omogući pretragu po username/email
    ordering = ("username",)

# prvo ukloni default registraciju User modela
admin.site.unregister(User)
# pa registruj naš prilagođeni
admin.site.register(User, CustomUserAdmin)

# Registracija tvojih modela
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("product_name", "price", "client", "created_at")

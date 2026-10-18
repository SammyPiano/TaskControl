from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Empresa, Usuario


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "rnc", "telefono", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre", "rnc")


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "empresa", "rol", "is_active")
    list_filter = ("rol", "empresa", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Empresa y rol", {"fields": ("empresa", "rol", "cargo", "telefono", "zona")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Empresa y rol", {"fields": ("empresa", "rol")}),)

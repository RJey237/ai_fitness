from django.contrib import admin
from .models import CustomUser, Bmi


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "phone")


@admin.register(Bmi)
class BmiAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "height", "weight")

from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'is_active'
    )

    prepopulated_fields = {
        'slug': ('name',)
    }

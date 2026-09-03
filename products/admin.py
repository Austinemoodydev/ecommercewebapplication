from django.contrib import admin
from .models import Brand, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "category",
        "brand",
        "current_price",
        "stock",
        "reserved_stock",
        "available_stock",
        "featured",
        "is_active",
    )

    list_filter = (
        "category",
        "brand",
        "featured",
        "is_active",
    )

    search_fields = (
        "name",
        "sku",
    )

    list_editable = (
        "featured",
        "is_active",
    )

    prepopulated_fields = {
        "slug": ("name",)
    }

    inlines = [ProductImageInline]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    prepopulated_fields = {
        "slug": ("name",)
    }


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "sku", "price", "stock", "is_active")
    list_filter = ("is_active", "product")
    search_fields = ("product__name", "name", "sku")
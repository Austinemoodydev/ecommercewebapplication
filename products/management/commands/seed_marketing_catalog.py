from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from categories.models import Category
from products.models import (
    Brand,
    Product,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
)


PRODUCTS = [
    {"name": "Studio Wireless Headphones", "category": "Electronics & Acessories", "brand": "UrbanTech", "price": "8499", "discount": "6999", "stock": 34, "image": "wireless-headphones.png", "featured": True, "description": "Comfortable over-ear wireless headphones with rich sound, soft memory-foam cushions, long battery life and a foldable travel-friendly design.", "option": ("Colour", [("Midnight Black", "#111827", "6999", 18), ("Silver", "#CBD5E1", "6999", 16)])},
    {"name": "Samsung Galaxy A55 5G", "category": "Electronics & Acessories", "brand": "Samsung", "price": "52999", "discount": "48999", "stock": 18, "image": "smartphone.png", "featured": True, "description": "A refined 5G smartphone with a vivid display, dependable all-day battery, versatile cameras and ample storage for everyday work and entertainment.", "option": ("Storage", [("128 GB", "", "48999", 11), ("256 GB", "", "56999", 7)])},
    {"name": "HP Pavilion 15 Laptop", "category": "Electronics & Acessories", "brand": "HP", "price": "89999", "discount": "84999", "stock": 12, "image": "laptop.png", "featured": True, "description": "A slim 15-inch productivity laptop designed for study, office work and entertainment, with a bright display and comfortable full-size keyboard.", "option": ("Configuration", [("8 GB / 512 GB", "", "84999", 7), ("16 GB / 1 TB", "", "109999", 5)])},
    {"name": "Lenovo Tab M11", "category": "Electronics & Acessories", "brand": "Lenovo", "price": "34999", "discount": "31999", "stock": 21, "image": "tablet.png", "featured": False, "description": "A lightweight tablet with a large display and stylus support for streaming, reading, note-taking and everyday family use."},
    {"name": "ActiveFit Smart Watch", "category": "Electronics & Acessories", "brand": "UrbanTech", "price": "6999", "discount": "5499", "stock": 42, "image": "smartwatch.png", "featured": True, "description": "Track daily activity, workouts, sleep and notifications with a comfortable water-resistant smartwatch made for an active lifestyle."},

    {"name": "Dove Deep Moisture Body Wash", "category": "Beauty & Personal care", "brand": "Dove", "price": "1350", "discount": "1199", "stock": 56, "image": "body-wash.png", "featured": False, "description": "A gentle 500 ml moisturizing body wash that cleanses without leaving skin feeling dry, suitable for an easy everyday care routine."},
    {"name": "Vaseline Cocoa Radiant Lotion", "category": "Beauty & Personal care", "brand": "Vaseline", "price": "1450", "discount": "1299", "stock": 48, "image": "body-lotion.png", "featured": True, "description": "A nourishing 400 ml body lotion with a warm cocoa-inspired scent, formulated to leave dry skin feeling smooth and comfortable."},
    {"name": "Daily Defence Face Sunscreen SPF 50", "category": "Beauty & Personal care", "brand": "GlowCare", "price": "1899", "discount": "1599", "stock": 39, "image": "sunscreen.png", "featured": True, "description": "Lightweight broad-spectrum SPF 50 face sunscreen with a comfortable non-greasy finish for everyday outdoor protection."},
    {"name": "Amber Noir Eau de Parfum", "category": "Beauty & Personal care", "brand": "GlowCare", "price": "4299", "discount": "3799", "stock": 24, "image": "perfume.png", "featured": False, "description": "An elegant 100 ml unisex fragrance combining warm amber, soft woods and subtle spice for day-to-evening wear."},
    {"name": "Strength & Shine Shampoo", "category": "Beauty & Personal care", "brand": "GlowCare", "price": "1199", "discount": "999", "stock": 62, "image": "shampoo.png", "featured": False, "description": "A cleansing shampoo for normal hair that helps leave every wash feeling fresh, manageable and naturally glossy.", "option": ("Size", [("400 ml", "", "999", 38), ("750 ml", "", "1699", 24)])},

    {"name": "Nike-Inspired Everyday Runner", "category": "Clothing", "brand": "Nike", "price": "7499", "discount": "6499", "stock": 35, "image": "sneakers.png", "featured": True, "description": "Clean everyday running shoes with cushioned support, breathable panels and a versatile white-and-navy finish.", "option": ("Shoe size", [("40", "", "6499", 6), ("41", "", "6499", 7), ("42", "", "6499", 9), ("43", "", "6499", 7), ("44", "", "6499", 6)])},
    {"name": "Adidas Essentials Pullover Hoodie", "category": "Clothing", "brand": "Adidas", "price": "5999", "discount": "4999", "stock": 32, "image": "hoodie.png", "featured": True, "description": "A soft charcoal pullover hoodie with a relaxed everyday fit, warm brushed interior and practical front pocket.", "option": ("Size", [("S", "", "4999", 6), ("M", "", "4999", 10), ("L", "", "4999", 10), ("XL", "", "4999", 6)])},
    {"name": "Puma Classic Cotton Polo", "category": "Clothing", "brand": "Puma", "price": "3299", "discount": "2799", "stock": 44, "image": "polo.png", "featured": False, "description": "A smart deep-blue cotton polo shirt with a clean collar and comfortable regular fit for work or casual weekends.", "option": ("Size", [("S", "", "2799", 8), ("M", "", "2799", 13), ("L", "", "2799", 14), ("XL", "", "2799", 9)])},
    {"name": "Classic Blue Denim Jacket", "category": "Clothing", "brand": "Urban Thread", "price": "5499", "discount": "4799", "stock": 29, "image": "denim-jacket.png", "featured": False, "description": "A timeless medium-wash denim jacket with useful pockets and an easy layering fit for cool evenings and casual outfits."},
    {"name": "City Explorer Travel Backpack", "category": "Clothing", "brand": "Urban Thread", "price": "4699", "discount": "3999", "stock": 37, "image": "backpack.png", "featured": True, "description": "A durable multi-compartment travel backpack with a padded laptop section, organized pockets and comfortable adjustable straps."},

    {"name": "HomePro 1.5L Glass Blender", "category": "Home & Kitchen", "brand": "HomePro", "price": "6999", "discount": "5999", "stock": 26, "image": "blender.png", "featured": True, "description": "A powerful countertop blender with a 1.5-litre glass jar for smoothies, sauces and everyday food preparation."},
    {"name": "HomePro Digital Air Fryer 5L", "category": "Home & Kitchen", "brand": "HomePro", "price": "12999", "discount": "10999", "stock": 19, "image": "air-fryer.png", "featured": True, "description": "A spacious 5-litre digital air fryer for convenient family meals with simple temperature and timer controls."},
    {"name": "HomePro Stainless Cookware Set", "category": "Home & Kitchen", "brand": "HomePro", "price": "15499", "discount": "13499", "stock": 15, "image": "cookware.png", "featured": False, "description": "A coordinated stainless-steel cookware set with essential pots, pan and fitted lids for a well-equipped everyday kitchen."},
    {"name": "HomePro Compact Coffee Maker", "category": "Home & Kitchen", "brand": "HomePro", "price": "8499", "discount": "7299", "stock": 23, "image": "coffee-maker.png", "featured": False, "description": "A compact drip coffee maker with a clear glass carafe, reusable filter basket and straightforward morning operation."},
    {"name": "Premium Cotton Bedsheet Set", "category": "Home & Kitchen", "brand": "HomePro", "price": "3999", "discount": "3299", "stock": 40, "image": "bedsheets.png", "featured": True, "description": "A soft sage-green cotton bedsheet set with matching pillowcases for a calm, coordinated and comfortable bedroom.", "option": ("Bed size", [("4 × 6 ft", "", "3299", 12), ("5 × 6 ft", "", "3799", 15), ("6 × 6 ft", "", "4299", 13)])},
]


class Command(BaseCommand):
    help = "Create or refresh the 20-product marketing demonstration catalogue."

    def _brand(self, name):
        brand = Brand.objects.filter(name__iexact=name).first()
        if brand:
            if not brand.is_active:
                brand.is_active = True
                brand.save(update_fields=["is_active"])
            return brand
        base_slug = slugify(name)
        slug = base_slug
        suffix = 2
        while Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return Brand.objects.create(name=name, slug=slug, is_active=True)

    def _variants(self, product, option_spec):
        if not option_spec:
            return 0
        option_name, choices = option_spec
        option, _ = ProductOption.objects.update_or_create(
            product=product,
            name=option_name,
            defaults={"position": 0},
        )
        keep_variant_ids = []
        keep_value_ids = []
        for position, (label, colour, price, stock) in enumerate(choices):
            value, _ = ProductOptionValue.objects.update_or_create(
                option=option,
                value=label,
                defaults={"colour_code": colour, "position": position},
            )
            variant, _ = ProductVariant.objects.update_or_create(
                product=product,
                name=label,
                defaults={
                    "price": Decimal(price),
                    "stock": stock,
                    "reserved_stock": 0,
                    "low_stock_threshold": 3,
                    "is_active": True,
                    "colour": label if colour else "",
                    "colour_code": colour,
                },
            )
            variant.option_values.set([value])
            keep_variant_ids.append(variant.pk)
            keep_value_ids.append(value.pk)
        ProductVariant.objects.filter(product=product).exclude(pk__in=keep_variant_ids).update(is_active=False)
        option.values.exclude(pk__in=keep_value_ids).delete()
        return len(keep_variant_ids)

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {
            category.name: category
            for category in Category.objects.filter(
                name__in={item["category"] for item in PRODUCTS}
            )
        }
        missing = sorted({item["category"] for item in PRODUCTS} - set(categories))
        if missing:
            self.stderr.write(self.style.ERROR(f"Missing categories: {', '.join(missing)}"))
            return

        created_count = 0
        variant_count = 0
        for item in PRODUCTS:
            brand = self._brand(item["brand"])
            slug = slugify(item["name"])
            product, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "category": categories[item["category"]],
                    "brand": brand,
                    "name": item["name"],
                    "description": item["description"],
                    "price": Decimal(item["price"]),
                    "discount_price": Decimal(item["discount"]),
                    "stock": item["stock"],
                    "reserved_stock": 0,
                    "low_stock_threshold": 5,
                    "image": f"products/demo/{Path(item['image']).with_suffix('.webp').name}",
                    "featured": item["featured"],
                    "is_active": True,
                },
            )
            created_count += int(created)
            variant_count += self._variants(product, item.get("option"))

        self.stdout.write(self.style.SUCCESS(
            f"Marketing catalogue ready: {len(PRODUCTS)} products "
            f"({created_count} created, {len(PRODUCTS) - created_count} refreshed), "
            f"{variant_count} active variants configured."
        ))

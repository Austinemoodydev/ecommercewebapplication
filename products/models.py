from django.db import models
from django.utils.text import slugify
from uuid import uuid4
from categories.models import Category

class ActiveProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)

    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="products"
    )

    name = models.CharField(max_length=255)

    slug = models.SlugField(unique=True)

    description = models.TextField()

    sku = models.CharField(max_length=50, unique=True, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)

    low_stock_threshold = models.PositiveIntegerField(default=5)

    image = models.ImageField(upload_to="products/")

    featured = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active = ActiveProductManager()

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.sku:
            self.sku = self.sku.strip().upper()
            super().save(*args, **kwargs)
            return

        self.sku = f"AUTO-{uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
        category_code = "".join(character for character in self.category.name.upper() if character.isalnum())[:3] or "GEN"
        brand_name = self.brand.name if self.brand_id else "General"
        brand_code = "".join(character for character in brand_name.upper() if character.isalnum())[:3] or "GEN"
        generated_sku = f"{category_code}-{brand_code}-{self.pk:04d}"
        Product.objects.filter(pk=self.pk).update(sku=generated_sku)
        self.sku = generated_sku

    @property
    def current_price(self):
        return self.discount_price or self.price

    
    @property
    def in_stock(self):
        return self.available_stock > 0

    @property
    def available_stock(self):
        return max(self.stock - self.reserved_stock, 0)

    @property
    def average_rating(self):
        result = self.reviews.aggregate(models.Avg("rating"))
        avg = result["rating__avg"]
        return round(avg, 1) if avg else 0

    @property
    def review_count(self):
        return self.reviews.count()

    def __str__(self):
        return self.name       
        
class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="products/gallery/")

    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.product.name} Image"


class ProductOption(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="options",
    )
    name = models.CharField(max_length=50)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("product", "name"),
                name="unique_product_option_name",
            )
        ]

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class ProductOptionValue(models.Model):
    option = models.ForeignKey(
        ProductOption,
        on_delete=models.CASCADE,
        related_name="values",
    )
    value = models.CharField(max_length=80)
    colour_code = models.CharField(max_length=7, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("option", "value"),
                name="unique_product_option_value",
            )
        ]

    def __str__(self):
        return f"{self.option.name}: {self.value}"


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=100)
    sku = models.CharField(max_length=50, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    colour = models.CharField(max_length=50, blank=True)
    colour_code = models.CharField(max_length=7, blank=True)
    image = models.ImageField(
        upload_to="products/variants/",
        blank=True,
        null=True,
    )
    option_values = models.ManyToManyField(
        ProductOptionValue,
        blank=True,
        related_name="variants",
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)

    low_stock_threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)

    @property
    def current_price(self):
        return self.price if self.price is not None else self.product.current_price

    @property
    def available_stock(self):
        return max(self.stock - self.reserved_stock, 0)

    @property
    def display_name(self):
        selected_values = sorted(
            self.option_values.all(),
            key=lambda value: (
                value.option.position,
                value.position,
                value.id,
            ),
        )
        if selected_values:
            return " / ".join(
                f"{value.option.name}: {value.value}"
                for value in selected_values
            )
        if self.colour:
            return f"{self.name} — {self.colour}"
        return self.name

    def __str__(self):
        return f"{self.product.name} - {self.display_name}"

    def save(self, *args, **kwargs):
        if self.sku:
            self.sku = self.sku.strip().upper()
            super().save(*args, **kwargs)
            return
        self.sku = f"AUTO-{uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
        generated_sku = f"{self.product.sku}-V{self.pk:02d}"[:50]
        ProductVariant.objects.filter(pk=self.pk).update(sku=generated_sku)
        self.sku = generated_sku

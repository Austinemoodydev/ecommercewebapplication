class ProductFilter:

    @staticmethod
    def apply(products, request):

        category = request.GET.get("category")
        brand = request.GET.get("brand")
        sort = request.GET.get("sort")

        if category:
            products = products.filter(
                category__slug=category
            )

        if brand:
            products = products.filter(
                brand__slug=brand
            )

        if sort == "price_low":
            products = products.order_by("price")

        elif sort == "price_high":
            products = products.order_by("-price")

        elif sort == "name":
            products = products.order_by("name")

        else:
            products = products.order_by("-created_at")

        return products
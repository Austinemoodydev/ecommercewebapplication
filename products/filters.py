class ProductFilter:

    @staticmethod
    def apply(products, request):
        categories = [value for value in request.GET.getlist("category") if value]
        brands = [value for value in request.GET.getlist("brand") if value]
        sort = request.GET.get("sort")

        if categories:
            products = products.filter(
                category__slug__in=categories
            )

        if brands:
            products = products.filter(
                brand__slug__in=brands
            )

        if sort == "price_low":
            products = products.order_by("price")

        elif sort == "price_high":
            products = products.order_by("-price")

        elif sort == "name":
            products = products.order_by("name")

        else:
            products = products.order_by("-created_at")

        return products.distinct()

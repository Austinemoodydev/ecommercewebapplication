from products.selectors.product_selector import ProductSelector


class ProductService:

    @staticmethod
    def featured_products(limit=8):

        return ProductSelector.featured()[:limit]

    @staticmethod
    def get_product(slug):

        return ProductSelector.by_slug(slug)
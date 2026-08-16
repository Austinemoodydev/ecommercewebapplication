from products.selectors.product_selector import ProductSelector


class SearchService:

    @staticmethod
    def search_products(query):

        if not query:
            return ProductSelector.get_active_products()

        return ProductSelector.search(query)
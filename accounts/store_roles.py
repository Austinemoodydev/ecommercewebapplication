STORE_OWNER = "Store Owner"
STORE_MANAGER = "Store Manager"
ORDER_STAFF = "Orders Staff"
INVENTORY_STAFF = "Inventory Staff"
FINANCE_STAFF = "Finance Staff"
SUPPORT_STAFF = "Support Staff"


STORE_ROLE_NAMES = [
    STORE_OWNER,
    STORE_MANAGER,
    ORDER_STAFF,
    INVENTORY_STAFF,
    FINANCE_STAFF,
    SUPPORT_STAFF,
]


ROLE_PERMISSION_MAP = {

    STORE_OWNER: [
        ("orders", "view_order"),
        ("orders", "add_order"),
        ("orders", "change_order"),
        ("orders", "delete_order"),

        ("orders", "view_orderitem"),
        ("orders", "add_orderitem"),
        ("orders", "change_orderitem"),
        ("orders", "delete_orderitem"),

        ("orders", "view_coupon"),
        ("orders", "add_coupon"),
        ("orders", "change_coupon"),
        ("orders", "delete_coupon"),

        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),
        ("products", "delete_product"),

        ("products", "view_productvariant"),
        ("products", "add_productvariant"),
        ("products", "change_productvariant"),
        ("products", "delete_productvariant"),

        ("products", "view_brand"),
        ("products", "add_brand"),
        ("products", "change_brand"),
        ("products", "delete_brand"),

        ("categories", "view_category"),
        ("categories", "add_category"),
        ("categories", "change_category"),
        ("categories", "delete_category"),

        ("inventory", "view_inventorymovement"),
        ("inventory", "add_inventorymovement"),
        ("inventory", "change_inventorymovement"),

        ("payments", "view_mpesatransaction"),
        ("payments", "change_mpesatransaction"),

        ("payments", "view_refundrequest"),
        ("payments", "change_refundrequest"),

        ("payments", "view_returnrequest"),
        ("payments", "change_returnrequest"),

        ("delivery", "view_delivery"),
        ("delivery", "add_delivery"),
        ("delivery", "change_delivery"),

        ("delivery", "view_deliveryprovider"),
        ("delivery", "add_deliveryprovider"),
        ("delivery", "change_deliveryprovider"),

        ("delivery", "view_deliveryzone"),
        ("delivery", "add_deliveryzone"),
        ("delivery", "change_deliveryzone"),

        ("crm", "view_customernote"),
        ("crm", "add_customernote"),
        ("crm", "change_customernote"),
        ("crm", "delete_customernote"),

        ("reviews", "view_review"),
        ("reviews", "change_review"),
        ("reviews", "delete_review"),

        ("notifications", "view_notification"),
        ("notifications", "change_notification"),

        ("core", "view_storesettings"),
        ("core", "change_storesettings"),
    ],


    STORE_MANAGER: [
        ("orders", "view_order"),
        ("orders", "change_order"),
        ("orders", "view_orderitem"),

        ("orders", "view_coupon"),
        ("orders", "add_coupon"),
        ("orders", "change_coupon"),

        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),

        ("products", "view_productvariant"),
        ("products", "add_productvariant"),
        ("products", "change_productvariant"),

        ("products", "view_brand"),
        ("products", "add_brand"),
        ("products", "change_brand"),

        ("categories", "view_category"),
        ("categories", "add_category"),
        ("categories", "change_category"),

        ("inventory", "view_inventorymovement"),
        ("inventory", "add_inventorymovement"),
        ("inventory", "change_inventorymovement"),

        ("delivery", "view_delivery"),
        ("delivery", "add_delivery"),
        ("delivery", "change_delivery"),

        ("delivery", "view_deliveryprovider"),
        ("delivery", "change_deliveryprovider"),

        ("delivery", "view_deliveryzone"),
        ("delivery", "change_deliveryzone"),

        ("payments", "view_mpesatransaction"),
        ("payments", "view_refundrequest"),
        ("payments", "view_returnrequest"),

        ("crm", "view_customernote"),
        ("crm", "add_customernote"),
        ("crm", "change_customernote"),

        ("reviews", "view_review"),
        ("reviews", "change_review"),

        ("notifications", "view_notification"),
        ("notifications", "change_notification"),
    ],


    ORDER_STAFF: [
        ("orders", "view_order"),
        ("orders", "change_order"),
        ("orders", "view_orderitem"),

        ("delivery", "view_delivery"),
        ("delivery", "add_delivery"),
        ("delivery", "change_delivery"),
    ],


    INVENTORY_STAFF: [
        ("products", "view_product"),
        ("products", "add_product"),
        ("products", "change_product"),

        ("products", "view_productvariant"),
        ("products", "add_productvariant"),
        ("products", "change_productvariant"),

        ("products", "view_brand"),

        ("categories", "view_category"),

        ("inventory", "view_inventorymovement"),
        ("inventory", "add_inventorymovement"),
        ("inventory", "change_inventorymovement"),
    ],


    FINANCE_STAFF: [
        ("orders", "view_order"),
        ("orders", "view_orderitem"),

        ("payments", "view_mpesatransaction"),
        ("payments", "change_mpesatransaction"),

        ("payments", "view_refundrequest"),
        ("payments", "change_refundrequest"),

        ("payments", "view_returnrequest"),
        ("payments", "change_returnrequest"),
    ],


    SUPPORT_STAFF: [
        ("orders", "view_order"),
        ("orders", "view_orderitem"),

        ("crm", "view_customernote"),
        ("crm", "add_customernote"),
        ("crm", "change_customernote"),

        ("reviews", "view_review"),
        ("reviews", "change_review"),

        ("notifications", "view_notification"),
        ("notifications", "change_notification"),
    ],
}

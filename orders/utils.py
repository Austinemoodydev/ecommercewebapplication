import uuid


def generate_order_number():
    return "ORD-" + uuid.uuid4().hex[:10].upper()

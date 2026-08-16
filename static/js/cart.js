function csrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
}

function updateCartUI(data) {
    const counter = document.getElementById("cart-count");
    if (counter) counter.textContent = data.count;

    const totalEl = document.getElementById("cart-total");
    if (totalEl) totalEl.textContent = data.total;

    if (data.item_id) {
        const qtyEl = document.getElementById(`qty-${data.item_id}`);
        const subEl = document.getElementById(`subtotal-${data.item_id}`);
        if (qtyEl) qtyEl.textContent = data.quantity;
        if (subEl) subEl.textContent = data.subtotal;
    }
}

function removeRow(itemId) {
    const row = document.getElementById(`cart-row-${itemId}`);
    if (row) row.remove();

    const table = document.getElementById("cart-table");
    const tbody = table ? table.querySelector("tbody") : null;
    if (tbody && tbody.children.length === 0) {
        const emptyRow = document.createElement("tr");
        emptyRow.innerHTML = `<td colspan="5">Your cart is empty.</td>`;
        tbody.appendChild(emptyRow);
    }
}

document.addEventListener("click", function (e) {

    if (e.target.matches(".qty-btn")) {

        const itemId = e.target.dataset.item;
        const action = e.target.dataset.action;

        fetch(`/cart/${action}/${itemId}/`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            if (data.quantity === undefined) {
                removeRow(itemId);
            }
            updateCartUI(data);
        });
    }

    if (e.target.matches(".remove-btn")) {

        const itemId = e.target.dataset.item;

        fetch(`/cart/remove/${itemId}/`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            removeRow(itemId);
            updateCartUI(data);
        });
    }

    if (e.target.matches(".add-to-cart-btn")) {

        const productId = e.target.dataset.product;

        fetch(`/cart/add/${productId}/`, {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            updateCartUI(data);
            e.target.textContent = "Added!";
            setTimeout(() => { e.target.textContent = "Add to Cart"; }, 1200);
        });
    }

});


document.addEventListener("DOMContentLoaded", function () {

    const toggle = document.getElementById("mini-cart-toggle");

    if (toggle) {
        toggle.addEventListener("click", function () {

            fetch("/cart/mini/", {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
            .then(res => res.json())
            .then(data => {

                const container = document.getElementById("mini-cart-items");
                const totalEl = document.getElementById("mini-cart-total");

                if (data.items.length === 0) {
                    container.innerHTML = `<p class="text-muted mb-0">Your cart is empty.</p>`;
                } else {
                    container.innerHTML = data.items.map(item => `
                        <div class="d-flex justify-content-between mb-1">
                            <span>${item.name} x${item.quantity}</span>
                            <span>KES ${item.subtotal}</span>
                        </div>
                    `).join("");
                }

                if (totalEl) totalEl.textContent = data.total;
            });
        });
    }

});

document.querySelectorAll(".wishlist-btn").forEach(button => {

    button.addEventListener("click", function () {

        const productId = this.dataset.product;

        fetch(`/wishlist/toggle/${productId}/`, {

            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }

        })

            .then(response => response.json())

            .then(data => {

                const icon = this.querySelector("i");

                if (data.added) {

                    icon.classList.remove("bi-heart");
                    icon.classList.add("bi-heart-fill");

                } else {

                    icon.classList.remove("bi-heart-fill");
                    icon.classList.add("bi-heart");

                }

                const counter = document.getElementById("wishlist-count");
                if (counter) {
                    counter.textContent = data.count;
                }

            });

    });

});
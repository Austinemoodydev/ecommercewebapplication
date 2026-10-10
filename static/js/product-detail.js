document.addEventListener("DOMContentLoaded", () => {
  const select = document.getElementById("variant-select");
  if (!select) return;
  const image = document.getElementById("product-main-image");
  const price = document.getElementById("product-live-price");
  const stock = document.getElementById("variant-stock-message");
  const addButton = document.querySelector(".add-to-cart-btn[data-variant-select]");
  const swatches = document.querySelectorAll(".variant-swatch");
  const optionSelects = [...document.querySelectorAll(".product-option-select")];
  const variantOptions = [...select.options].filter(option => option.value);

  function updateVariant() {
    const option = select.options[select.selectedIndex];
    const selected = Boolean(option?.value);
    const available = selected && Number(option.dataset.stock) > 0;
    if (selected) {
      image.src = option.dataset.image;
      image.alt = `${option.dataset.name}${option.dataset.colour ? ` - ${option.dataset.colour}` : ""}`;
      price.textContent = option.dataset.priceDisplay;
      stock.textContent = available ? `${option.dataset.stock} available` : "Out of stock";
      stock.classList.toggle("text-danger", !available);
    } else {
      stock.textContent = "Select an option to see availability.";
      stock.classList.remove("text-danger");
    }
    addButton.disabled = !available;
    swatches.forEach(swatch => swatch.classList.toggle("is-selected", swatch.dataset.variantId === select.value));
  }

  function updateStructuredOptions() {
    const selected = optionSelects.map(item => item.value).filter(Boolean);
    optionSelects.forEach(optionSelect => {
      [...optionSelect.options].forEach(valueOption => {
        if (!valueOption.value) return;
        const others = optionSelects.filter(item => item !== optionSelect && item.value).map(item => item.value);
        valueOption.disabled = !variantOptions.some(variant => {
          const values = variant.dataset.values.split(",");
          return Number(variant.dataset.stock) > 0 && values.includes(valueOption.value) && others.every(value => values.includes(value));
        });
      });
    });
    const match = selected.length === optionSelects.length
      ? variantOptions.find(variant => {
          const values = variant.dataset.values.split(",");
          return selected.length === values.length && selected.every(value => values.includes(value));
        })
      : null;
    select.value = match?.value || "";
    updateVariant();
    if (!match && selected.length === optionSelects.length) {
      stock.textContent = "This combination is not available.";
      stock.classList.add("text-danger");
    }
  }

  select.addEventListener("change", updateVariant);
  swatches.forEach(swatch => swatch.addEventListener("click", () => {
    select.value = swatch.dataset.variantId;
    updateVariant();
  }));
  optionSelects.forEach((optionSelect, index) => optionSelect.addEventListener("change", () => {
    optionSelects.slice(index + 1).forEach(laterSelect => { laterSelect.value = ""; });
    updateStructuredOptions();
  }));
  updateVariant();
});

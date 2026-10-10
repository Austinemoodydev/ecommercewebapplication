document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-filter-group]").forEach((group) => {
    const search = group.querySelector("[data-filter-search]");
    const options = group.querySelector("[data-filter-options]");
    const items = [...group.querySelectorAll("[data-filter-option]")];
    const empty = group.querySelector("[data-filter-empty]");
    const more = group.querySelector("[data-filter-more]");
    const visibleCount = Number(options?.dataset.visibleCount || 8);
    const render = () => {
      const query = search?.value.trim().toLowerCase() || "";
      const expanded = !options?.classList.contains("is-collapsed");
      let matches = 0;
      items.forEach((item, index) => {
        const matchesQuery = item.dataset.filterLabel.includes(query);
        const show = matchesQuery && (query || expanded || index < visibleCount || item.querySelector("input").checked);
        item.hidden = !show;
        if (matchesQuery) matches += 1;
      });
      if (empty) empty.hidden = matches !== 0;
      if (more) more.hidden = Boolean(query);
    };
    search?.addEventListener("input", render);
    more?.addEventListener("click", () => {
      options.classList.toggle("is-collapsed");
      const collapsed = options.classList.contains("is-collapsed");
      more.textContent = collapsed ? more.dataset.moreLabel : more.dataset.lessLabel;
      more.setAttribute("aria-expanded", String(!collapsed));
      render();
    });
    render();
  });
  document.querySelectorAll("[data-auto-submit]").forEach((control) => control.addEventListener("change", () => control.form.submit()));
});

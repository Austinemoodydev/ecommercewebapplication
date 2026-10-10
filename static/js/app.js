document.addEventListener("DOMContentLoaded", () => {
    const navigation = document.getElementById("storefrontNav");
    const toggle = document.querySelector("[data-bs-target='#storefrontNav']");

    if (!navigation || !toggle) return;

    navigation.addEventListener("show.bs.collapse", () => {
        toggle.setAttribute("aria-label", "Close navigation");
        toggle.classList.add("is-open");
    });

    navigation.addEventListener("hide.bs.collapse", () => {
        toggle.setAttribute("aria-label", "Open navigation");
        toggle.classList.remove("is-open");
    });
});

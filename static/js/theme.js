(function () {
    "use strict";

    const storageKey = "store-theme";
    const root = document.documentElement;

    function preferredTheme() {
        let saved = null;
        try {
            saved = localStorage.getItem(storageKey);
        } catch (error) {
            // The browser can disable storage in private or restricted contexts.
        }
        if (saved === "light" || saved === "dark") return saved;
        return window.matchMedia?.("(prefers-color-scheme: dark)").matches
            ? "dark"
            : "light";
    }

    function applyTheme(theme) {
        const resolved = theme === "dark" ? "dark" : "light";
        root.dataset.theme = resolved;
        root.style.colorScheme = resolved;

        document.querySelectorAll("[data-theme-toggle]").forEach(button => {
            const dark = resolved === "dark";
            button.setAttribute("aria-label", dark ? "Use light theme" : "Use dark theme");
            button.setAttribute("title", dark ? "Use light theme" : "Use dark theme");
            button.setAttribute("aria-pressed", String(dark));

            const icon = button.querySelector("i");
            if (icon) {
                icon.className = dark ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
            }
        });
    }

    applyTheme(preferredTheme());

    document.addEventListener("DOMContentLoaded", () => {
        applyTheme(root.dataset.theme);

        document.querySelectorAll("[data-theme-toggle]").forEach(button => {
            button.addEventListener("click", () => {
                const next = root.dataset.theme === "dark" ? "light" : "dark";
                try {
                    localStorage.setItem(storageKey, next);
                } catch (error) {
                    // Apply the selection for this page even when storage is unavailable.
                }
                applyTheme(next);
            });
        });
    });
})();

document.addEventListener("DOMContentLoaded", () => {
  const element = document.getElementById("homeHeroCarousel");
  const toggle = element?.querySelector(".home-hero-playback");
  if (!element || !toggle || typeof bootstrap === "undefined") return;
  const carousel = bootstrap.Carousel.getOrCreateInstance(element);
  const icon = toggle.querySelector("i");
  let paused = false;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    carousel.pause(); paused = true; toggle.setAttribute("aria-pressed","true");
    toggle.setAttribute("aria-label","Play rotating promotions"); icon.className="bi bi-play-fill";
  }
  toggle.addEventListener("click", () => {
    paused = !paused; if (paused) carousel.pause(); else carousel.cycle();
    toggle.setAttribute("aria-pressed",String(paused));
    toggle.setAttribute("aria-label",paused ? "Play rotating promotions" : "Pause rotating promotions");
    icon.className = paused ? "bi bi-play-fill" : "bi bi-pause-fill";
  });
});

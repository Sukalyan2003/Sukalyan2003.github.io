const navToggle = document.querySelector(".navbar-toggler");
const navMenu = document.getElementById("navbarSupportedContent");
const navbar = document.querySelector(".navbar.fixed-top");

if (navToggle && navMenu) {
  navToggle.addEventListener("click", () => {
    const isOpen = navMenu.classList.toggle("show");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  navMenu.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      navMenu.classList.remove("show");
      navToggle.setAttribute("aria-expanded", "false");
    }
  });
}

// Keep body offset and anchor scroll-padding in sync with the real navbar
// height, so section headings never land underneath the fixed bar.
if (navbar) {
  const syncNavHeight = () => {
    const collapsed = navMenu && navMenu.classList.contains("show");
    // Measure the bar itself, not the expanded mobile menu.
    const height = collapsed
      ? navbar.offsetHeight - navMenu.offsetHeight
      : navbar.offsetHeight;
    document.documentElement.style.setProperty("--nav-h", `${Math.round(height)}px`);
  };

  syncNavHeight();
  window.addEventListener("resize", syncNavHeight, { passive: true });
  window.addEventListener("load", syncNavHeight);
}

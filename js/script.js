const navToggle = document.querySelector(".navbar-toggler");
const navMenu = document.getElementById("navbarSupportedContent");

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

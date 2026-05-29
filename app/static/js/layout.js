(function () {
  const root = document.documentElement;

  function renderIcons() {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  function setCollapsed(collapsed) {
    root.classList.toggle("sidebar-collapsed", collapsed);
    root.classList.remove("sidebar-open");

    try {
      localStorage.setItem("medextract.sidebar", collapsed ? "collapsed" : "expanded");
    } catch (error) {
      // Local storage can be unavailable in some browser modes.
    }

    syncControls();
  }

  function setMobileOpen(open) {
    root.classList.toggle("sidebar-open", open);
    syncControls();
  }

  function syncControls() {
    const collapsed = root.classList.contains("sidebar-collapsed");
    const mobileOpen = root.classList.contains("sidebar-open");

    document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
      const icon = button.querySelector("[data-lucide]");
      button.setAttribute("aria-expanded", String(!collapsed));
      button.setAttribute("aria-label", collapsed ? "Mostrar menu" : "Ocultar menu");
      button.title = collapsed ? "Mostrar menu" : "Ocultar menu";
      if (icon) {
        icon.setAttribute("data-lucide", collapsed ? "panel-left-open" : "panel-left-close");
      }
    });

    document.querySelectorAll("[data-mobile-sidebar-toggle]").forEach((button) => {
      const icon = button.querySelector("[data-lucide]");
      button.setAttribute("aria-expanded", String(mobileOpen));
      button.setAttribute("aria-label", mobileOpen ? "Fechar menu" : "Abrir menu");
      button.title = mobileOpen ? "Fechar menu" : "Abrir menu";
      if (icon) {
        icon.setAttribute("data-lucide", mobileOpen ? "x" : "menu");
      }
    });

    renderIcons();
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        setCollapsed(!root.classList.contains("sidebar-collapsed"));
      });
    });

    document.querySelectorAll("[data-mobile-sidebar-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        setMobileOpen(!root.classList.contains("sidebar-open"));
      });
    });

    const backdrop = document.querySelector("[data-sidebar-backdrop]");
    if (backdrop) {
      backdrop.addEventListener("click", () => setMobileOpen(false));
    }

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    });

    window.addEventListener("resize", () => {
      if (window.matchMedia("(min-width: 721px)").matches) {
        setMobileOpen(false);
      }
    });

    syncControls();
  });
})();

/*==================================================
    HUMEN SOLUTIONS
    script.js
==================================================*/

document.addEventListener("DOMContentLoaded", () => {

    /*==========================================
      ELEMENTOS
    ==========================================*/

    const header = document.querySelector("#header");
    const menu = document.querySelector(".menu");
    const menuButton = document.querySelector(".menu-mobile");
    const menuLinks = document.querySelectorAll(".menu a");

    const faqItems = document.querySelectorAll(".faq-item");

    const sections = document.querySelectorAll("main section");

    const fadeElements = document.querySelectorAll(".fade-up");

    const year = document.querySelector("#year");



    /*==========================================
      MENÚ MÓVIL
    ==========================================*/

    if (menuButton && menu) {

        menuButton.addEventListener("click", () => {

            menu.classList.toggle("active");
            menuButton.classList.toggle("active");

        });

        menuLinks.forEach(link => {

            link.addEventListener("click", () => {

                menu.classList.remove("active");
                menuButton.classList.remove("active");

            });

        });

    }



    /*==========================================
      HEADER AL HACER SCROLL
    ==========================================*/

    window.addEventListener("scroll", () => {

        if (window.scrollY > 80) {

            header.classList.add("scrolled");

        } else {

            header.classList.remove("scrolled");

        }

    });



    /*==========================================
      SCROLL SUAVE
    ==========================================*/

    menuLinks.forEach(link => {

        link.addEventListener("click", function (e) {

            const href = this.getAttribute("href");

            if (!href.startsWith("#")) return;

            e.preventDefault();

            const section = document.querySelector(href);

            if (!section) return;

            window.scrollTo({

                top: section.offsetTop - 80,
                behavior: "smooth"

            });

        });

    });



    /*==========================================
      FAQ
    ==========================================*/

    faqItems.forEach(item => {

        const question = item.querySelector(".faq-question");

        question.addEventListener("click", () => {

            faqItems.forEach(faq => {

                if (faq !== item) {

                    faq.classList.remove("active");

                }

            });

            item.classList.toggle("active");

        });

    });



    /*==========================================
      ANIMACIONES
    ==========================================*/

    if ("IntersectionObserver" in window) {

        const observer = new IntersectionObserver((entries) => {

            entries.forEach(entry => {

                if (entry.isIntersecting) {

                    entry.target.classList.add("active");

                }

            });

        }, {

            threshold: 0.15

        });

        fadeElements.forEach(element => {

            observer.observe(element);

        });

    }



    /*==========================================
      BOTÓN VOLVER ARRIBA
    ==========================================*/

    const backTop = document.createElement("button");

    backTop.className = "back-top";

    backTop.innerHTML = "↑";

    backTop.setAttribute("aria-label", "Volver arriba");

    document.body.appendChild(backTop);

    window.addEventListener("scroll", () => {

        if (window.scrollY > 400) {

            backTop.classList.add("show");

        } else {

            backTop.classList.remove("show");

        }

    });

    backTop.addEventListener("click", () => {

        window.scrollTo({

            top: 0,
            behavior: "smooth"

        });

    });



    /*==========================================
      MENÚ ACTIVO
    ==========================================*/

    window.addEventListener("scroll", () => {

        let current = "";

        sections.forEach(section => {

            const top = section.offsetTop - 120;

            const height = section.offsetHeight;

            if (window.scrollY >= top && window.scrollY < top + height) {

                current = section.getAttribute("id");

            }

        });

        menuLinks.forEach(link => {

            link.classList.remove("active");

            if (link.getAttribute("href") === "#" + current) {

                link.classList.add("active");

            }

        });

    });



    /*==========================================
      AÑO AUTOMÁTICO
    ==========================================*/

    if (year) {

        year.textContent = new Date().getFullYear();

    }

});
/*==================================================
MODAL: SISTEMA PROPIO (ERP HUMEN)
==================================================*/

document.addEventListener("DOMContentLoaded", () => {

    const overlay = document.getElementById("erpModalOverlay");
    const openBtn = document.getElementById("btnVerERP");
    const closeBtn = document.getElementById("erpModalClose");
    const prevBtn = document.getElementById("erpPrev");
    const nextBtn = document.getElementById("erpNext");
    const dotsWrap = document.getElementById("erpDots");
    const slidesWrap = document.getElementById("erpModalSlides");

    if (!overlay || !openBtn || !slidesWrap) return;

    const slides = Array.from(slidesWrap.querySelectorAll(".erp-slide"));
    let current = 0;

    // Generar los puntos indicadores
    slides.forEach((_, i) => {
        const dot = document.createElement("button");
        dot.type = "button";
        dot.className = "erp-dot";
        dot.setAttribute("aria-label", "Ir a la diapositiva " + (i + 1));
        dot.addEventListener("click", () => goTo(i));
        dotsWrap.appendChild(dot);
    });

    const dots = Array.from(dotsWrap.querySelectorAll(".erp-dot"));

    function render() {
        slides.forEach((s, i) => s.classList.toggle("active", i === current));
        dots.forEach((d, i) => d.classList.toggle("active", i === current));
        prevBtn.disabled = current === 0;
        prevBtn.style.opacity = current === 0 ? ".35" : "1";
        nextBtn.style.visibility = current === slides.length - 1 ? "hidden" : "visible";
    }

    function goTo(index) {
        current = Math.max(0, Math.min(slides.length - 1, index));
        render();
    }

    function open() {
        current = 0;
        render();
        overlay.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function close() {
        overlay.classList.remove("active");
        document.body.style.overflow = "";
    }

    openBtn.addEventListener("click", open);
    closeBtn.addEventListener("click", close);
    prevBtn.addEventListener("click", () => goTo(current - 1));
    nextBtn.addEventListener("click", () => goTo(current + 1));

    overlay.querySelectorAll("[data-erp-close]").forEach(btn => {
        btn.addEventListener("click", close);
    });

    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) close();
    });

    document.addEventListener("keydown", (e) => {
        if (!overlay.classList.contains("active")) return;
        if (e.key === "Escape") close();
        if (e.key === "ArrowRight") goTo(current + 1);
        if (e.key === "ArrowLeft") goTo(current - 1);
    });

});


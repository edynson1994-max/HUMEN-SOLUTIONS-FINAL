/*==================================================
    HUMEN SOLUTIONS S.A.C.S.
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
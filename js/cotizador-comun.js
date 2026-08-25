/*==================================================
    HUMEN SOLUTIONS — cotizador-comun.js

    Motor compartido de cotizador + pago, usado por las 3 sub-páginas de
    servicio (contabilidad/, inventarios/, humen-clean/). Antes esta
    lógica vivía embebida una sola vez en el cotizador de la página
    principal (js/script.js); ahora cada servicio tiene su propia página
    y su propio cotizador, así que este archivo evita triplicar el
    código de: generar el código de cotización, mostrar el resultado con
    su animación, y el flujo completo de pago con Mercado Pago
    (exactamente el mismo backend/Codigo.gs de siempre — no requiere un
    nuevo despliegue).

    Cada página solo tiene que:
      1. Incluir este script + tener en el HTML el modal de pago con los
         mismos ids que ya usaba el cotizador original (ver humen-clean/
         index.html, contabilidad/index.html o inventarios/index.html
         como referencia).
      2. Llamar a HumenCotizador.init({...}) con la configuración de su
         propio servicio (nombre, umbral de revisión manual, si aplica
         el descuento por pago inmediato, y las funciones que exponen el
         precio/código/detalle actuales de SU propio cálculo).
==================================================*/

(function (global) {

    // Mismo backend de siempre (Google Apps Script + Mercado Pago) — es
    // genérico, no le importa qué servicio le llega, así que las 3
    // páginas nuevas lo reutilizan sin necesidad de un nuevo despliegue.
    var MP_BACKEND_URL = "https://script.google.com/macros/s/AKfycbyeKli4LZB3w7lPRfKjTBx97FwLpLy93l66RF9hsPWpgJAqsAYAmuMDqblbfZdr-p-s1g/exec";

    function formatoMoneda(n) {
        return "S/ " + Number(n).toLocaleString("es-PE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function generarCodigo() {
        var ahora = new Date();
        var fecha =
            ahora.getFullYear().toString() +
            String(ahora.getMonth() + 1).padStart(2, "0") +
            String(ahora.getDate()).padStart(2, "0");
        var aleatorio = Math.random().toString(36).substring(2, 6).toUpperCase();
        return "HUM-" + fecha + "-" + aleatorio;
    }

    function whatsappLink(numero, texto) {
        return "https://wa.me/" + numero + "?text=" + encodeURIComponent(texto);
    }

    // Número de WhatsApp del negocio — el mismo que ya se usa en la
    // tarjeta de contacto de la página principal.
    var WHATSAPP_NEGOCIO = "51952242779";

    // Estado de la cotización actual en esta página (una sola por
    // página, a diferencia del cotizador original que tenía 3 tabs).
    var estado = { precio: null, codigo: null, parametros: null };

    /**
     * mostrarResultado(precio, detalleHtml, opts) — pinta el resultado en
     * el panel ".cotizador-resultado" (mismo markup/clases que usaba el
     * cotizador original) y deja todo listo para pagar o pedir por
     * WhatsApp.
     *
     * opts = {
     *   parametros: object,               (se guarda para mandarlo al backend si paga)
     *   umbralRevisionManual: number|null,
     *   descuentoPagoRapido: number,       (0 = sin descuento por pago inmediato)
     *   whatsappTexto: (codigo, precio) => string
     * }
     */
    function mostrarResultado(precio, detalleHtml, opts) {

        opts = opts || {};

        var codigo = generarCodigo();
        estado.precio = precio;
        estado.codigo = codigo;
        estado.parametros = opts.parametros || null;

        var resultadoEl = document.querySelector(".cotizador-resultado h2");
        var detalleEl = document.getElementById("detalleCotizacion");

        if (resultadoEl) {
            var fecha = new Date().toLocaleString("es-PE");
            resultadoEl.innerHTML =
                formatoMoneda(precio) +
                '<div class="codigo-cotizacion" id="codigoCotizacion">' + codigo + '</div>' +
                '<div class="fecha-cotizacion">' + fecha + '</div>';
        }

        if (detalleEl) {
            detalleEl.innerHTML = detalleHtml;
            detalleEl.classList.remove("cotizacion-animada");
            void detalleEl.offsetWidth;
            detalleEl.classList.add("cotizacion-animada");
        }

        var btnPagarAhora = document.getElementById("btnPagarAhora");
        var notaRevision = document.getElementById("notaRevisionManual");
        var notaPagoSeguro = document.getElementById("notaPagoSeguro");
        var descuentoBox = document.getElementById("descuentoPagoRapido");
        var descuentoPrecioFinal = document.getElementById("descuentoPrecioFinal");
        var descuentoPrecioOriginal = document.getElementById("descuentoPrecioOriginal");

        var umbral = opts.umbralRevisionManual;
        var necesitaRevision = umbral ? precio > umbral : false;
        var descuento = opts.descuentoPagoRapido || 0;

        if (btnPagarAhora) {
            btnPagarAhora.style.display = necesitaRevision ? "none" : "";
            if (notaRevision) notaRevision.style.display = necesitaRevision ? "" : "none";
            if (notaPagoSeguro) notaPagoSeguro.style.display = necesitaRevision ? "none" : "";
            if (descuentoBox) {
                if (descuento > 0 && !necesitaRevision) {
                    descuentoBox.style.display = "flex";
                    var precioConDescuento = Math.round(precio * (1 - descuento) * 100) / 100;
                    if (descuentoPrecioFinal) descuentoPrecioFinal.textContent = formatoMoneda(precioConDescuento);
                    if (descuentoPrecioOriginal) descuentoPrecioOriginal.textContent = formatoMoneda(precio);
                } else {
                    descuentoBox.style.display = "none";
                }
            }
        }

        var btnWA = document.getElementById("btnSolicitarCotizacion");
        if (btnWA && opts.whatsappTexto) {
            btnWA.href = whatsappLink(WHATSAPP_NEGOCIO, opts.whatsappTexto(codigo, precio));
        }
    }

    /**
     * config = {
     *   servicioNombre: "Limpieza de Oficinas — HUMEN Clean",
     *   servicioClave: "limpieza",
     *   umbralRevisionManual: 1500 | null   (null = nunca requiere revisión manual)
     *   descuentoPagoRapido: 0.10 | 0       (0 = no se ofrece descuento por pagar ahora)
     *   obtenerPrecio: () => number | null,
     *   obtenerCodigo: () => string,
     *   obtenerParametros: () => object,
     *   obtenerDetalleTexto: () => string,
     *   botonesPagoAdicionales: [            (opcional — otros botones que abren
     *     {                                   el mismo modal de pago pero cobran
     *       id: "btnPagarGlobal",             un monto distinto al de
     *       obtenerPrecio: () => number,      "btnPagarAhora". Pensado para el
     *       obtenerParametros: () => object,  caso de HUMEN Clean: pagar UNA
     *       obtenerDetalleTexto: () => string,visita, o pagar un plan completo
     *       etiquetaResumen: () => string,    por adelantado. El botón normal
     *       umbralRevisionManual: number      (btnPagarAhora) sigue funcionando
     *     }                                   igual si no se usa esto. umbralRevisionManual
     *   ]                                     es opcional — si no se pasa, usa el de config.
     * }
     */
    function init(config) {

        config = config || {};
        if (!config.obtenerPrecio) config.obtenerPrecio = function () { return estado.precio; };
        if (!config.obtenerCodigo) config.obtenerCodigo = function () { return estado.codigo; };
        if (!config.obtenerParametros) config.obtenerParametros = function () { return estado.parametros; };
        if (!config.obtenerDetalleTexto) config.obtenerDetalleTexto = function () {
            var el = document.getElementById("detalleCotizacion");
            return el ? el.innerText : "";
        };

        // El botón de WhatsApp vive dentro del panel de resultado, visible
        // desde que se carga la página — pero su href solo se llenaba
        // dentro de mostrarResultado(), después de calcular. Si el
        // cliente lo tocaba ANTES de calcular, el href seguía siendo "#"
        // y no pasaba nada (no abría ningún chat). Se le da un link real
        // desde el inicio, con un mensaje genérico, para que el botón
        // siempre funcione — mostrarResultado() lo reemplaza por el
        // mensaje con el detalle en cuanto el cliente calcula.
        var btnWAInicial = document.getElementById("btnSolicitarCotizacion");
        if (btnWAInicial) {
            var hrefActual = btnWAInicial.getAttribute("href");
            if (!hrefActual || hrefActual === "#") {
                btnWAInicial.href = whatsappLink(
                    WHATSAPP_NEGOCIO,
                    "Hola, quisiera solicitar una cotización del servicio de " + (config.servicioNombre || "Humen Solutions") + "."
                );
            }
        }

        var btnPagar = document.getElementById("btnPagarAhora");
        var overlay = document.getElementById("pagoModalOverlay");
        var closeBtn = document.getElementById("pagoModalClose");
        var form = document.getElementById("formPago");
        var resumen = document.getElementById("pagoResumen");
        var errorBox = document.getElementById("pagoError");
        var btnConfirmar = document.getElementById("btnConfirmarPago");
        var camposFactura = document.getElementById("camposFactura");
        var camposBoleta = document.getElementById("camposBoleta");
        var radiosComprobante = document.querySelectorAll('input[name="tipoComprobante"]');

        if (!btnPagar || !overlay || !form) return;

        var descuento = config.descuentoPagoRapido || 0;

        // Qué botón de pago abrió el modal en este momento — por defecto el
        // normal (btnPagarAhora / config.*), o el descriptor de un botón
        // adicional si el cliente eligió otra forma de pago (ej. "pagar el
        // plan completo"). El formulario, al enviarse, cobra lo que diga
        // este descriptor, no siempre config.obtenerPrecio().
        var pagoActivo = null;

        window.addEventListener("pageshow", function (event) {
            if (event.persisted) {
                btnConfirmar.disabled = false;
                btnConfirmar.textContent = "Continuar a Mercado Pago";
            }
        });

        function requiereRevisionManual(precio, umbralOverride) {
            var umbral = (umbralOverride !== undefined && umbralOverride !== null)
                ? umbralOverride
                : config.umbralRevisionManual;
            return umbral ? precio > umbral : false;
        }

        function tipoComprobanteActual() {
            var seleccionado = document.querySelector('input[name="tipoComprobante"]:checked');
            return seleccionado ? seleccionado.value : "boleta";
        }

        function actualizarCamposComprobante() {
            var esFactura = tipoComprobanteActual() === "factura";
            camposFactura.hidden = !esFactura;
            camposBoleta.hidden = esFactura;
            document.getElementById("pagoRazonSocial").required = esFactura;
            document.getElementById("pagoRuc").required = esFactura;
        }

        radiosComprobante.forEach(function (r) {
            r.addEventListener("change", actualizarCamposComprobante);
        });

        function abrir(descriptor) {

            descriptor = descriptor || {};

            var obtenerPrecio = descriptor.obtenerPrecio || config.obtenerPrecio;
            var obtenerParametros = descriptor.obtenerParametros || config.obtenerParametros;
            var obtenerDetalleTexto = descriptor.obtenerDetalleTexto || config.obtenerDetalleTexto;
            var servicioNombre = descriptor.servicioNombre || config.servicioNombre;
            var etiquetaResumen = typeof descriptor.etiquetaResumen === "function"
                ? descriptor.etiquetaResumen()
                : (descriptor.etiquetaResumen || "");

            var precio = obtenerPrecio();

            if (!precio || precio <= 0) {
                alert("Primero completa los datos de tu cotización para calcular un precio.");
                return;
            }

            if (requiereRevisionManual(precio, descriptor.umbralRevisionManual)) {
                alert("Este monto requiere una revisión manual antes de pagar. Por favor usa 'Solicitar Cotización' por WhatsApp.");
                return;
            }

            pagoActivo = {
                obtenerPrecio: obtenerPrecio,
                obtenerParametros: obtenerParametros,
                obtenerDetalleTexto: obtenerDetalleTexto,
                servicioNombre: servicioNombre
            };

            errorBox.textContent = "";
            actualizarCamposComprobante();

            var precioFinal = descuento > 0
                ? Math.round(precio * (1 - descuento) * 100) / 100
                : precio;

            resumen.innerHTML =
                "<strong>Servicio:</strong> " + servicioNombre + (etiquetaResumen ? " — " + etiquetaResumen : "") + "<br>" +
                "<strong>Código:</strong> " + config.obtenerCodigo() + "<br>" +
                "<strong>Total a pagar" + (descuento > 0 ? " (" + Math.round(descuento * 100) + "% dcto. por pago inmediato)" : "") + ":</strong> " +
                formatoMoneda(precioFinal);

            overlay.classList.add("active");
            document.body.style.overflow = "hidden";
        }

        function cerrar() {
            overlay.classList.remove("active");
            document.body.style.overflow = "";
        }

        btnPagar.addEventListener("click", function () { abrir(); });

        (config.botonesPagoAdicionales || []).forEach(function (extra) {
            var btn = document.getElementById(extra.id);
            if (!btn) return;
            btn.addEventListener("click", function () { abrir(extra); });
        });

        if (closeBtn) closeBtn.addEventListener("click", cerrar);

        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) cerrar();
        });

        document.addEventListener("keydown", function (e) {
            if (overlay.classList.contains("active") && e.key === "Escape") cerrar();
        });

        form.addEventListener("submit", function (e) {

            e.preventDefault();
            errorBox.textContent = "";

            var tipoComprobante = tipoComprobanteActual();
            var razonSocial = document.getElementById("pagoRazonSocial").value.trim();
            var ruc = document.getElementById("pagoRuc").value.trim();
            var dni = document.getElementById("pagoDni").value.trim();

            if (tipoComprobante === "factura") {
                if (!razonSocial) {
                    errorBox.textContent = "Ingresa la razón social de la empresa.";
                    return;
                }
                if (!/^\d{11}$/.test(ruc)) {
                    errorBox.textContent = "El RUC debe tener 11 dígitos.";
                    return;
                }
            } else if (dni && !/^\d{8}$/.test(dni)) {
                errorBox.textContent = "El DNI debe tener 8 dígitos.";
                return;
            }

            // Usa el descriptor del botón que abrió el modal (el normal o
            // uno adicional, ej. "pagar plan completo") — si por algo el
            // modal se abrió sin pasar por abrir() (no debería pasar, pero
            // por seguridad), cae de vuelta a los valores de config.
            var activo = pagoActivo || {
                obtenerPrecio: config.obtenerPrecio,
                obtenerParametros: config.obtenerParametros,
                obtenerDetalleTexto: config.obtenerDetalleTexto,
                servicioNombre: config.servicioNombre
            };

            var precio = activo.obtenerPrecio();
            var precioFinal = descuento > 0
                ? Math.round(precio * (1 - descuento) * 100) / 100
                : precio;

            var datos = {
                servicio: activo.servicioNombre,
                servicioClave: config.servicioClave,
                parametros: activo.obtenerParametros ? activo.obtenerParametros() : {},
                monto: precioFinal,
                montoSinDescuento: precio,
                descuentoAplicado: descuento,
                codigo: config.obtenerCodigo(),
                detalle: activo.obtenerDetalleTexto ? activo.obtenerDetalleTexto() : "",
                nombre: document.getElementById("pagoNombre").value.trim(),
                correo: document.getElementById("pagoCorreo").value.trim(),
                telefono: document.getElementById("pagoTelefono").value.trim(),
                tipoComprobante: tipoComprobante,
                razonSocial: tipoComprobante === "factura" ? razonSocial : "",
                ruc: tipoComprobante === "factura" ? ruc : "",
                dni: tipoComprobante === "boleta" ? dni : ""
            };

            btnConfirmar.disabled = true;
            btnConfirmar.textContent = "Redirigiendo...";

            var url = MP_BACKEND_URL + "?datos=" + encodeURIComponent(JSON.stringify(datos));

            // Navegación directa (no fetch): Apps Script nunca agrega el
            // encabezado de CORS necesario para leer una respuesta entre
            // dominios distintos, pero una navegación de página completa
            // no tiene esa restricción — mismo patrón que usaba el
            // cotizador original de la página principal.
            window.location.href = url;

        });
    }

    global.HumenCotizador = {
        MP_BACKEND_URL: MP_BACKEND_URL,
        WHATSAPP_NEGOCIO: WHATSAPP_NEGOCIO,
        estado: estado,
        formatoMoneda: formatoMoneda,
        generarCodigo: generarCodigo,
        whatsappLink: whatsappLink,
        mostrarResultado: mostrarResultado,
        init: init
    };

})(window);

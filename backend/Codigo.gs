/**
 * ============================================================================
 *  BACKEND DE PAGOS — HUMEN SOLUTIONS
 * ============================================================================
 *  Conecta el cotizador de la página web con Mercado Pago (Checkout Pro).
 *
 *  Flujo:
 *   1. El cliente completa el cotizador en la web y hace clic en "Pagar ahora".
 *   2. La web NAVEGA (no usa fetch) directamente a este script (doGet, con
 *      los datos en la URL) → se crea una "preferencia" de pago en Mercado
 *      Pago y se guarda el pedido como "pendiente" en una Hoja de cálculo.
 *      El script responde con una página que redirige al cliente
 *      directamente a Mercado Pago.
 *      (Se navega en vez de usar fetch específicamente porque Apps Script
 *      nunca agrega el encabezado de CORS necesario para que un navegador
 *      pueda LEER una respuesta de fetch entre distintos dominios — pero
 *      una navegación de página completa no tiene esa restricción.)
 *   3. El cliente paga en Mercado Pago.
 *   4. Mercado Pago avisa a este mismo script (doPost, vía webhook, con un
 *      JSON en el cuerpo) que el pago fue aprobado.
 *   5. El script marca el pedido como "pagado", genera el contrato / orden
 *      de servicio en PDF a partir de una plantilla de Google Docs, se lo
 *      envía por correo al cliente, y te avisa a ti para que emitas la
 *      boleta/factura por tu proceso habitual.
 *
 *  Ver GUIA-INSTALACION.md para el paso a paso de cómo configurar todo esto.
 * ============================================================================
 *  CONFIGURACIÓN (Editor de Apps Script → ⚙ Configuración del proyecto →
 *  Propiedades del script → "Agregar propiedad del script"). NUNCA escribas
 *  estos valores directamente en el código:
 *
 *    MP_ACCESS_TOKEN        Access Token de producción de Mercado Pago
 *    HOJA_PEDIDOS_ID        ID de la Google Sheet donde se registran los pedidos
 *    PLANTILLA_CONTRATO_ID  ID del Google Doc plantilla del contrato
 *    CARPETA_CONTRATOS_ID   ID de la carpeta de Drive donde guardar los PDF generados
 *    CORREO_NEGOCIO         Tu correo, para avisos de pago confirmado
 *    URL_EXITO              URL a la que Mercado Pago redirige tras un pago exitoso
 *                            (ej: https://www.humen.solutions/gracias.html)
 *    URL_SITIO               URL base de tu sitio (ej: https://www.humen.solutions)
 * ============================================================================
 */

const CABECERAS_HOJA = [
  "Fecha", "Referencia", "Código Cotización", "Servicio", "Monto",
  "Tipo Comprobante", "Nombre", "Razón Social", "RUC / DNI",
  "Correo", "Teléfono", "Detalle", "Estado", "ID Pago Mercado Pago"
];

/* ------------------------------------------------------------------ *
 *  PUNTOS DE ENTRADA
 * ------------------------------------------------------------------ */

// Llamado por la página web (fetch GET) para crear el pago.
// Se usa GET — y no POST — específicamente para evitar el bloqueo de CORS
// que Apps Script presenta con peticiones POST hechas desde otro dominio.
function doGet(e) {
  try {

    if (e.parameter.datos) {

      const datos = JSON.parse(decodeURIComponent(e.parameter.datos));
      validarDatosPedido(datos);
      const preferencia = crearPreferenciaMP(datos);

      // Redirige la página completa a Mercado Pago (no devuelve JSON).
      // Esto evita por completo el bloqueo de CORS: una navegación de
      // página nunca pasa por esa restricción, solo los fetch() la tienen.
      //
      // Apps Script envuelve su salida en un iframe interno, así que se
      // usan 3 mecanismos de respaldo para garantizar que la pestaña
      // completa navegue a Mercado Pago (no solo el iframe):
      //  1. <meta refresh> — funciona incluso si JavaScript está bloqueado
      //  2. JS con window.top — "rompe" el iframe de Apps Script
      //  3. Enlace visible — respaldo manual si los dos anteriores fallan
      return HtmlService.createHtmlOutput(
        '<!DOCTYPE html><html><head>' +
        '<meta http-equiv="refresh" content="0; url=' + preferencia.init_point + '">' +
        '</head><body style="font-family:sans-serif;text-align:center;padding:80px 20px;color:#666;">' +
        '<p>Redirigiendo a Mercado Pago…</p>' +
        '<p><a href="' + preferencia.init_point + '" target="_top" style="color:#33472A;font-weight:bold;">Haz clic aquí si no eres redirigido automáticamente</a></p>' +
        '<script>' +
        'var destino = ' + JSON.stringify(preferencia.init_point) + ';' +
        'try { window.top.location.replace(destino); } catch (e) { window.location.replace(destino); }' +
        '</script>' +
        '</body></html>'
      );
    }

    // Compatibilidad con el formato antiguo de notificación de Mercado Pago
    // (algunos reintentos o integraciones antiguas todavía usan GET con
    // parámetros en la URL en vez de POST con JSON).
    const esNotificacionPago =
      e.parameter.topic === "payment" || e.parameter.type === "payment";

    if (esNotificacionPago) {
      const paymentId = e.parameter.id || e.parameter["data.id"];
      procesarPagoConfirmado(paymentId);
    }

    return ContentService.createTextOutput("ok");

  } catch (err) {

    const props = PropertiesService.getScriptProperties();
    const urlSitio = props.getProperty("URL_SITIO") || "#";

    return HtmlService.createHtmlOutput(
      '<div style="font-family:sans-serif;max-width:480px;margin:60px auto;text-align:center;color:#333;">' +
      '<h2 style="color:#B3261E;">No pudimos iniciar tu pago</h2>' +
      '<p>' + (err.message || "Ocurrió un error inesperado.") + '</p>' +
      '<p><a href="' + urlSitio + '" style="color:#33472A;font-weight:bold;">Volver al sitio</a></p>' +
      '</div>'
    );
  }
}

// Llamado por Mercado Pago (webhook) cuando cambia el estado de un pago.
// El webhook nuevo de Mercado Pago envía un POST con un cuerpo JSON, por
// ejemplo: { type: "payment", data: { id: "123456" }, ... }
function doPost(e) {
  try {
    const cuerpo = JSON.parse(e.postData.contents);

    const esNotificacionPago =
      cuerpo.type === "payment" || cuerpo.action === "payment.updated" || cuerpo.action === "payment.created";

    if (esNotificacionPago) {
      const paymentId = cuerpo.data && cuerpo.data.id;
      if (paymentId) procesarPagoConfirmado(paymentId);
    }

  } catch (err) {
    Logger.log("Error procesando webhook: " + err.message);
  }
  return ContentService.createTextOutput("ok");
}

/* ------------------------------------------------------------------ *
 *  CREACIÓN DEL PAGO
 * ------------------------------------------------------------------ */

function validarDatosPedido(datos) {
  if (!datos.nombre || !datos.correo || !datos.telefono) {
    throw new Error("Faltan datos de contacto (nombre, correo o teléfono).");
  }
  if (!datos.monto || Number(datos.monto) <= 0) {
    throw new Error("El monto de la cotización no es válido.");
  }
  if (datos.tipoComprobante === "factura") {
    if (!datos.razonSocial) {
      throw new Error("Falta la razón social para emitir la factura.");
    }
    if (!/^\d{11}$/.test(datos.ruc || "")) {
      throw new Error("El RUC ingresado no es válido (debe tener 11 dígitos).");
    }
  }
}

function crearPreferenciaMP(datos) {
  const props = PropertiesService.getScriptProperties();
  const accessToken = props.getProperty("MP_ACCESS_TOKEN");
  const urlExito = props.getProperty("URL_EXITO") || "https://www.humen.solutions/gracias.html";
  const urlSitio = props.getProperty("URL_SITIO") || "https://www.humen.solutions";

  if (!accessToken) {
    throw new Error("Falta configurar MP_ACCESS_TOKEN en las Propiedades del script.");
  }

  const referencia = "HUM-" + new Date().getTime();

  guardarPedido(referencia, datos, "pendiente", "");

  const payerInfo = {
    name: datos.nombre,
    email: datos.correo
  };

  const numeroIdentificacion = datos.tipoComprobante === "factura" ? datos.ruc : datos.dni;

  if (numeroIdentificacion) {
    payerInfo.identification = {
      type: datos.tipoComprobante === "factura" ? "RUC" : "DNI",
      number: numeroIdentificacion
    };
  }

  const payload = {
    items: [{
      title: datos.servicio + " — HUMEN SOLUTIONS",
      quantity: 1,
      unit_price: Number(datos.monto),
      currency_id: "PEN"
    }],
    payer: payerInfo,
    external_reference: referencia,
    back_urls: {
      success: urlExito,
      failure: urlSitio,
      pending: urlSitio
    },
    auto_return: "approved",
    notification_url: ScriptApp.getService().getUrl()
  };

  const resp = UrlFetchApp.fetch("https://api.mercadopago.com/checkout/preferences", {
    method: "post",
    contentType: "application/json",
    headers: { Authorization: "Bearer " + accessToken },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  const resultado = JSON.parse(resp.getContentText());

  if (!resultado.init_point) {
    throw new Error(resultado.message || "Mercado Pago no devolvió un link de pago. Revisa tu Access Token.");
  }

  return resultado;
}

/* ------------------------------------------------------------------ *
 *  REGISTRO DE PEDIDOS (Google Sheet)
 * ------------------------------------------------------------------ */

function obtenerHoja() {
  const props = PropertiesService.getScriptProperties();
  const hojaId = props.getProperty("HOJA_PEDIDOS_ID");
  if (!hojaId) throw new Error("Falta configurar HOJA_PEDIDOS_ID en las Propiedades del script.");

  const libro = SpreadsheetApp.openById(hojaId);
  const hoja = libro.getSheets()[0];

  if (hoja.getLastRow() === 0) {
    hoja.appendRow(CABECERAS_HOJA);
  }
  return hoja;
}

function guardarPedido(referencia, datos, estado, paymentId) {
  const hoja = obtenerHoja();
  const rucODni = datos.tipoComprobante === "factura" ? datos.ruc : datos.dni;

  hoja.appendRow([
    new Date(), referencia, datos.codigo || "", datos.servicio, datos.monto,
    datos.tipoComprobante || "boleta", datos.nombre, datos.razonSocial || "",
    rucODni || "", datos.correo, datos.telefono, datos.detalle || "",
    estado, paymentId || ""
  ]);
}

function buscarFilaPorReferencia(referencia) {
  const hoja = obtenerHoja();
  const valores = hoja.getDataRange().getValues();

  for (let i = 1; i < valores.length; i++) {
    if (valores[i][1] === referencia) {
      return { fila: i + 1, datos: valores[i] };
    }
  }
  return null;
}

function marcarPedidoComoPagado(referencia, paymentId) {
  const hoja = obtenerHoja();
  const encontrado = buscarFilaPorReferencia(referencia);
  if (!encontrado) return null;

  hoja.getRange(encontrado.fila, 13).setValue("pagado");       // columna "Estado"
  hoja.getRange(encontrado.fila, 14).setValue(paymentId);      // columna "ID Pago Mercado Pago"

  return encontrado.datos;
}

/* ------------------------------------------------------------------ *
 *  CONFIRMACIÓN DE PAGO (webhook de Mercado Pago)
 * ------------------------------------------------------------------ */

function procesarPagoConfirmado(paymentId) {
  const props = PropertiesService.getScriptProperties();
  const accessToken = props.getProperty("MP_ACCESS_TOKEN");

  const resp = UrlFetchApp.fetch("https://api.mercadopago.com/v1/payments/" + paymentId, {
    headers: { Authorization: "Bearer " + accessToken },
    muteHttpExceptions: true
  });
  const pago = JSON.parse(resp.getContentText());

  if (pago.status !== "approved") return;

  const referencia = pago.external_reference;
  const encontrado = buscarFilaPorReferencia(referencia);
  if (!encontrado) return;

  const filaActual = encontrado.datos;
  const estadoActual = filaActual[12];

  // Evita procesar dos veces si Mercado Pago reintenta el mismo webhook
  if (estadoActual === "pagado") return;

  marcarPedidoComoPagado(referencia, paymentId);

  const pedido = {
    codigo: filaActual[2],
    servicio: filaActual[3],
    monto: filaActual[4],
    tipoComprobante: filaActual[5],
    nombre: filaActual[6],
    razonSocial: filaActual[7],
    rucODni: filaActual[8],
    correo: filaActual[9],
    telefono: filaActual[10],
    detalle: filaActual[11]
  };

  let contratoPdf = null;
  try {
    contratoPdf = generarContratoPDF(pedido);
  } catch (err) {
    Logger.log("No se pudo generar el contrato: " + err.message);
  }

  enviarCorreoCliente(pedido, contratoPdf);
  enviarCorreoNegocio(pedido, paymentId);
}

/* ------------------------------------------------------------------ *
 *  GENERACIÓN DEL CONTRATO / ORDEN DE SERVICIO (PDF)
 * ------------------------------------------------------------------ */

function generarContratoPDF(pedido) {
  const props = PropertiesService.getScriptProperties();
  const plantillaId = props.getProperty("PLANTILLA_CONTRATO_ID");
  const carpetaId = props.getProperty("CARPETA_CONTRATOS_ID");

  if (!plantillaId) {
    throw new Error("Falta configurar PLANTILLA_CONTRATO_ID en las Propiedades del script.");
  }

  const copia = DriveApp.getFileById(plantillaId).makeCopy(
    "Orden de servicio - " + pedido.codigo
  );

  const doc = DocumentApp.openById(copia.getId());
  const cuerpo = doc.getBody();

  const fecha = new Date().toLocaleDateString("es-PE", {
    day: "numeric", month: "long", year: "numeric"
  });

  const montoFormateado = "S/ " + Number(pedido.monto).toLocaleString("es-PE", {
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });

  cuerpo.replaceText("{{NOMBRE}}", pedido.nombre);
  cuerpo.replaceText("{{CORREO}}", pedido.correo);
  cuerpo.replaceText("{{TELEFONO}}", pedido.telefono);
  cuerpo.replaceText("{{SERVICIO}}", pedido.servicio);
  cuerpo.replaceText("{{MONTO}}", montoFormateado);
  cuerpo.replaceText("{{CODIGO}}", pedido.codigo);
  cuerpo.replaceText("{{FECHA}}", fecha);
  cuerpo.replaceText("{{DETALLE}}", pedido.detalle || "");
  cuerpo.replaceText("{{TIPO_COMPROBANTE}}", pedido.tipoComprobante === "factura" ? "Factura" : "Boleta");
  cuerpo.replaceText("{{RAZON_SOCIAL}}", pedido.razonSocial || "");
  cuerpo.replaceText("{{RUC}}", pedido.tipoComprobante === "factura" ? (pedido.rucODni || "") : "");
  cuerpo.replaceText("{{DNI}}", pedido.tipoComprobante === "boleta" ? (pedido.rucODni || "-") : "");

  doc.saveAndClose();

  const pdf = DriveApp.getFileById(copia.getId()).getAs("application/pdf");
  pdf.setName("Orden de servicio - " + pedido.codigo + ".pdf");

  if (carpetaId) {
    DriveApp.getFolderById(carpetaId).createFile(pdf);
  }

  // Borra el Google Doc temporal (ya tenemos el PDF); deja solo el PDF archivado
  DriveApp.getFileById(copia.getId()).setTrashed(true);

  return pdf;
}

/* ------------------------------------------------------------------ *
 *  NOTIFICACIONES POR CORREO
 * ------------------------------------------------------------------ */

function enviarCorreoCliente(pedido, contratoPdf) {
  const asunto = "Confirmación de pago — " + pedido.codigo + " — HUMEN SOLUTIONS";

  const cuerpo =
    "Hola " + pedido.nombre + ",\n\n" +
    "Hemos confirmado tu pago por el servicio de " + pedido.servicio + ".\n\n" +
    "Código de cotización: " + pedido.codigo + "\n" +
    "Monto pagado: S/ " + Number(pedido.monto).toLocaleString("es-PE", {minimumFractionDigits:2}) + "\n\n" +
    (contratoPdf ? "Adjuntamos tu orden de servicio.\n\n" : "") +
    "En breve nos pondremos en contacto contigo para coordinar los siguientes pasos. " +
    "Tu boleta o factura electrónica te llegará por separado.\n\n" +
    "Gracias por confiar en HUMEN SOLUTIONS.";

  const opciones = {};
  if (contratoPdf) opciones.attachments = [contratoPdf];

  MailApp.sendEmail(pedido.correo, asunto, cuerpo, opciones);
}

function enviarCorreoNegocio(pedido, paymentId) {
  const props = PropertiesService.getScriptProperties();
  const correoNegocio = props.getProperty("CORREO_NEGOCIO");
  if (!correoNegocio) return;

  const asunto = "💰 Pago recibido — " + pedido.codigo;

  const esFactura = pedido.tipoComprobante === "factura";

  const cuerpo =
    "Se confirmó un nuevo pago:\n\n" +
    "Cliente: " + pedido.nombre + "\n" +
    "Correo: " + pedido.correo + "\n" +
    "Teléfono: " + pedido.telefono + "\n" +
    "Servicio: " + pedido.servicio + "\n" +
    "Monto: S/ " + Number(pedido.monto).toLocaleString("es-PE", {minimumFractionDigits:2}) + "\n" +
    "ID de pago Mercado Pago: " + paymentId + "\n\n" +
    "Comprobante a emitir: " + (esFactura ? "FACTURA" : "BOLETA") + "\n" +
    (esFactura
      ? "Razón social: " + (pedido.razonSocial || "-") + "\nRUC: " + (pedido.rucODni || "-") + "\n"
      : "DNI: " + (pedido.rucODni || "no proporcionado") + "\n") +
    "\nRecuerda emitir el comprobante correspondiente por tu proceso habitual.";

  MailApp.sendEmail(correoNegocio, asunto, cuerpo);
}

/* ------------------------------------------------------------------ *
 *  PRUEBA MANUAL (opcional) — ejecuta esta función desde el editor
 *  de Apps Script para revisar que la configuración esté correcta,
 *  sin necesidad de hacer un pago real.
 * ------------------------------------------------------------------ */

function probarConfiguracion() {
  const datosPrueba = {
    servicio: "Reclutamiento y Selección de Personal",
    monto: 10,
    codigo: "HUM-PRUEBA-0001",
    detalle: "Prueba de configuración",
    nombre: "Cliente de Prueba",
    correo: Session.getActiveUser().getEmail(),
    telefono: "+51 999 999 999",
    tipoComprobante: "boleta",
    dni: "12345678"
  };

  const preferencia = crearPreferenciaMP(datosPrueba);
  Logger.log("Link de pago de prueba: " + preferencia.init_point);
}

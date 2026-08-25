# Guía de instalación — Pago con Mercado Pago

Esta guía te lleva paso a paso para activar el botón "Pagar ahora" de tu
cotizador. No necesitas saber programar — solo ir marcando cada paso.

En total son 6 pasos. Calcula unos 30-40 minutos la primera vez.

---

## Paso 1 — Crear tu cuenta de Mercado Pago para negocios

1. Entra a https://www.mercadopago.com.pe y crea una cuenta (o usa la que ya tengas).
2. Ve a **Tu negocio → Credenciales** (o busca "credenciales" en el
   buscador del panel).
3. Si es la primera vez, verás **"No hay aplicaciones creadas"**. Esto es
   normal — Mercado Pago pide crear una "aplicación" antes de darte
   credenciales, aunque no vayas a programar nada especial. Clic en
   **"Crear aplicación"**.
   - Nombre: pon algo simple, por ejemplo `Sitio web HUMEN SOLUTIONS`.
   - Cuando te pregunte qué vas a integrar / qué producto usarás, elige
     **"Checkout Pro"** (es la opción que ya usa el código que te entregué,
     no necesitas elegir otra ni programar nada adicional).
   - Si te pregunta el modelo de integración, elige la opción más simple
     disponible (normalmente "Pagos en línea" o "Ecommerce").
4. Ya creada la aplicación, entra a ella y ahí sí verás **Credenciales de
   producción** y **Credenciales de prueba**.
5. Si es la primera vez que activas credenciales de producción, Mercado
   Pago te va a pedir completar unos datos del negocio antes de dártelas:
   - **Industria**: elige la que más se parezca a lo que haces (por
     ejemplo "Servicios profesionales", "Consultoría" o "Recursos Humanos").
   - **Sitio web (obligatorio)**: aquí va la URL de **tu página web**,
     `https://www.humen.solutions` — **no** la URL del backend de Apps
     Script (esa es otra, la vas a usar recién en el Paso 6, no aquí).
   - Marca la autorización, completa el captcha y clic en **"Activar
     credenciales de producción"**.
6. Verás dos pares de credenciales: **de prueba** y **de producción**.
   - Usa las **de prueba** mientras configuras todo (para no cobrar de verdad).
   - Cuando todo funcione, cambia al **Access Token de producción**.
7. Copia el **Access Token** (empieza con `APP_USR-` o `TEST-`). Lo vas a
   necesitar en el Paso 4.

---

## Paso 2 — Crear la Google Sheet donde se registran los pedidos

1. Ve a https://sheets.google.com y crea una hoja de cálculo nueva.
2. Ponle un nombre, por ejemplo **"Pedidos - Pagos web"**.
3. Déjala vacía (el sistema escribe los encabezados automáticamente la
   primera vez que se usa).
4. De la URL, copia el ID de la hoja — es el texto largo entre `/d/` y
   `/edit`:

   ```
   https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit
   ```

---

## Paso 3 — Crear la plantilla del contrato / orden de servicio

1. Ve a https://docs.google.com y crea un documento nuevo con el texto de
   tu contrato u orden de servicio, tal como lo usas normalmente.
2. En los lugares donde debe ir información de cada cliente, escribe
   exactamente estos textos (con las llaves dobles, tal cual se ven abajo,
   sin ningún otro símbolo alrededor), y el sistema los reemplaza
   automáticamente:

   | Escribe esto en el documento | Se reemplaza por |
   |---|---|
   | {{NOMBRE}} | Nombre del cliente |
   | {{CORREO}} | Correo del cliente |
   | {{TELEFONO}} | Teléfono del cliente |
   | {{SERVICIO}} | Servicio contratado |
   | {{MONTO}} | Monto pagado (ej: S/ 350.00) |
   | {{CODIGO}} | Código de la cotización |
   | {{FECHA}} | Fecha de emisión |
   | {{DETALLE}} | Detalle completo de la cotización |
   | {{TIPO_COMPROBANTE}} | "Boleta" o "Factura" |
   | {{RAZON_SOCIAL}} | Nombre de la empresa (solo si es factura) |
   | {{RUC}} | RUC (solo si es factura) |
   | {{DNI}} | DNI (solo si es boleta y el cliente lo proporcionó) |

3. De la URL del documento, copia el ID (igual que en el Paso 2, el texto
   entre `/d/` y `/edit`).

**Opcional:** crea también una carpeta en Google Drive donde quieras
guardar copia de cada contrato generado, y copia su ID desde la URL
(`https://drive.google.com/drive/folders/ESTE_ES_EL_ID`).

---

## Paso 4 — Desplegar el backend en Google Apps Script

1. Ve a https://script.google.com y crea un **Proyecto nuevo**.
   - Si prefieres usar el mismo proyecto de tu ERP en vez de uno nuevo,
     también funciona — solo agrega un archivo nuevo dentro de ese proyecto.
2. Borra el contenido de ejemplo (`function myFunction() {}`) y pega
   completo el contenido del archivo **`Codigo.gs`** que te entregué.
3. Ve a **⚙ Configuración del proyecto** (ícono de engranaje, panel
   izquierdo) → baja hasta **"Propiedades del script"** → **"Agregar
   propiedad del script"**, y agrega una por una:

   > ⚠️ **Importante:** copia solo el texto, **sin las comillas invertidas**
   > ( ` ) que puedan aparecer alrededor en esta guía — esas comillas son
   > solo de formato, no van dentro del campo. El nombre de la propiedad
   > debe quedar exactamente `MP_ACCESS_TOKEN`, no `` `MP_ACCESS_TOKEN` ``.

   | Propiedad | Valor |
   |---|---|
   | MP_ACCESS_TOKEN | El Access Token que copiaste en el Paso 1 |
   | HOJA_PEDIDOS_ID | El ID de la hoja del Paso 2 |
   | PLANTILLA_CONTRATO_ID | El ID del documento del Paso 3 |
   | CARPETA_CONTRATOS_ID | (opcional) ID de la carpeta del Paso 3 |
   | CORREO_NEGOCIO | El correo donde quieres recibir el aviso de cada pago |
   | URL_EXITO | https://www.humen.solutions/gracias.html |
   | URL_SITIO | https://www.humen.solutions |

4. Guarda el proyecto (ícono de disquete o Ctrl+S).
5. Arriba a la derecha, clic en **Implementar → Nueva implementación**.
   - Tipo: **Aplicación web**.
   - Ejecutar como: **Yo (tu correo)**.
   - Quién tiene acceso: **Cualquier usuario**.
6. Clic en **Implementar**. La primera vez te pedirá autorizar permisos
   (acceso a Sheets, Drive, Gmail) — es normal, son los permisos que el
   script necesita para funcionar. Acepta.
7. Copia la **URL de la aplicación web** que te muestra al terminar
   (termina en `/exec`). La necesitas en el Paso 5.

> Cada vez que edites el código más adelante, tendrás que volver a
> **Implementar → Administrar implementaciones → ✏️ Editar → Nueva
> versión** para que los cambios se apliquen.

---

## Paso 5 — Conectar la web con el backend

Desde que cada servicio (Contabilidad, Inventarios, HUMEN Clean) tiene su
propia página con su propio cotizador, este backend ya no se conecta desde
`js/script.js` — ese archivo ahora solo tiene la lógica del sitio principal
(menú, animaciones, formulario de contacto). El cotizador y el pago viven en
`js/cotizador-comun.js`, compartido por las 3 sub-páginas.

1. Abre el archivo `js/cotizador-comun.js`.
2. Busca esta línea (cerca del inicio del archivo):

   ```js
   var MP_BACKEND_URL = "https://script.google.com/macros/s/AKfycb.../exec";
   ```

3. Reemplázala por la URL que copiaste en el Paso 4, entre comillas. Como es
   un solo archivo compartido, actualizarlo aquí actualiza el pago en las 3
   páginas de servicio a la vez (`contabilidad/`, `inventarios/`,
   `humen-clean/`).

4. Sube el archivo actualizado a tu repositorio / hosting.

---

## Paso 6 — Activar las notificaciones de pago (webhook)

Esta configuración vive en el **panel de Developers** de Mercado Pago
(distinto del panel normal de tu cuenta), dentro de tu aplicación:

1. Entra a tu aplicación en el panel de Developers. La forma más directa:
   - Ve a **Tus integraciones → Integraciones** (arriba a la derecha del
     panel dice **"Integraciones"**), y selecciona tu aplicación (ej.
     `Sitio web HUMEN SOLUTIONS`).
   - O usa la URL directa con el **Client ID** de tu aplicación (lo ves en
     la pantalla de Credenciales de producción):
     ```
     https://www.mercadopago.com.pe/developers/panel/app/TU_CLIENT_ID/webhooks
     ```
2. En el menú de la izquierda, dentro de la sección **"NOTIFICACIONES"**,
   haz clic en **"Webhooks"**.
3. Clic en el botón azul **"Configurar notificaciones"**.
4. Pega la URL de tu backend (la que termina en `/exec`, del Paso 4) tanto
   en el campo de **producción** como en el de **prueba**.
5. En **Eventos**, marca **"Pagos"**.
6. Clic en **"Guardar"** (esto también genera una firma secreta para la
   aplicación — no es necesaria para lo que armamos, no pasa nada si se
   crea igual).

Con esto, cuando un pago se apruebe, Mercado Pago avisará automáticamente
a tu backend, que generará el contrato y enviará los correos.

---

## Cómo probar todo sin cobrar de verdad

Mientras uses el **Access Token de prueba** (Paso 1), Mercado Pago te deja
pagar con tarjetas de prueba que no cobran dinero real. Perú:

- Tarjeta de prueba Visa: `4009 1753 3280 6176`, cualquier fecha futura,
  CVV `123`.
- Puedes generar más tarjetas de prueba en:
  https://www.mercadopago.com.pe/developers/es/docs/checkout-pro/additional-content/test-cards

También puedes ejecutar la función `probarConfiguracion` directamente
desde el editor de Apps Script (selecciónala en el menú desplegable de
arriba y clic en ▶ Ejecutar) — te genera un link de pago de prueba y lo
muestra en los "Registros" (Ver → Registros), sin necesidad de tocar la
página web.

Cuando confirmes que todo funciona bien, reemplaza el Access Token de
prueba por el **de producción** en las Propiedades del script (Paso 4) y
listo — pagos reales.

---

## Preguntas frecuentes

**¿Esto emite la boleta o factura electrónica?**
No. Genera el contrato/orden de servicio y te avisa por correo cuando
entra un pago, para que emitas la boleta/factura por tu proceso habitual
(el que ya tienes resuelto). Si más adelante quieres automatizar también
esa parte, es un paso aparte que se puede agregar.

**¿Puedo agregar Izipay más adelante?**
Sí — la estructura del backend está pensada para eso: se agregaría una
función parecida a `crearPreferenciaMP` pero para la API de Izipay, y un
segundo botón en la web. Es un buen siguiente paso una vez que Mercado
Pago esté funcionando bien.

**¿Qué pasa si un cliente cierra la ventana antes de pagar?**
El pedido queda guardado como "pendiente" en la Google Sheet. No pasa
nada malo — simplemente no se generará el contrato ni se enviará ningún
correo hasta que el pago se confirme.

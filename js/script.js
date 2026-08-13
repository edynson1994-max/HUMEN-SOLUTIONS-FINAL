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
    COTIZADOR HUMEN SOLUTIONS V3
==================================================*/

// Filtro de seguridad simple: por encima de estos montos, la cotización
// no se puede pagar directo — el cliente debe pasar por "Solicitar
// Cotización" para una revisión manual antes de cobrar.
const UMBRAL_REVISION_MANUAL = {
    reclutamiento: 3000,
    inventario: 3000,
    contabilidad: 2500
};

function requiereRevisionManual(servicio, precio) {
    const umbral = UMBRAL_REVISION_MANUAL[servicio];
    return umbral ? precio > umbral : false;
}

const Cotizador = {

    iniciar() {

    console.log("Cotizador iniciado");

    this.obtenerElementos();

},
obtenerElementos() {

    this.botones = document.querySelectorAll(".cotizador-btn");

    this.resultado = document.querySelector(".cotizador-resultado h2");

    this.detalle = document.getElementById("detalleCotizacion");

    this.contenedor = document.getElementById("contenedorFormulario");

    this.servicioActual = "reclutamiento";

    console.log("Botones encontrados:", this.botones.length);

    this.eventos();

    this.mostrarFormulario();

},

eventos() {

    this.botones.forEach(boton => {

        boton.addEventListener("click", () => {

            this.botones.forEach(btn => {
                btn.classList.remove("active");
            });

            boton.classList.add("active");

            this.servicioActual = boton.dataset.servicio;

            this.mostrarFormulario();

            console.log("Servicio:", this.servicioActual);

        });

    });

},

mostrarFormulario() {

    this.contenedor.innerHTML=`

<h3>Reclutamiento y Selección de Personal</h3>

<label>Nombre del puesto</label>

<input
type="text"
id="puesto"
placeholder="Ejemplo: Asistente Contable">

<label>Sueldo mensual ofrecido (S/)</label>

<input
type="number"
id="sueldo"
min="0"
placeholder="Ejemplo: 1800">

<label>Cantidad de vacantes</label>

<input
type="number"
id="vacantes"
min="1"
value="1">

<label>1. Nivel del puesto requerido</label>

<select id="nivelPuesto">

<option value="">Seleccione...</option>

<option value="operativo">
Operativo / Campo
</option>

<option value="comercial">
Comercial / Atención
</option>

<option value="administrativo">
Administrativo / Confianza
</option>

<option value="jefatura">
Jefatura / Gerencia
</option>

</select>

<small>

Determina el nivel de filtro de antecedentes,
entrevistas y validación de referencias.

</small>

<br><br>

<label>2. Urgencia del proceso</label>

<select id="urgencia">

<option value="normal">
Estándar (10 a 15 días)
</option>

<option value="urgente">
Urgente (5 a 7 días)
</option>

<option value="expreso">
Expreso (3 a 4 días)
</option>

</select>

<hr>

<div style="font-size:13px;opacity:.85;line-height:1.7">

<b>El servicio incluye</b>

<ul>

<li>Publicación de la vacante.</li>

<li>Filtro curricular.</li>

<li>Entrevista por competencias.</li>

<li>Validación de referencias laborales.</li>

<li>Verificación de antecedentes.</li>

<li>Garantía de reposición por 30 días.</li>

</ul>

</div>

<button id="btnCalcular">

Calcular Cotización

</button>

`;

document
.getElementById("btnCalcular")
.addEventListener("click",()=>{

this.calcularReclutamiento();

});

    if (this.servicioActual === "inventario") {

this.contenedor.innerHTML = `

<h3>Inventario y Control de Almacén</h3>

<label>1. ¿Qué servicio necesitas?</label>

<select id="tipoServicio">

<option value="">Seleccione...</option>

<option value="puntual">
Toma de Inventario Físico (Puntual)
</option>

<option value="kardex">
Control de Kárdex y Stock (Mensual)
</option>

</select>

<small>
Elige si necesitas una auditoría puntual o un control permanente.
</small>

<br><br>

<label>2. ¿Cuántos tipos de productos (SKUs) manejas?</label>

<select id="skus">

<option value="">Seleccione...</option>

<option value="150">
Hasta 150 tipos
</option>

<option value="600">
151 a 600 tipos
</option>

<option value="1500">
601 a 1500 tipos
</option>

<option value="masivo">
Más de 1500 (Evaluación técnica)
</option>

</select>

<small>

Cada talla, color o presentación cuenta como un SKU diferente.

</small>

<br><br>

<label>3. Cantidad aproximada de unidades físicas</label>

<select id="unidades">

<option value="">Seleccione...</option>

<option value="3000">
Hasta 3,000 unidades
</option>

<option value="10000">
3,001 a 10,000
</option>

<option value="30000">
10,001 a 30,000
</option>

<option value="masivo">
Más de 30,000
</option>

</select>

<br><br>

<label>4. ¿Cuántos locales o almacenes?</label>

<select id="almacenes">

<option value="1">1 almacén</option>

<option value="2">2 almacenes</option>

<option value="3">3 almacenes</option>

<option value="4">Más de 3</option>

</select>

<br><br>

<label>5. Ubicación</label>

<select id="ciudad">

<option value="">Seleccione...</option>

<option value="Cusco">Cusco Cercado</option>

<option value="Wanchaq">Wanchaq</option>

<option value="Santiago">Santiago</option>

<option value="San Sebastian">San Sebastián</option>

<option value="San Jeronimo">San Jerónimo</option>

<option value="Valle">Valle Sagrado</option>

<option value="Otra">Otra ciudad</option>

</select>

<br><br>

<label>6. Estado de la mercadería</label>

<select id="organizacion">

<option value="">Seleccione...</option>

<option value="excelente">
Excelente
</option>

<option value="regular">
Regular
</option>

<option value="desordenado">
Desordenado
</option>

</select>

<br><br>

<label>7. Código de barras</label>

<select id="codigo">

<option value="todos">
Todos los productos
</option>

<option value="parcial">
Solo algunos
</option>

<option value="ninguno">
Ninguno
</option>

</select>

<br><br>

<label class="check-card">

<span>

Requiere conciliación de diferencias

</span>

<input
type="checkbox"
id="conciliacion">

</label>

<br>

<label class="check-card">

<span>

Requiere valorización económica

</span>

<input
type="checkbox"
id="valorizacion">

</label>

<br>

<label class="check-card">

<span>

Informe Ejecutivo para Gerencia

</span>

<input
type="checkbox"
id="ejecutivo">

</label>

<hr>

<div style="font-size:13px;opacity:.85;line-height:1.7">

<b>Condiciones del servicio</b>

<ul>

<li>La tarifa considera hasta 3,000 unidades físicas.</li>

<li>Almacenes de gran volumen requieren visita técnica.</li>

<li>La mercadería debe encontrarse accesible para el conteo.</li>

<li>Servicios fuera de Cusco tendrán viáticos adicionales.</li>

</ul>

</div>

<button id="btnCalcularInventario">

Calcular Cotización

</button>

`;

document
.getElementById("btnCalcularInventario")
.addEventListener("click",()=>{

this.calcularInventario();

});

}

    if (this.servicioActual === "contabilidad") {

this.contenedor.innerHTML=`

<h3>Servicio Contable</h3>

<label>Régimen Tributario</label>

<select id="regimen">

<option value="">Seleccione...</option>

<option value="RUS">Nuevo RUS</option>

<option value="RER">Régimen Especial (RER)</option>

<option value="RMT">Régimen MYPE Tributario</option>

<option value="GENERAL">Régimen General</option>

</select>


<label>Comprobantes mensuales</label>

<input
type="number"
id="comprobantes"
min="0"
placeholder="Ejemplo: 120">


<label>Trabajadores en planilla</label>

<input
type="number"
id="trabajadores"
value="0"
min="0">


<hr>

<h4 class="titulo-seccion">

Operaciones Especiales

</h4>

<label class="check-card">

<span>

Realiza importaciones

</span>

<input
type="checkbox"
id="importaciones">

</label>

<label class="check-card">

<span>

Realiza exportaciones

</span>

<input
type="checkbox"
id="exportaciones">

</label>

<label class="check-card">

<span>

Opera con detracciones

</span>

<input
type="checkbox"
id="detracciones">

</label>

<label class="check-card">

<span>

Percepciones / Retenciones

</span>

<input
type="checkbox"
id="retenciones">

</label>

<label class="check-card">

<span>

Maneja caja chica

</span>

<input
type="checkbox"
id="cajachica">

</label>

<label class="check-card">

<span>

Más de una cuenta bancaria

</span>

<input
type="checkbox"
id="bancos">

</label>

<hr>

<h4 class="titulo-seccion">Servicios Adicionales</h4>

<label class="check-card">

<span>

Emisión de comprobantes electrónicos

</span>

<input
type="checkbox"
id="facturacion">

</label>

<label class="check-card">

<span>

Reportes gerenciales

</span>

<input
type="checkbox"
id="reportes">

</label>

<label class="check-card">

<span>

Atención de requerimientos SUNAT

</span>

<input
type="checkbox"
id="sunat">

</label>

<label class="check-card">

<span>

Asesoría tributaria permanente

</span>

<input
type="checkbox"
id="asesoria">

</label>

<button
id="btnCalcularContabilidad">

Calcular Cotización

</button>

`;

document

.getElementById("btnCalcularContabilidad")

.addEventListener("click",()=>{

this.calcularContabilidad();

});

}

},

calcularReclutamiento(){

const puesto=document.getElementById("puesto").value.trim();

const sueldo=Number(document.getElementById("sueldo").value);

const vacantes=Number(document.getElementById("vacantes").value);

const nivel=document.getElementById("nivelPuesto").value;

const urgencia=document.getElementById("urgencia").value;

if(
puesto===""||
isNaN(sueldo)||sueldo<=0||
isNaN(vacantes)||vacantes<=0||
nivel===""){
alert("Complete todos los datos con valores válidos.");
return;
}

if(sueldo>30000){
alert("Para sueldos mayores a S/30,000 contáctanos directamente para una cotización personalizada.");
return;
}

if(vacantes>30){
alert("Para más de 30 vacantes contáctanos directamente — seguro conseguimos un mejor precio por volumen.");
return;
}

let precioBase=0;

let porcentaje=0;

let minimo=0;

let detalle=[];

let diagnostico=[];

let recomendaciones=[];

/*-------------------------
NIVEL DEL PUESTO
--------------------------*/

switch(nivel){

case "operativo":

porcentaje=0.45;
minimo=480;

diagnostico.push(
"El puesto corresponde a un nivel operativo con un proceso estándar de selección."
);

break;

case "comercial":

porcentaje=0.55;
minimo=620;

diagnostico.push(
"El puesto requiere evaluar habilidades comerciales y de atención al cliente."
);

break;

case "administrativo":

porcentaje=0.70;
minimo=890;

diagnostico.push(
"El proceso contempla validación de antecedentes y referencias laborales."
);

break;

case "jefatura":

porcentaje=1.05;
minimo=1650;

diagnostico.push(
"El puesto requiere un proceso de búsqueda especializado y entrevistas de mayor profundidad."
);

break;

}

precioBase=Math.max(
sueldo*porcentaje,
minimo
);

detalle.push(
`Primera vacante ...................... S/${precioBase.toFixed(2)}`
);

let subtotal=precioBase;

/*-------------------------
VACANTES ADICIONALES
--------------------------*/

if(vacantes>1){

const adicionales=(vacantes-1)*(precioBase*0.50);

subtotal+=adicionales;

detalle.push(
`Vacantes adicionales (${vacantes-1}) ......... S/${adicionales.toFixed(2)}`
);

diagnostico.push(
`Se cubrirán ${vacantes} vacantes del mismo perfil.`
);

}

/*-------------------------
URGENCIA
--------------------------*/

let porcentajeUrgencia=0;
let tiempo="10 a 15 días hábiles";

switch(urgencia){

case "normal":

porcentajeUrgencia=0;

diagnostico.push(
"El proceso seguirá el tiempo estándar de reclutamiento."
);

break;

case "urgente":

porcentajeUrgencia=0.20;

tiempo="5 a 7 días hábiles";

diagnostico.push(
"El cliente requiere acelerar el proceso de selección."
);

detalle.push(
"Recargo por urgencia ............... +20%"
);

break;

case "expreso":

porcentajeUrgencia=0.35;

tiempo="3 a 4 días hábiles";

diagnostico.push(
"Se requiere una búsqueda prioritaria con dedicación exclusiva."
);

detalle.push(
"Recargo por servicio expreso ....... +35%"
);

break;

}

const recargo=subtotal*porcentajeUrgencia;

const total=subtotal+recargo;

if(recargo>0){

detalle.push(
`Recargo aplicado ................... S/${recargo.toFixed(2)}`
);

}

/*-------------------------
RECOMENDACIONES
--------------------------*/

recomendaciones.push(
"El servicio incluye publicación de la vacante y filtro curricular."
);

recomendaciones.push(
"Se realizará entrevista por competencias."
);

recomendaciones.push(
"Se validarán antecedentes policiales, penales y referencias laborales."
);

recomendaciones.push(
"Incluye una reposición sin costo durante los primeros 30 días."
);

if(nivel==="jefatura"){

recomendaciones.push(
"Para cargos estratégicos se recomienda una entrevista final con la gerencia."
);

}

let complejidad="Baja";
let estrellas="⭐⭐☆☆☆";

if(total>=800){

complejidad="Media";
estrellas="⭐⭐⭐☆☆";

}

if(total>=1500){

complejidad="Alta";
estrellas="⭐⭐⭐⭐☆";

}

if(total>=3000){

complejidad="Muy Alta";
estrellas="⭐⭐⭐⭐⭐";

}

const codigo=this.generarCodigoCotizacion();

const html=`

<div class="resultado-cotizacion">

<h3>👥 Cotización de Reclutamiento</h3>

<h4>Valorización del Servicio</h4>

${detalle.map(x=>`<div>${x}</div>`).join("")}

<hr>

<div style="display:flex;justify-content:space-between;font-size:1.2rem;font-weight:bold">

<span>TOTAL</span>

<span>S/${total.toFixed(2)}</span>

</div>

<hr>

<h4>Complejidad del Proceso</h4>

<p>${estrellas}</p>

<p><strong>${complejidad}</strong></p>

<hr>

<h4>Diagnóstico</h4>

<ul>

${diagnostico.map(x=>`<li>${x}</li>`).join("")}

</ul>

<hr>

<h4>Tiempo estimado</h4>

<p>${tiempo}</p>

<hr>

<h4>Incluye el servicio</h4>

<ul>

<li>Publicación de la vacante.</li>

<li>Filtro curricular.</li>

<li>Entrevista por competencias.</li>

<li>Verificación de antecedentes.</li>

<li>Validación de referencias laborales.</li>

<li>Presentación de candidatos finalistas.</li>

<li>Garantía de reposición por 30 días.</li>

</ul>

<hr>

<h4>Recomendaciones</h4>

<ul>

${recomendaciones.map(x=>`<li>${x}</li>`).join("")}

</ul>

<hr>

<h4>Condiciones comerciales</h4>

<ul>

<li>50% al iniciar el proceso.</li>

<li>50% al incorporarse el candidato seleccionado.</li>

<li>No incluye evaluaciones médicas ni psicológicas especializadas.</li>

<li>La garantía cubre una reposición dentro de los primeros 30 días.</li>

<li>Cada perfil distinto se cotiza de forma independiente.</li>

</ul>

</div>

`;

this.parametrosActuales = {nivel, sueldo, vacantes, urgencia};

this.mostrarResultado(total,html);

},

calcularInventario(){

const tipoServicio=document.getElementById("tipoServicio").value;
const skus=document.getElementById("skus").value;
const unidades=document.getElementById("unidades").value;
const almacenes=Number(document.getElementById("almacenes").value);
const ciudad=document.getElementById("ciudad").value;
const organizacion=document.getElementById("organizacion").value;
const codigo=document.getElementById("codigo").value;

const conciliacion=document.getElementById("conciliacion").checked;
const valorizacion=document.getElementById("valorizacion").checked;
const ejecutivo=document.getElementById("ejecutivo").checked;

if(
tipoServicio===""||
skus===""||
unidades===""||
ciudad===""||
organizacion===""||
isNaN(almacenes)||almacenes<1){
alert("Complete todos los datos con valores válidos.");
return;
}

if(almacenes>15){
alert("Para más de 15 almacenes contáctanos directamente para una cotización personalizada.");
return;
}

if(skus==="masivo"){
alert("Este volumen de SKUs requiere una visita técnica previa.");
return;
}

let total=0;

let detalle=[];

let diagnostico=[];

let recomendaciones=[];

let puntos=0;

/*-------------------------
SERVICIO
--------------------------*/

if(tipoServicio==="puntual"){

total+=950;

detalle.push("Inventario físico puntual .......... S/950");

puntos+=2;

diagnostico.push("Se realizará un inventario físico con conciliación e informe final.");

}

if(tipoServicio==="kardex"){

total+=710;

detalle.push("Control mensual de Kárdex .......... S/710");

puntos+=1;

diagnostico.push("El servicio corresponde al control permanente del inventario.");

}

/*-------------------------
SKUs
--------------------------*/

switch(skus){

case "150":

diagnostico.push("Hasta 150 tipos de productos.");

break;

case "600":

total+=250;

detalle.push("151 a 600 SKUs ..................... +S/250");

puntos++;

diagnostico.push("Inventario con variedad media de productos.");

break;

case "1500":

total+=500;

detalle.push("601 a 1500 SKUs .................... +S/500");

puntos+=2;

diagnostico.push("Alta variedad de productos.");

break;

}

/*-------------------------
UNIDADES
--------------------------*/

switch(unidades){

case "3000":

diagnostico.push("Hasta 3,000 unidades físicas.");

break;

case "10000":

total+=250;

detalle.push("3,001 a 10,000 unidades ............ +S/250");

puntos++;

diagnostico.push("Volumen medio de conteo.");

break;

case "30000":

total+=500;

detalle.push("10,001 a 30,000 unidades ........... +S/500");

puntos+=2;

diagnostico.push("Alto volumen de inventario.");

break;

case "masivo":

total+=900;

detalle.push("Más de 30,000 unidades ............. +S/900");

puntos+=4;

diagnostico.push("Inventario de gran volumen.");

break;

}

/*-------------------------
ALMACENES
--------------------------*/

if(almacenes>1){

const extra=(almacenes-1)*150;

total+=extra;

detalle.push(
`${almacenes} almacenes ..................... +S/${extra}`
);

puntos+=almacenes-1;

diagnostico.push(
`Inventario distribuido en ${almacenes} almacenes.`
);

}

/*-------------------------
UBICACIÓN
--------------------------*/

if(ciudad==="Valle"){

total+=120;

detalle.push("Viáticos Valle Sagrado ............. +S/120");

recomendaciones.push("Incluye desplazamiento al Valle Sagrado.");

}

if(ciudad==="Otra"){

total+=250;

detalle.push("Viáticos fuera de Cusco ............ +S/250");

recomendaciones.push("Los viáticos pueden variar según la ubicación.");

}

/*-------------------------
ORGANIZACIÓN
--------------------------*/

switch(organizacion){

case "excelente":

diagnostico.push("Mercadería correctamente organizada.");

break;

case "regular":

total+=120;

detalle.push("Organización regular ............... +S/120");

puntos++;

diagnostico.push("Será necesario ordenar parcialmente la mercadería.");

break;

case "desordenado":

total+=300;

detalle.push("Mercadería desordenada ............. +S/300");

puntos+=3;

diagnostico.push("El conteo demandará búsqueda manual de productos.");

break;

}

/*-------------------------
CÓDIGOS DE BARRAS
--------------------------*/

switch(codigo){

case "todos":

diagnostico.push("Todos los productos cuentan con código.");

break;

case "parcial":

total+=80;

detalle.push("Código de barras parcial ........... +S/80");

puntos++;

break;

case "ninguno":

total+=180;

detalle.push("Sin código de barras ............... +S/180");

puntos+=2;

recomendaciones.push("Se recomienda implementar codificación para futuros inventarios.");

break;

}

/*-------------------------
SERVICIOS ADICIONALES
--------------------------*/

if(conciliacion){

total+=120;

detalle.push("Conciliación de diferencias ........ +S/120");

recomendaciones.push("Se entregará análisis de sobrantes y faltantes.");

}

if(valorizacion){

total+=150;

detalle.push("Valorización económica ............. +S/150");

recomendaciones.push("Se entregará valorización monetaria del inventario.");

}

if(ejecutivo){

total+=100;

detalle.push("Informe ejecutivo ................. +S/100");

recomendaciones.push("Incluye conclusiones y recomendaciones gerenciales.");

}

/*-------------------------
COMPLEJIDAD
--------------------------*/

let complejidad="";
let estrellas="";
let equipo=2;
let tiempo="1 día";

if(puntos<=2){
    complejidad="Baja";
    estrellas="⭐⭐☆☆☆";
    equipo=2;
    tiempo="1 día";
}
else if(puntos<=5){
    complejidad="Media";
    estrellas="⭐⭐⭐☆☆";
    equipo=2;
    tiempo="1 a 2 días";
}
else if(puntos<=8){
    complejidad="Alta";
    estrellas="⭐⭐⭐⭐☆";
    equipo=3;
    tiempo="2 a 3 días";
}
else{
    complejidad="Muy Alta";
    estrellas="⭐⭐⭐⭐⭐";
    equipo=4;
    tiempo="3 a 5 días";
}

if(recomendaciones.length===0){
    recomendaciones.push("No se identificaron requerimientos adicionales para este servicio.");
}

const codigoCotizacion=this.generarCodigoCotizacion();

const html=`

<div class="resultado-cotizacion">

<h3>📦 Cotización de Inventario</h3>

<h4>Valorización del Servicio</h4>

${detalle.map(item=>`<div>${item}</div>`).join("")}

<hr>

<div style="display:flex;justify-content:space-between;font-size:1.2rem;font-weight:bold">

<span>TOTAL ESTIMADO</span>

<span>S/${total.toFixed(2)}</span>

</div>

<hr>

<h4>Nivel de Complejidad</h4>

<p>${estrellas}</p>

<p><strong>${complejidad}</strong></p>

<hr>

<h4>Diagnóstico</h4>

<ul>

${diagnostico.map(d=>`<li>${d}</li>`).join("")}

</ul>

<hr>

<h4>Recomendaciones</h4>

<ul>

${recomendaciones.map(r=>`<li>${r}</li>`).join("")}

</ul>

<hr>

<h4>Plan Operativo Recomendado</h4>

<p><strong>Equipo sugerido:</strong> ${equipo} inventarista(s)</p>

<p><strong>Tiempo estimado:</strong> ${tiempo}</p>

<p><strong>Entrega del informe:</strong> 48 horas después del servicio.</p>

<hr>

<div style="font-size:.9rem;opacity:.85">

<b>Condiciones del servicio</b>

<ul>

<li>La tarifa considera hasta 3,000 unidades como volumen estándar.</li>

<li>Inventarios masivos podrán requerir una visita técnica previa.</li>

<li>La mercadería deberá encontrarse accesible para realizar el conteo.</li>

<li>Los servicios fuera de la ciudad de Cusco pueden generar costos adicionales por desplazamiento.</li>

<li>El precio es final según los datos proporcionados; si el alcance real del servicio difiere de lo declarado, se cotiza el ajuste por separado.</li>

</ul>

</div>

</div>

`;

this.parametrosActuales = {tipoServicio, skus, unidades, almacenes, ciudad, organizacion, codigo, conciliacion, valorizacion, ejecutivo};

this.mostrarResultado(total,html);

},

calcularContabilidad(){

const regimen=document.getElementById("regimen").value;
const comprobantes=Number(document.getElementById("comprobantes").value);
const trabajadores=Number(document.getElementById("trabajadores").value);

const importaciones=document.getElementById("importaciones").checked;
const exportaciones=document.getElementById("exportaciones").checked;
const detracciones=document.getElementById("detracciones").checked;
const retenciones=document.getElementById("retenciones").checked;
const cajachica=document.getElementById("cajachica").checked;
const bancos=document.getElementById("bancos").checked;

const facturacion=document.getElementById("facturacion").checked;
const reportes=document.getElementById("reportes").checked;
const sunat=document.getElementById("sunat").checked;
const asesoria=document.getElementById("asesoria").checked;

if(
regimen===""||
isNaN(comprobantes)||comprobantes<0||
isNaN(trabajadores)||trabajadores<0){
alert("Complete todos los datos con valores válidos (comprobantes y trabajadores, aunque sea con 0).");
return;
}

if(comprobantes>300){
alert("Para más de 300 comprobantes mensuales contáctanos directamente para una cotización personalizada.");
return;
}

if(trabajadores>100){
alert("Para más de 100 trabajadores en planilla contáctanos directamente para una cotización personalizada.");
return;
}

let total=0;

let detalle=[];

let diagnostico=[];

let recomendaciones=[];

let puntos=0;

/*--------------------------
BASE
---------------------------*/

if(regimen==="RUS"){

this.parametrosActuales = {regimen, comprobantes, trabajadores, importaciones, exportaciones, detracciones, retenciones, cajachica, bancos, facturacion, reportes, sunat, asesoria};

this.mostrarResultado(

65,

`
<strong>Nuevo RUS</strong><br><br>

Precio mensual estimado:
<strong>S/65.00</strong>

<br><br>

Este régimen tiene obligaciones tributarias básicas.

<br><br>

Para este régimen no es necesario completar una valorización detallada.
`

);

return;

}

if(regimen==="RER"){

total+=540;

detalle.push("Base Régimen Especial ............ S/540");

puntos+=1;

diagnostico.push("La empresa pertenece al Régimen Especial.");

}

if(regimen==="RMT"){

total+=720;

detalle.push("Base Régimen MYPE ............... S/720");

puntos+=2;

diagnostico.push("La empresa pertenece al Régimen MYPE Tributario.");

}

if(regimen==="GENERAL"){

total+=900;

detalle.push("Base Régimen General ............ S/900");

puntos+=3;

diagnostico.push("La empresa pertenece al Régimen General.");

}

/*--------------------------
COMPROBANTES
---------------------------*/

if(comprobantes<=50){

diagnostico.push("Hasta 50 comprobantes mensuales.");

}
else if(comprobantes<=150){

total+=50;

detalle.push("Comprobantes .................... +S/50");

puntos++;

diagnostico.push("Volumen medio de comprobantes.");

}
else{

// comprobantes <= 300 (más de 300 ya se bloquea arriba con evaluación manual)

total+=100;

detalle.push("Comprobantes .................... +S/100");

puntos+=2;

diagnostico.push("Alto volumen de comprobantes.");

}
/*--------------------------
PLANILLAS
---------------------------*/

if(trabajadores==0){

diagnostico.push("No cuenta con trabajadores en planilla.");

}

else if(trabajadores<=3){

total+=50;

detalle.push("Planilla (1-3 trabajadores) ..... +S/50");

puntos++;

diagnostico.push("Planilla pequeña.");

}

else if(trabajadores<=10){

total+=120;

detalle.push("Planilla (4-10 trabajadores) .... +S/120");

puntos+=2;

diagnostico.push("Planilla mediana.");

}

else{

let adicional=(trabajadores-10)*15;

total+=120+adicional;

detalle.push(`Planilla (${trabajadores} trabajadores) .... +S/${120+adicional}`);

puntos+=3;

diagnostico.push("Planilla numerosa.");

}

/*--------------------------
OPERACIONES ESPECIALES
---------------------------*/

if(importaciones){

total+=100;

detalle.push("Importaciones ................... +S/100");

puntos+=2;

diagnostico.push("Realiza importaciones.");

}

if(exportaciones){

total+=100;

detalle.push("Exportaciones ................... +S/100");

puntos+=2;

diagnostico.push("Realiza exportaciones.");

}

if(detracciones){

total+=60;

detalle.push("Detracciones .................... +S/60");

puntos++;

diagnostico.push("Opera con detracciones.");

}

if(retenciones){

total+=60;

detalle.push("Retenciones / Percepciones ...... +S/60");

puntos++;

diagnostico.push("Opera con retenciones o percepciones.");

}

if(cajachica){

total+=40;

detalle.push("Caja chica ...................... +S/40");

puntos++;

diagnostico.push("Administra caja chica.");

}

if(bancos){

total+=50;

detalle.push("Varias cuentas bancarias ........ +S/50");

puntos++;

diagnostico.push("Maneja varias cuentas bancarias.");

}

/*--------------------------
SERVICIOS ADICIONALES
---------------------------*/

if(facturacion){

total+=80;

detalle.push("Emisión comprobantes ............ +S/80");

recomendaciones.push("Incluye emisión de comprobantes electrónicos.");

}

if(reportes){

total+=80;

detalle.push("Reportes gerenciales ............ +S/80");

recomendaciones.push("Incluye reportes mensuales.");

}

if(sunat){

total+=60;

detalle.push("Atención SUNAT ................. +S/60");

recomendaciones.push("Incluye atención de requerimientos SUNAT.");

}

if(asesoria){

total+=100;

detalle.push("Asesoría tributaria ............. +S/100");

recomendaciones.push("Incluye asesoría tributaria permanente.");

}

/*--------------------------
COMPLEJIDAD
---------------------------*/

let complejidad="Baja";

if(puntos>=5) complejidad="Media";

if(puntos>=10) complejidad="Alta";

if(puntos>=15) complejidad="Muy Alta";

/*--------------------------
RECOMENDACIONES
---------------------------*/

if(trabajadores>20){

recomendaciones.push("Se recomienda automatizar la gestión de planillas.");

}

if(importaciones||exportaciones){

recomendaciones.push("Es recomendable realizar revisiones tributarias periódicas relacionadas con comercio exterior.");

}

if(detracciones||retenciones){

recomendaciones.push("Se recomienda efectuar conciliaciones tributarias mensuales.");

}

if(recomendaciones.length===0){

recomendaciones.push("La empresa presenta una operación estándar y puede mantenerse con el servicio mensual cotizado.");

}

/*--------------------------
RESULTADO
---------------------------*/

let html=`

<h3>Cotización Contable</h3>

<hr>

<h4>Valorización</h4>

${detalle.join("<br>")}

<br><br>

<strong>Total Mensual: S/${total.toFixed(2)}</strong>

<hr>

<h4>Complejidad</h4>

${complejidad}

<hr>

<h4>Diagnóstico</h4>

<ul>

${diagnostico.map(x=>`<li>${x}</li>`).join("")}

</ul>

<hr>

<h4>Recomendaciones</h4>

<ul>

${recomendaciones.map(x=>`<li>${x}</li>`).join("")}

</ul>

<hr>

<p>

La Declaración Jurada Anual no está incluida en esta cotización y se cotiza de manera independiente.

</p>

`;

this.parametrosActuales = {regimen, comprobantes, trabajadores, importaciones, exportaciones, detracciones, retenciones, cajachica, bancos, facturacion, reportes, sunat, asesoria};

this.mostrarResultado(total,html);

},


generarCodigoCotizacion() {

    const ahora = new Date();

    const fecha =
        ahora.getFullYear().toString() +
        String(ahora.getMonth() + 1).padStart(2, "0") +
        String(ahora.getDate()).padStart(2, "0");

    const aleatorio = Math.random()
        .toString(36)
        .substring(2, 6)
        .toUpperCase();

    return `HUM-${fecha}-${aleatorio}`;

},

mostrarResultado(precio, detalle) {

    const codigo = this.generarCodigoCotizacion();

    this.codigoActual = codigo;

    this.precioActual = precio;

    const fecha = new Date().toLocaleString("es-PE");

    this.resultado.innerHTML = `
        S/ ${precio.toLocaleString("es-PE", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}

        <div class="codigo-cotizacion" id="codigoCotizacion">
    ${this.codigoActual}
</div>

        <div class="fecha-cotizacion">
            ${fecha}
        </div>
    `;

    this.detalle.innerHTML = detalle;

    this.detalle.classList.remove("cotizacion-animada");

    void this.detalle.offsetWidth;

    this.detalle.classList.add("cotizacion-animada");

    // Filtro de seguridad: montos por encima del umbral no se pueden
    // pagar directo, requieren revisión manual vía "Solicitar Cotización"
    const btnPagarAhora = document.getElementById("btnPagarAhora");
    const notaRevision = document.getElementById("notaRevisionManual");
    const notaPagoSeguro = document.getElementById("notaPagoSeguro");

    if (btnPagarAhora) {

        const necesitaRevision = requiereRevisionManual(this.servicioActual, precio);

        btnPagarAhora.style.display = necesitaRevision ? "none" : "";

        if (notaRevision) {
            notaRevision.style.display = necesitaRevision ? "" : "none";
        }

        if (notaPagoSeguro) {
            notaPagoSeguro.style.display = necesitaRevision ? "none" : "";
        }
    }

    const btnSolicitar = document.getElementById("btnSolicitarCotizacion");

if (btnSolicitar) {

    btnSolicitar.onclick = () => {

        // Servicio
        document.getElementById("servicio").value =
            this.servicioActual === "reclutamiento"
                ? "Reclutamiento y Selección de Personal"
                : this.servicioActual === "inventario"
                ? "Inventarios Físicos"
                : "Contabilidad Empresarial";

        // Mensaje
        document.getElementById("mensaje").value =
`Código de Cotización:
${this.codigoActual}

Servicio:
${this.servicioActual}

Precio:
S/ ${precio.toLocaleString("es-PE", {
    minimumFractionDigits:2,
    maximumFractionDigits:2
})}

${document.getElementById("detalleCotizacion").innerText}`;

        // Ir al formulario
        document.getElementById("contacto").scrollIntoView({
            behavior: "smooth"
        });

    };

}

}

};

document.addEventListener("DOMContentLoaded", () => {

    Cotizador.iniciar();

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

/*==================================================
PAGO CON MERCADO PAGO
==================================================*/

// ⚠️ IMPORTANTE: reemplaza esta URL por la de tu Web App de Google Apps Script
// una vez que la despliegues (ver GUIA-INSTALACION.md). Mientras diga
// "PENDIENTE_CONFIGURAR", el botón de pago mostrará un aviso en vez de fallar en silencio.
const MP_BACKEND_URL = "PENDIENTE_CONFIGURAR";

document.addEventListener("DOMContentLoaded", () => {

    const btnPagar = document.getElementById("btnPagarAhora");
    const overlay = document.getElementById("pagoModalOverlay");
    const closeBtn = document.getElementById("pagoModalClose");
    const form = document.getElementById("formPago");
    const resumen = document.getElementById("pagoResumen");
    const errorBox = document.getElementById("pagoError");
    const btnConfirmar = document.getElementById("btnConfirmarPago");
    const camposFactura = document.getElementById("camposFactura");
    const camposBoleta = document.getElementById("camposBoleta");
    const radiosComprobante = document.querySelectorAll('input[name="tipoComprobante"]');

    if (!btnPagar || !overlay || !form) return;

    // Si el navegador restaura esta página desde su caché al volver con
    // "atrás" (por ejemplo, desde Mercado Pago), el botón puede quedar
    // pegado en el estado "Redirigiendo..." de un intento anterior.
    // Esto lo resetea automáticamente para no obligar al cliente a
    // recargar la página manualmente.
    window.addEventListener("pageshow", (event) => {
        if (event.persisted) {
            btnConfirmar.disabled = false;
            btnConfirmar.textContent = "Continuar a Mercado Pago";
        }
    });

    function nombreServicio(clave) {
        if (clave === "reclutamiento") return "Reclutamiento y Selección de Personal";
        if (clave === "inventario") return "Inventarios Físicos";
        return "Contabilidad Empresarial";
    }

    function tipoComprobanteActual() {
        const seleccionado = document.querySelector('input[name="tipoComprobante"]:checked');
        return seleccionado ? seleccionado.value : "boleta";
    }

    function actualizarCamposComprobante() {

        const esFactura = tipoComprobanteActual() === "factura";

        camposFactura.hidden = !esFactura;
        camposBoleta.hidden = esFactura;

        document.getElementById("pagoRazonSocial").required = esFactura;
        document.getElementById("pagoRuc").required = esFactura;
    }

    radiosComprobante.forEach(r => r.addEventListener("change", actualizarCamposComprobante));

    function abrir() {

        const precio = Cotizador.precioActual;

        if (!precio || precio <= 0) {
            alert("Primero completa los datos de tu cotización para calcular un precio.");
            return;
        }

        if (requiereRevisionManual(Cotizador.servicioActual, precio)) {
            alert("Este monto requiere una revisión manual antes de pagar. Por favor usa 'Solicitar Cotización'.");
            return;
        }

        errorBox.textContent = "";
        actualizarCamposComprobante();

        resumen.innerHTML = `
            <strong>Servicio:</strong> ${nombreServicio(Cotizador.servicioActual)}<br>
            <strong>Código:</strong> ${Cotizador.codigoActual}<br>
            <strong>Total a pagar:</strong> S/ ${precio.toLocaleString("es-PE", {minimumFractionDigits:2, maximumFractionDigits:2})}
        `;

        overlay.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function cerrar() {
        overlay.classList.remove("active");
        document.body.style.overflow = "";
    }

    btnPagar.addEventListener("click", abrir);
    closeBtn.addEventListener("click", cerrar);

    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) cerrar();
    });

    document.addEventListener("keydown", (e) => {
        if (overlay.classList.contains("active") && e.key === "Escape") cerrar();
    });

    form.addEventListener("submit", async (e) => {

        e.preventDefault();
        errorBox.textContent = "";

        const tipoComprobante = tipoComprobanteActual();
        const razonSocial = document.getElementById("pagoRazonSocial").value.trim();
        const ruc = document.getElementById("pagoRuc").value.trim();
        const dni = document.getElementById("pagoDni").value.trim();

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

        if (MP_BACKEND_URL === "PENDIENTE_CONFIGURAR") {
            errorBox.textContent = "El pago en línea aún no está activado. Por favor usa 'Solicitar Cotización' mientras tanto.";
            return;
        }

        const datos = {
            servicio: nombreServicio(Cotizador.servicioActual),
            servicioClave: Cotizador.servicioActual,
            parametros: Cotizador.parametrosActuales,
            monto: Cotizador.precioActual,
            codigo: Cotizador.codigoActual,
            detalle: document.getElementById("detalleCotizacion").innerText,
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

        const url = MP_BACKEND_URL + "?datos=" + encodeURIComponent(JSON.stringify(datos));

        // Navegación directa (no fetch): Apps Script nunca agrega el
        // encabezado de CORS necesario para leer una respuesta entre
        // dominios distintos, pero una navegación de página completa no
        // tiene esa restricción. Apps Script se encarga de redirigir a
        // Mercado Pago, o de mostrar una página de error si algo falla.
        window.location.href = url;

    });

});

/*==================================================
PROPONER UN PRECIO DISTINTO
==================================================*/

document.addEventListener("DOMContentLoaded", () => {

    const btnProponer = document.getElementById("btnProponerPrecio");
    const overlay = document.getElementById("proponerModalOverlay");
    const closeBtn = document.getElementById("proponerModalClose");
    const body = document.getElementById("proponerModalBody");
    const form = document.getElementById("formProponer");
    const resumen = document.getElementById("propResumen");
    const errorBox = document.getElementById("propError");
    const btnEnviar = document.getElementById("btnEnviarPropuesta");

    if (!btnProponer || !overlay || !form) return;

    function nombreServicio(clave) {
        if (clave === "reclutamiento") return "Reclutamiento y Selección de Personal";
        if (clave === "inventario") return "Inventarios Físicos";
        return "Contabilidad Empresarial";
    }

    function abrir() {

        const precio = Cotizador.precioActual;

        if (!precio || precio <= 0) {
            alert("Primero completa los datos de tu cotización para calcular un precio.");
            return;
        }

        errorBox.textContent = "";

        resumen.innerHTML = `
            <strong>Servicio:</strong> ${nombreServicio(Cotizador.servicioActual)}<br>
            <strong>Código:</strong> ${Cotizador.codigoActual}<br>
            <strong>Precio calculado por el sistema:</strong> S/ ${precio.toLocaleString("es-PE", {minimumFractionDigits:2, maximumFractionDigits:2})}
        `;

        overlay.classList.add("active");
        document.body.style.overflow = "hidden";
    }

    function cerrar() {
        overlay.classList.remove("active");
        document.body.style.overflow = "";
    }

    btnProponer.addEventListener("click", abrir);
    closeBtn.addEventListener("click", cerrar);

    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) cerrar();
    });

    document.addEventListener("keydown", (e) => {
        if (overlay.classList.contains("active") && e.key === "Escape") cerrar();
    });

    form.addEventListener("submit", async (e) => {

        e.preventDefault();
        errorBox.textContent = "";

        const presupuesto = Number(document.getElementById("propPresupuesto").value);

        if (!presupuesto || presupuesto <= 0) {
            errorBox.textContent = "Ingresa un presupuesto válido.";
            return;
        }

        // Si el honeypot tiene valor, es un bot — se finge éxito sin enviar nada
        const honeypot = document.getElementById("propHoneypot").value;
        if (honeypot) {
            body.innerHTML = `
                <div class="propuesta-enviada">
                    <svg xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    <h4>¡Propuesta enviada!</h4>
                    <p>Revisamos tu presupuesto y te contactamos directamente para coordinar el pago.</p>
                </div>
            `;
            return;
        }

        const datos = {
            _subject: "🤝 Propuesta de precio — " + Cotizador.codigoActual,
            _url: window.location.href,
            _honey: honeypot,
            Nombre: document.getElementById("propNombre").value.trim(),
            Correo: document.getElementById("propCorreo").value.trim(),
            Telefono: document.getElementById("propTelefono").value.trim(),
            Servicio: nombreServicio(Cotizador.servicioActual),
            "Código de cotización": Cotizador.codigoActual,
            "Precio calculado por el sistema": "S/ " + Cotizador.precioActual.toLocaleString("es-PE", {minimumFractionDigits:2}),
            "Presupuesto propuesto por el cliente": "S/ " + presupuesto.toLocaleString("es-PE", {minimumFractionDigits:2}),
            Mensaje: document.getElementById("propMensaje").value.trim() || "(sin mensaje adicional)",
            "Detalle de la cotización": document.getElementById("detalleCotizacion") ? document.getElementById("detalleCotizacion").innerText : "",
            _template: "table",
            _captcha: "false"
        };

        btnEnviar.disabled = true;
        btnEnviar.textContent = "Enviando...";

        try {

            const resp = await fetch("https://formsubmit.co/ajax/contacto@humen.solutions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                body: JSON.stringify(datos)
            });

            const resultado = await resp.json().catch(() => null);

            const exito = resp.ok && resultado && (resultado.success === "true" || resultado.success === true);

            if (!exito) {
                const detalle = resultado && resultado.message ? resultado.message : "";
                throw new Error("No se pudo enviar la propuesta." + (detalle ? " (" + detalle + ")" : ""));
            }

            body.innerHTML = `
                <div class="propuesta-enviada">
                    <svg xmlns="http://www.w3.org/2000/svg" width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    <h4>¡Propuesta enviada!</h4>
                    <p>Revisamos tu presupuesto y te contactamos directamente para coordinar el pago.</p>
                </div>
            `;

        } catch (err) {

            console.error(err);
            errorBox.textContent = "No pudimos enviar tu propuesta. Intenta de nuevo o contáctanos directamente por WhatsApp.";
            btnEnviar.disabled = false;
            btnEnviar.textContent = "Enviar propuesta";

        }

    });

});

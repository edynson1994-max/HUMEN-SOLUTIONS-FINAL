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
/*==================================================
        COTIZADOR HUMEN SOLUTIONS
==================================================*/

const servicio = document.getElementById("servicio");

if (servicio) {

const boxReclutamiento = document.getElementById("box-reclutamiento");
const boxInventario = document.getElementById("box-inventario");
const boxContabilidad = document.getElementById("box-contabilidad");

const precio = document.getElementById("precio");
const nivelServicio = document.getElementById("nivelServicio");

const resumen=document.getElementById("resumen");

const codigoCotizacion=document.getElementById("codigoCotizacion");

function ocultarTodo(){

boxReclutamiento.classList.remove("active");
boxInventario.classList.remove("active");
boxContabilidad.classList.remove("active");

}

servicio.addEventListener("change",function(){

ocultarTodo();

precio.innerHTML="0";
nivelServicio.innerHTML="Sin calcular";

if(this.value==="reclutamiento"){

boxReclutamiento.classList.add("active");

}

if(this.value==="inventario"){

boxInventario.classList.add("active");

}

if(this.value==="contabilidad"){

boxContabilidad.classList.add("active");

}

});

function calcular(){
let codigo="HUM-"+Math.floor(100000+Math.random()*900000);

codigoCotizacion.innerHTML=codigo;    

if(servicio.value==="reclutamiento"){

let sueldo=parseFloat(document.getElementById("sueldo").value)||0;

let porcentaje=parseFloat(document.getElementById("nivel").value);

let modalidad=parseFloat(document.getElementById("modalidad").value);

let vacantes=parseInt(document.getElementById("vacantes").value)||1;

let total=sueldo*porcentaje;

if(modalidad===0.5){

total=sueldo*0.50;

}

total=total*vacantes;

if(vacantes>=5){

total*=0.90;

}

if(vacantes>=10){

total*=0.85;

}

precio.innerHTML=Math.round(total).toLocaleString();

resumen.innerHTML=`

<b>Servicio</b><br>

Reclutamiento y Selección

<br><br>

<b>Puesto</b><br>

${document.getElementById("puesto").value||"-"}

<br><br>

<b>Vacantes</b><br>

${vacantes}

<br><br>

<b>Sueldo</b><br>

S/${sueldo.toLocaleString()}

`;

if(total<1000){

nivelServicio.innerHTML="Baja";

}else if(total<2500){

nivelServicio.innerHTML="Media";

}else if(total<5000){

nivelServicio.innerHTML="Alta";

}else{

nivelServicio.innerHTML="Muy Alta";

}

}

if(servicio.value==="inventario"){

let sector=document.getElementById("sector").value;

let items=parseInt(document.getElementById("items").value)||0;

let almacenes=parseInt(document.getElementById("almacenes").value)||1;

let ciudad=document.getElementById("ciudadInventario").value;

let codigo=document.getElementById("codigoBarras").value;

let horario=document.getElementById("horarioInventario").value;

let conciliacion=document.getElementById("conciliacion").value;

let puntos=0;


/* SECTOR */

switch(sector){

case "800":
puntos+=1;
break;

case "1200":
puntos+=2;
break;

case "1800":
puntos+=3;
break;

case "2500":
puntos+=4;
break;

case "3200":
puntos+=5;
break;

default:
puntos+=2;

}


/* ITEMS */

if(items<=500){

puntos+=1;

}else if(items<=2000){

puntos+=2;

}else if(items<=5000){

puntos+=3;

}else if(items<=10000){

puntos+=4;

}else{

puntos+=5;

}


/* ALMACENES */

if(almacenes==1){

puntos+=1;

}else if(almacenes<=3){

puntos+=2;

}else if(almacenes<=5){

puntos+=3;

}else{

puntos+=5;

}


/* CODIGO DE BARRAS */

if(codigo=="no"){

puntos+=2;

}


/* HORARIO */

if(horario=="nocturno"){

puntos+=2;

}

if(horario=="finsemana"){

puntos+=3;

}


/* CONCILIACION */

if(conciliacion=="si"){

puntos+=2;

}

switch (rubro) {

    case "comercio":
        motor.precioItem = 0.16;
        break;

    case "almacen":
        motor.precioItem = 0.18;
        break;

    case "retail":
        motor.precioItem = 0.20;
        break;

    case "industria":
        motor.precioItem = 0.25;
        break;

    case "construccion":
        motor.precioItem = 0.30;
        break;

    case "salud":
        motor.precioItem = 0.28;
        break;

    case "hoteleria":
        motor.precioItem = 0.18;
        break;

    case "educacion":
        motor.precioItem = 0.16;
        break;

    case "mineria":
        motor.precioItem = 0.45;
        break;

    default:
        motor.precioItem = 0.18;

}

/* PRECIO */

//let precioFinal=500+(puntos*180);

let precioBase = motor.cargoMinimo + (items * motor.precioItem);

if (almacenes > 1) {
    precioBase += (almacenes - 1) * 150;
}

if (codigoBarras === "no") {
    precioBase += 400;
}

if (ciudad !== "Cusco" && ciudad !== "") {
    precioBase += 300;
}


/* NIVEL */

let nivel="Baja";
let estrellas="★★☆☆☆";

if(puntos>=8){

nivel="Media";
estrellas="★★★☆☆";

}

if(puntos>=12){

nivel="Alta";
estrellas="★★★★☆";

}

if(puntos>=16){

nivel="Muy Alta";
estrellas="★★★★★";

}


/* EQUIPO */

let personal=2;

if(items>2000) personal=3;

if(items>5000) personal=4;

if(items>10000) personal=6;


/* TIEMPO */

let dias=1;

if(items>2000) dias=2;

if(items>5000) dias=3;

if(items>10000) dias=5;


/* RESULTADO */

precio.innerHTML = precioBase.toLocaleString();

nivelServicio.innerHTML=estrellas+" "+nivel;

resumen.innerHTML=`

<b>Servicio</b><br>
Inventario Físico

<br><br>

<b>Ciudad</b><br>
${ciudad==""?"Por definir":ciudad}

<br><br>

<b>Complejidad</b><br>
${nivel}

<br><br>

<b>Equipo recomendado</b><br>
${personal} inventaristas

<br><br>

<b>Tiempo estimado</b><br>
${dias} día(s)

<br><br>

<b>Incluye</b>

<ul>

<li>Inventario físico</li>

<li>Supervisión</li>

<li>Informe final</li>

<li>Base digital</li>

</ul>

`;

}

if(servicio.value==="contabilidad"){

let regimen=document.getElementById("regimen").value;

let comprobantes=parseInt(document.getElementById("comprobantes").value)||0;

let trabajadores=parseInt(document.getElementById("trabajadores").value)||0;

let planilla=document.getElementById("planilla").value;

let facturacion=document.getElementById("facturacion").value;

let eeff=document.getElementById("eeff").checked;

let tributaria=document.getElementById("tributaria").checked;

let sunat=document.getElementById("sunat").checked;


let puntos=0;


/* REGIMEN */

switch(regimen){

case "250":

puntos+=1;

break;

case "350":

puntos+=2;

break;

case "500":

puntos+=3;

break;

case "700":

puntos+=4;

break;

}


/* COMPROBANTES */

if(comprobantes<=50){

puntos+=1;

}else if(comprobantes<=150){

puntos+=2;

}else if(comprobantes<=300){

puntos+=3;

}else{

puntos+=4;

}


/* TRABAJADORES */

if(trabajadores==0){

puntos+=0;

}else if(trabajadores<=5){

puntos+=1;

}else if(trabajadores<=20){

puntos+=2;

}else{

puntos+=3;

}


/* PLANILLA */

if(planilla=="si"){

puntos+=2;

}


/* FACTURACION */

if(facturacion=="2"){

puntos+=1;

}

if(facturacion=="3"){

puntos+=2;

}


/* ADICIONALES */

if(eeff){

puntos++;

}

if(tributaria){

puntos++;

}

if(sunat){

puntos+=2;

}


/* PLAN */

let plan="Plan Emprendedor";

let precioPlan=350;

let incluye=[
"Registro contable",
"Declaraciones mensuales",
"Asistencia por WhatsApp"
];

if(puntos>=7){

plan="Plan Empresarial";

precioPlan=650;

incluye=[
"Registro contable",
"Libros electrónicos",
"Declaraciones mensuales",
"Asesoría tributaria",
"Soporte prioritario"
];

}

if(puntos>=12){

plan="Plan Corporativo";

precioPlan=990;

incluye=[
"Contabilidad integral",
"Estados financieros",
"Libros electrónicos",
"Asesoría tributaria",
"Atención SUNAT",
"Reuniones mensuales"
];

}


precio.innerHTML=precioPlan.toLocaleString();

nivelServicio.innerHTML=plan;

resumen.innerHTML=`

<b>Plan recomendado</b><br>
${plan}

<br><br>

<b>Precio mensual estimado</b><br>

S/ ${precioPlan.toLocaleString()}

<br><br>

<b>Servicios incluidos</b>

<ul>

${incluye.map(i=>`<li>${i}</li>`).join("")}

</ul>

`;

}

}

document.querySelectorAll("#cotizacion input,#cotizacion select").forEach(function(e){

e.addEventListener("input",calcular);

e.addEventListener("change",calcular);

});

}
/*=========================================
 ENVIAR COTIZACIÓN AL FORMULARIO
=========================================*/

document.addEventListener("DOMContentLoaded", () => {

    const boton = document.getElementById("btnCotizar");

    if (!boton) return;

    boton.addEventListener("click", function (e) {

        e.preventDefault();

        const nombre = document.getElementById("nombre");
        const empresa = document.getElementById("empresa");
        const correo = document.getElementById("correo");
        const mensaje = document.getElementById("mensaje");

        const codigo = document.getElementById("codigoCotizacion").innerText;
        const servicio = document.getElementById("servicio").options[
            document.getElementById("servicio").selectedIndex
        ].text;

        const precio = document.getElementById("precio").innerText;
        const nivel = document.getElementById("nivelServicio").innerText;
        const resumen = document.getElementById("resumen").innerText;

        mensaje.value =
`Hola, me gustaría solicitar una cotización.

Código:
${codigo}

Servicio:
${servicio}

Precio estimado:
S/ ${precio}

Nivel:
${nivel}

Resumen:

${resumen}

Agradecería recibir una propuesta formal.

Muchas gracias.`;

        document.getElementById("contacto").scrollIntoView({

            behavior: "smooth"

        });

        setTimeout(() => {

            if(nombre.value===""){

                nombre.focus();

            }else if(empresa && empresa.value===""){

                empresa.focus();

            }else if(correo.value===""){

                correo.focus();

            }

        },600);

    });

});

/*==================================================
    COTIZADOR HUMEN SOLUTIONS V3
==================================================*/

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

    if (this.servicioActual === "reclutamiento") {

    this.contenedor.innerHTML = `

        <h3>Reclutamiento y Selección</h3>

        <label>Nivel del puesto</label>

        <select id="nivelPuesto">

            <option value="">Seleccione...</option>

            <option value="Operativo">Operativo</option>

            <option value="Tecnico">Técnico</option>

            <option value="Administrativo">Administrativo</option>

            <option value="Analista">Analista</option>

            <option value="Supervisor">Supervisor</option>

            <option value="Coordinador">Coordinador</option>

            <option value="Jefatura">Jefatura</option>

            <option value="Gerencia">Gerencia</option>

            <option value="Direccion">Dirección</option>

        </select>

        <label>Nombre del puesto</label>

        <input
            type="text"
            id="puesto"
            placeholder="Ejemplo: Asistente Contable">

        <label>Cantidad de vacantes</label>

        <input
            type="number"
            id="vacantes"
            min="1"
            value="1">

        <label>Sueldo mensual (S/)</label>

        <input
            type="number"
            id="sueldo"
            min="0">

        <label>Urgencia del proceso</label>

        <select id="urgencia">

            <option value="normal">Normal</option>

            <option value="urgente">Urgente</option>

            <option value="muyUrgente">Muy urgente</option>

        </select>

        <button id="btnCalcular">

            Calcular cotización

        </button>

    `;

    document
        .getElementById("btnCalcular")
        .addEventListener("click", () => {

            this.calcularReclutamiento();

        });

}

    if (this.servicioActual === "inventario") {

    this.contenedor.innerHTML = `
        <h3>Inventario Físico</h3>

        <label>Rubro de la empresa</label>

<select id="rubro">

    <option value="">Seleccione...</option>

    <option value="comercio">Comercio</option>

    <option value="almacen">Almacén Logístico</option>

    <option value="retail">Retail</option>

    <option value="industria">Industria</option>

    <option value="construccion">Construcción</option>

    <option value="salud">Salud</option>

    <option value="hoteleria">Hotelería</option>

    <option value="educacion">Educación</option>

    <option value="mineria">Minería</option>

</select>

        <label>Cantidad de ítems</label>
        <input
            type="number"
            id="items"
            min="1"
            placeholder="Ejemplo: 3500">

        <label>Cantidad de almacenes</label>
        <input
            type="number"
            id="almacenes"
            value="1"
            min="1">

        <label>Ciudad</label>

        <select id="ciudad">
            <option value="">Seleccione...</option>
            <option>Cusco</option>
            <option>Lima</option>
            <option>Arequipa</option>
            <option>Otra ciudad</option>
        </select>

        <label>¿Los productos tienen código de barras?</label>

        <select id="codigoBarras">
            <option value="si">Sí</option>
            <option value="no">No</option>
        </select>

        <button id="btnCalcularInventario">
            Calcular
        </button>
    `;

    document
        .getElementById("btnCalcularInventario")
        .addEventListener("click", () => {

            this.calcularInventario();

        });

}

    if (this.servicioActual === "contabilidad") {

    this.contenedor.innerHTML = `
        <h3>Servicio Contable</h3>

        <label>Régimen Tributario</label>
        <select id="regimen">
            <option value="">Seleccione...</option>
            <option value="RUS">Nuevo RUS</option>
            <option value="RER">Régimen Especial (RER)</option>
            <option value="MYPE">Régimen MYPE</option>
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

        <label>¿Incluye planillas?</label>
        <select id="planillas">
            <option value="no">No</option>
            <option value="si">Sí</option>
        </select>

        <button id="btnCalcularContabilidad">
            Calcular
        </button>
    `;

    document
        .getElementById("btnCalcularContabilidad")
        .addEventListener("click", () => {

            this.calcularContabilidad();

        });

}

},

calcularReclutamiento() {

    const nivel = document.getElementById("nivelPuesto").value;

    const urgencia = document.getElementById("urgencia").value;

    const puesto = document.getElementById("puesto").value;

    const vacantes = Number(document.getElementById("vacantes").value);

    const sueldo = Number(document.getElementById("sueldo").value);

    const motor = {

    factorNivel: 1,

    factorVacantes: 1,

    factorSueldo: 1,

    factorUrgencia: 0,

    complejidad: "Baja",

    dias: 7,

    reclutadores: 1,

    garantia: 30,

    diagnostico: [],

    recomendaciones: []

};

switch (nivel) {

    case "Operativo":

    motor.factorNivel = 1.00;

    motor.diagnostico.push(
        "El puesto es operativo, por lo que el proceso de búsqueda es de baja complejidad."
    );

    break;

    case "Tecnico":

        motor.factorNivel = 1.10;

        motor.diagnostico.push(
    "El puesto requiere conocimientos técnicos específicos."
);

break;

    case "Administrativo":

        motor.factorNivel = 1.15;

        motor.diagnostico.push(
    "El perfil administrativo requiere validar experiencia y competencias."
);
        break;

    case "Analista":

        motor.factorNivel = 1.30;

        motor.diagnostico.push(
    "El nivel analista demanda una evaluación más detallada del perfil."
);
        break;

    case "Supervisor":

        motor.factorNivel = 1.50;

        motor.diagnostico.push(
    "El cargo de supervisión requiere evaluar liderazgo y experiencia."
);
        break;

    case "Coordinador":

        motor.factorNivel = 1.70;

        motor.diagnostico.push(
    "El puesto de coordinación exige experiencia en gestión de equipos."
);
        break;

    case "Jefatura":

        motor.factorNivel = 2.00;

        motor.diagnostico.push(
    "El proceso corresponde a una jefatura y requiere una evaluación especializada."
);
        break;

    case "Gerencia":

        motor.factorNivel = 2.50;

        motor.diagnostico.push(
    "La búsqueda gerencial requiere un proceso ejecutivo y mayor nivel de validación."
);
        break;

    case "Direccion":

        motor.factorNivel = 3.20;

        motor.diagnostico.push(
    "La selección para un cargo directivo implica un proceso altamente estratégico."
);
        break;

}

if (vacantes == 1) {

    motor.factorVacantes = 1;

    motor.diagnostico.push(
    "Se solicita cubrir una única vacante."
);

}
else if (vacantes <= 3) {

    motor.factorVacantes = 1.8;

    motor.diagnostico.push(
    "El proceso contempla varias vacantes similares."
);

}
else if (vacantes <= 6) {

    motor.factorVacantes = 2.5;

    motor.diagnostico.push(
    "El número de vacantes incrementa el esfuerzo de búsqueda y entrevistas."
);

}
else if (vacantes <= 10) {

    motor.factorVacantes = 3.2;

    motor.diagnostico.push(
    "Se requiere una estrategia de reclutamiento masivo."
);

}
else {

    motor.factorVacantes = 4 + ((vacantes - 10) * 0.50);

    motor.diagnostico.push(
        `El proceso contempla ${vacantes} vacantes y requiere un equipo dedicado de reclutamiento.`
    );

}

if (sueldo <= 1500) {

    motor.factorSueldo = 1;

    motor.diagnostico.push(
        "El rango salarial corresponde a un perfil de baja especialización."
    );

}
else if (sueldo <= 2500) {

    motor.factorSueldo = 1.15;

    motor.diagnostico.push(
        "El salario indica un perfil con experiencia intermedia."
    );

}
else if (sueldo <= 4000) {

    motor.factorSueldo = 1.35;

    motor.diagnostico.push(
        "El perfil requiere una búsqueda más especializada."
    );

}
else if (sueldo <= 6000) {

    motor.factorSueldo = 1.60;

    motor.diagnostico.push(
        "El salario corresponde a un puesto de mayor responsabilidad."
    );

}
else {

    motor.factorSueldo = 2;

    motor.diagnostico.push(
        "El nivel salarial corresponde a un perfil altamente especializado o ejecutivo."
    );

}

switch (urgencia) {

    case "normal":

    motor.factorUrgencia = 0;

    motor.diagnostico.push(
        "El proceso se desarrollará dentro de los tiempos habituales de reclutamiento."
    );

    break;

    case "urgente":

    motor.factorUrgencia = 0.20;

    motor.diagnostico.push(
        "Se requiere acelerar la búsqueda de candidatos para cumplir el plazo solicitado."
    );

    break;

    case "muyUrgente":

    motor.factorUrgencia = 0.40;

    motor.diagnostico.push(
        "La alta urgencia exige dedicar más recursos y priorizar este proceso."
    );

    break;

}

let puntos = 0;

puntos += motor.factorNivel;

puntos += motor.factorVacantes;

puntos += motor.factorSueldo;

puntos += motor.factorUrgencia * 5;


if (puntos < 4) {

    motor.complejidad = "Baja";

}

else if (puntos < 6) {

    motor.complejidad = "Media";

}
else if (puntos < 8) {

    motor.complejidad = "Alta";

}
else {

    motor.complejidad = "Crítica";

}

switch (motor.complejidad) {

    case "Baja":

        motor.dias = 12;

        motor.reclutadores = 1;

        motor.garantia = 30;

        motor.recomendaciones.push(
        "El proceso puede ser gestionado por un reclutador."
    );

    motor.recomendaciones.push(
        "El plazo estimado permite realizar una búsqueda ordenada."
    );

    motor.recomendaciones.push(
        "La garantía de 30 días cubre posibles reemplazos."
    );

        break;

    case "Media":

    motor.dias = 12;

    motor.reclutadores = 1;

    motor.garantia = 30;

    motor.recomendaciones.push(
        "Se recomienda ampliar las fuentes de reclutamiento."
    );

    motor.recomendaciones.push(
        "Un reclutador puede gestionar el proceso completo."
    );

    motor.recomendaciones.push(
        "La garantía recomendada es de 45 días."
    );

    break;

    case "Alta":

    motor.dias = 18;

    motor.reclutadores = 2;

    motor.garantia = 30;

    motor.recomendaciones.push(
        "Se recomienda asignar dos reclutadores para cumplir el plazo."
    );

    motor.recomendaciones.push(
        "El proceso requiere una evaluación técnica más profunda."
    );

    motor.recomendaciones.push(
        "La garantía de 60 días reduce el riesgo de reposición."
    );

    break;

    case "Crítica":

    motor.dias = 25;

    motor.reclutadores = 3;

    motor.garantia = 30;

    motor.recomendaciones.push(
        "Se recomienda un equipo especializado de tres reclutadores."
    );

    motor.recomendaciones.push(
        "Es conveniente realizar seguimiento continuo al proceso."
    );

    motor.recomendaciones.push(
        "La garantía de 90 días brinda mayor seguridad al cliente."
    );

    break;

}

// Ajustar el tiempo según la urgencia

switch (urgencia) {

    case "urgente":

        motor.dias = Math.max(3, motor.dias - 2);

        break;

    case "muyUrgente":

        motor.dias = Math.max(2, motor.dias - 5);

        break;

}

    if (

    nivel === "" ||

    puesto === "" ||

    vacantes <= 0 ||

    sueldo <= 0

){

    alert("Completa todos los datos.");

    return;

}

    const tarifaBase = 450;

    let total = tarifaBase;

    total *= motor.factorNivel;

    total *= motor.factorVacantes;

    total *= motor.factorSueldo;

    total += total * motor.factorUrgencia;

    const garantia60 = total * 1.10;
const garantia90 = total * 1.20;

const listaDiagnostico = motor.diagnostico
    .map(item => `• ${item}<br>`)
    .join("");

const listaRecomendaciones = motor.recomendaciones
    .map(item => `✓ ${item}<br>`)
    .join("");

    const detalle = `

<strong>Servicio:</strong> Reclutamiento y Selección<br><br>

<strong>Puesto:</strong> ${puesto}<br>

<strong>Nivel:</strong> ${nivel}<br>

<strong>Vacantes:</strong> ${vacantes}<br>

<strong>Sueldo:</strong> S/ ${sueldo.toLocaleString("es-PE")}<br><br>

<strong>Diagnóstico del proceso</strong><br>

${listaDiagnostico}

<br>

<strong>Resultado del análisis</strong><br>

• Complejidad: ${motor.complejidad}<br>

• Tiempo estimado: ${motor.dias} días<br>

• Equipo recomendado: ${motor.reclutadores} reclutador(es)<br>

• Garantía de reposición incluida: ${motor.garantia} días<br>

<div style="
    margin:12px 0 18px;
    padding:14px 16px;
    background:rgba(255,255,255,.08);
    border-left:4px solid #00C896;
    border-radius:8px;
    color:#EAF6FF;
    font-size:14px;
    line-height:1.7;
">

<strong style="color:#FFFFFF;">
🛡️ Amplía tu garantía de reposición
</strong>

<br><br>

✔ Garantía incluida:
<strong>${motor.garantia} días</strong>

<br><br>

○ Garantía Extendida:
<strong>60 días</strong>

(+10%)

<br>

<strong>
S/ ${garantia60.toLocaleString("es-PE",{
minimumFractionDigits:2
})}
</strong>

<br><br>

○ Garantía Premium:
<strong>90 días</strong>

(+20%)

<br>

<strong>
S/ ${garantia90.toLocaleString("es-PE",{
minimumFractionDigits:2
})}
</strong>

<br><br>

<small style="opacity:.85;">
El precio mostrado corresponde al valor total del servicio con la garantía ampliada incluida.
</small>

</div>

<strong>Recomendaciones</strong><br>

${listaRecomendaciones}

`;

this.mostrarResultado(total, detalle);

},

calcularInventario() {

    const rubro = document.getElementById("rubro").value;

    const items = Number(document.getElementById("items").value);

    const almacenes = Number(document.getElementById("almacenes").value);

    const ciudad = document.getElementById("ciudad").value;

    const codigo = document.getElementById("codigoBarras").value;

    const motor = {

    precioBase: 600,

    precioFinal: 600,

    puntos: 0,

    complejidad: "Baja",

    inventaristas: 1,

    dias: 1,

    diagnostico: [],

    recomendaciones: [],

    precioItem: 0,

    cargoMinimo: 500,

    precioItem: 0,

    cargoMinimo: 500,

    subtotalItems:0,

    costoAlmacenes:0,

    costoCodigo:0,

    costoViaticos:0

};

    if (
        items <= 0 ||
        almacenes <= 0 ||
        ciudad === ""
    ) {
        alert("Completa todos los datos.");
        return;
    }

switch (rubro) {

    case "comercio":
        motor.precioItem = 0.16;
        break;

    case "almacen":
        motor.precioItem = 0.18;
        break;

    case "retail":
        motor.precioItem = 0.20;
        break;

    case "industria":
        motor.precioItem = 0.25;
        break;

    case "construccion":
        motor.precioItem = 0.30;
        break;

    case "salud":
        motor.precioItem = 0.28;
        break;

    case "hoteleria":
        motor.precioItem = 0.18;
        break;

    case "educacion":
        motor.precioItem = 0.16;
        break;

    case "mineria":
        motor.precioItem = 0.45;
        break;

    default:
        motor.precioItem = 0.18;

}

    // Precio según cantidad de ítems
    if (items <= 1000) {

    motor.subtotalItems = items * motor.precioItem;

motor.precioBase =
    motor.cargoMinimo + motor.subtotalItems;

    motor.puntos += 1;

    motor.diagnostico.push(
        "El volumen de hasta 1,000 ítems corresponde a un inventario de baja complejidad."
    );
    motor.recomendaciones.push(
    "El inventario puede ejecutarse con un solo equipo de trabajo."
);

} else if (items <= 5000) {

    motor.subtotalItems = items * motor.precioItem;

motor.precioBase =
    motor.cargoMinimo + motor.subtotalItems;

    motor.puntos += 2;

    motor.diagnostico.push(
        "La cantidad de ítems requiere una planificación operativa para optimizar el conteo."
    );
    motor.recomendaciones.push(
    "Se recomienda planificar previamente la distribución de los productos por zonas."
);

} else if (items <= 10000) {

    motor.subtotalItems = items * motor.precioItem;

motor.precioBase =
    motor.cargoMinimo + motor.subtotalItems;

    motor.puntos += 3;

    motor.diagnostico.push(
        "El volumen de ítems demanda un equipo de trabajo más amplio y mayor tiempo de ejecución."
    );
    motor.recomendaciones.push(
    "Es recomendable dividir el inventario por áreas para optimizar los tiempos."
);

} else {

    motor.subtotalItems = items * motor.precioItem;

motor.precioBase =
    motor.cargoMinimo + motor.subtotalItems;

    motor.puntos += 4;

    motor.diagnostico.push(
        "El inventario corresponde a una operación de alta complejidad por el elevado volumen de ítems."
    );
    motor.recomendaciones.push(
    "Se recomienda ejecutar el inventario con varios equipos de trabajo y un supervisor general."
);

}

    // Almacenes adicionales

if (almacenes == 1) {

    motor.puntos += 1;

    motor.diagnostico.push(
        "Todos los productos se encuentran en un solo almacén, facilitando la ejecución del inventario."
    );

}

else {

    motor.costoAlmacenes = (almacenes - 1) * 150;

motor.precioBase += motor.costoAlmacenes;

    motor.puntos += 2;

    motor.diagnostico.push(
        `El inventario se distribuirá en ${almacenes} almacenes, lo que incrementa el tiempo de coordinación y desplazamiento del equipo.`
    );

}

    // Código de barras
if (codigo === "si") {

    motor.puntos += 1;

    motor.diagnostico.push(
        "Los productos cuentan con código de barras, lo que agiliza el conteo y mejora la precisión del inventario."
    );

} else {

    motor.costoCodigo = 400;

motor.precioBase += motor.costoCodigo;

    motor.puntos += 2;

    motor.diagnostico.push(
        "Los productos no cuentan con código de barras, por lo que el conteo será manual y demandará mayor tiempo de ejecución."
    );

}

    // Viáticos
if (ciudad === "Cusco") {

    motor.puntos += 1;

    motor.diagnostico.push(
        "El servicio se realizará en Cusco, por lo que no se consideran viáticos ni costos adicionales de desplazamiento."
    );

} else {

    motor.costoViaticos = 300;

motor.precioBase += motor.costoViaticos;

    motor.puntos += 2;

    motor.diagnostico.push(
        `El servicio se realizará en ${ciudad}, por lo que se consideran viáticos y costos de desplazamiento del equipo.`
    );

}

if (motor.puntos <= 4) {

    motor.complejidad = "Baja";

} else if (motor.puntos <= 6) {

    motor.complejidad = "Media";

} else if (motor.puntos <= 8) {

    motor.complejidad = "Alta";

} else {

    motor.complejidad = "Crítica";

}

switch (motor.complejidad) {

    case "Baja":

        motor.inventaristas = 1;
        motor.dias = Math.ceil(items / 1800);

        motor.recomendaciones.push(
            "El inventario puede ejecutarse con un solo inventarista."
        );

        break;

    case "Media":

        motor.inventaristas = 2;
        motor.dias = Math.ceil(items / 3600);

        motor.recomendaciones.push(
            "Se recomienda trabajar con dos inventaristas para optimizar los tiempos."
        );

        break;

    case "Alta":

        motor.inventaristas = 3;
        motor.dias = Math.ceil(items / 5400);

        motor.recomendaciones.push(
            "Es recomendable asignar un supervisor y dividir el inventario por zonas."
        );

        break;

    case "Crítica":

        motor.inventaristas = 5;
        motor.dias = Math.ceil(items / 9000);

        motor.recomendaciones.push(
            "Se recomienda formar varios equipos de trabajo con un coordinador general."
        );

        break;

}

if (motor.dias < 1) {

    motor.dias = 1;

}

motor.precioFinal = motor.precioBase;

const listaDiagnostico = motor.diagnostico
    .map(item => `• ${item}<br>`)
    .join("");

const listaRecomendaciones = motor.recomendaciones
    .map(item => `✓ ${item}<br>`)
    .join("");    

    const detalle = `
<strong>Servicio:</strong> Inventario Físico<br>

<strong>Ítems:</strong> ${items.toLocaleString("es-PE")}<br>

<strong>Almacenes:</strong> ${almacenes}<br>

<strong>Ciudad:</strong> ${ciudad}<br>

<strong>Código de barras:</strong> ${codigo === "si" ? "Sí" : "No"}<br><br>

<hr>

<h3 style="margin:12px 0 8px;color:#FFFFFF;">
💰 Análisis Económico
</h3>

<table style="width:100%;border-collapse:collapse;font-size:15px">

<tr>
<td>Cargo mínimo</td>
<td style="text-align:right">
S/ ${motor.cargoMinimo.toLocaleString("es-PE",{minimumFractionDigits:2})}
</td>
</tr>

<tr>
<td>Subtotal por ítems</td>
<td style="text-align:right">
S/ ${motor.subtotalItems.toLocaleString("es-PE",{minimumFractionDigits:2})}
</td>
</tr>

<tr>
<td>Tarifa por ítem</td>
<td style="text-align:right">
S/ ${motor.precioItem.toFixed(2)}
</td>
</tr>

<tr>
<td>Almacenes adicionales</td>
<td style="text-align:right">
S/ ${motor.costoAlmacenes.toLocaleString("es-PE",{minimumFractionDigits:2})}
</td>
</tr>

<tr>
<td>Conteo manual</td>
<td style="text-align:right">
S/ ${motor.costoCodigo.toLocaleString("es-PE",{minimumFractionDigits:2})}
</td>
</tr>

<tr>
<td>Viáticos</td>
<td style="text-align:right">
S/ ${motor.costoViaticos.toLocaleString("es-PE",{minimumFractionDigits:2})}
</td>
</tr>

<tr style="font-size:18px;font-weight:bold;border-top:2px solid rgba(255,255,255,.35)">

<td>Total estimado</td>

<td style="text-align:right;color:#FFFFFF">

S/ ${motor.precioFinal.toLocaleString("es-PE",{minimumFractionDigits:2})}

</td>

</tr>

</table>

<br>

<strong>Diagnóstico del proceso</strong><br>

${listaDiagnostico}

<br>

<strong>Complejidad del servicio:</strong> ${motor.complejidad}<br>

<strong>Equipo recomendado:</strong> ${motor.inventaristas} inventarista(s)<br>

<strong>Duración estimada:</strong> ${motor.dias} día(s)<br><br>

<strong>Recomendaciones</strong><br>

${listaRecomendaciones}

<br>

<strong>Incluye:</strong>

<ul>
<li>Conteo físico</li>
<li>Conciliación básica</li>
<li>Reporte final</li>
</ul>
`;

    this.mostrarResultado(
    motor.precioFinal,
    detalle
);

},

calcularContabilidad() {

    const regimen = document.getElementById("regimen").value;

    const comprobantes = Number(document.getElementById("comprobantes").value);

    const trabajadores = Number(document.getElementById("trabajadores").value);

    const planillas = document.getElementById("planillas").value;

    const motor = {

    precioBase: 0,

    precioFinal: 0,

    puntos: 0,

    complejidad: "Baja",

    plan: "Emprendedor",

    diagnostico: [],

    recomendaciones: []

};

    if (regimen === "" || comprobantes < 0 || trabajadores < 0) {

        alert("Completa todos los datos.");

        return;

    }

    // Precio base según régimen
    switch (regimen) {

        case "RUS":
            motor.precioBase = 180;
motor.puntos += 1;

motor.diagnostico.push(
    "El negocio pertenece al Nuevo RUS, por lo que sus obligaciones contables son básicas."
);
            break;

        case "RER":
            motor.precioBase = 280;
motor.puntos += 2;

motor.diagnostico.push(
    "El Régimen Especial requiere un mayor control tributario y contable."
);
            break;

        case "MYPE":
            motor.precioBase = 450;
motor.puntos += 3;

motor.diagnostico.push(
    "El Régimen MYPE demanda un seguimiento contable más completo."
);
            break;

        case "GENERAL":
            motor.precioBase = 700;
motor.puntos += 4;

motor.diagnostico.push(
    "El Régimen General implica una gestión contable y tributaria de mayor complejidad."
);
            break;

    }

    // Incremento por comprobantes
    if (comprobantes <= 50) {

    motor.puntos += 1;

    motor.diagnostico.push(
        "El volumen mensual de comprobantes es bajo y puede administrarse fácilmente."
    );

} else if (comprobantes <= 150) {

    motor.puntos += 2;

    motor.precioBase += 40;

    motor.diagnostico.push(
        "El volumen de comprobantes requiere una dedicación contable intermedia."
    );

} else if (comprobantes <= 300) {

    motor.puntos += 3;

    motor.precioBase += 120;

    motor.diagnostico.push(
        "La empresa presenta un movimiento contable importante durante el mes."
    );

} else {

    motor.puntos += 4;

    motor.precioBase += 240;

    motor.diagnostico.push(
        "El alto volumen de comprobantes exige un mayor tiempo de registro y revisión."
    );

}

    // Incremento por trabajadores
    if (trabajadores === 0) {

    motor.puntos += 0;

    motor.diagnostico.push(
        "La empresa no cuenta con trabajadores en planilla."
    );

} else if (trabajadores <= 5) {

    motor.puntos += 1;

    motor.precioBase += trabajadores * 20;

    motor.diagnostico.push(
        "La empresa cuenta con una planilla pequeña de hasta 5 trabajadores."
    );

} else if (trabajadores <= 20) {

    motor.puntos += 2;

    motor.precioBase += trabajadores * 20;

    motor.diagnostico.push(
        "La planilla requiere un control periódico de obligaciones laborales."
    );

} else {

    motor.puntos += 3;

    motor.precioBase += trabajadores * 20;

    motor.diagnostico.push(
        "La empresa administra una planilla amplia que demanda mayor dedicación y control."
    );

}

    // Administración de planillas
    if (planillas === "si") {

    motor.precioBase += 120;

    motor.puntos += 2;

    motor.diagnostico.push(
        "La empresa requiere la administración de planillas y obligaciones laborales."
    );

} else {

    motor.puntos += 0;

    motor.diagnostico.push(
        "El servicio no incluye administración de planillas."
    );

}

if (motor.puntos <= 3) {

    motor.complejidad = "Básica";

} else if (motor.puntos <= 6) {

    motor.complejidad = "Intermedia";

} else if (motor.puntos <= 9) {

    motor.complejidad = "Avanzada";

} else {

    motor.complejidad = "Corporativa";

}

let incluye = [];

switch (motor.complejidad) {

    case "Básica":

        motor.plan = "Plan Emprendedor";
        motor.precioFinal = motor.precioBase;

        motor.recomendaciones.push(
            "Este plan es ideal para pequeñas empresas con operaciones sencillas."
        );

        incluye = [
            "Registro contable",
            "Declaraciones mensuales",
            "Asistencia por WhatsApp"
        ];

        break;

    case "Intermedia":

        motor.plan = "Plan Empresarial";
        motor.precioFinal = motor.precioBase + 150;

        motor.recomendaciones.push(
            "Se recomienda un seguimiento contable mensual y asesoría tributaria."
        );

        incluye = [
            "Registro contable",
            "Libros electrónicos",
            "Declaraciones mensuales",
            "Asesoría tributaria"
        ];

        break;

    case "Avanzada":

        motor.plan = "Plan Avanzado";
        motor.precioFinal = motor.precioBase + 350;

        motor.recomendaciones.push(
            "La empresa requiere un mayor control de sus procesos contables y laborales."
        );

        incluye = [
            "Contabilidad integral",
            "Libros electrónicos",
            "Estados financieros",
            "Asesoría tributaria",
            "Soporte prioritario"
        ];

        break;

    case "Corporativa":

        motor.plan = "Plan Corporativo";
        motor.precioFinal = motor.precioBase + 600;

        motor.recomendaciones.push(
            "Se recomienda un servicio contable integral con acompañamiento permanente."
        );

        incluye = [
            "Contabilidad integral",
            "Estados financieros",
            "Libros electrónicos",
            "Planeamiento tributario",
            "Atención SUNAT",
            "Reuniones mensuales"
        ];

        break;

}
const listaDiagnostico = motor.diagnostico
    .map(item => `• ${item}<br>`)
    .join("");

const listaRecomendaciones = motor.recomendaciones
    .map(item => `✓ ${item}<br>`)
    .join("");

    const detalle = `

<strong>Servicio:</strong> Contabilidad Mensual<br><br>

<strong>Diagnóstico</strong><br>

${listaDiagnostico}

<br>

<strong>Resultado del análisis</strong><br>

• Complejidad: ${motor.complejidad}<br>

• Plan recomendado: ${motor.plan}<br>

• Precio estimado: S/ ${motor.precioFinal.toLocaleString("es-PE")}<br>

<br>

<strong>Recomendaciones</strong><br>

${listaRecomendaciones}

<br>

<strong>Servicios incluidos</strong>

<ul>

${incluye.map(item => `<li>${item}</li>`).join("")}

</ul>

`;

    this.mostrarResultado(motor.precioFinal, detalle);

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

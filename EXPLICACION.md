# TaskControl explicado paso a paso

Este documento explica **cómo está hecho TaskControl** para alguien que está aprendiendo a programar.
Como el proyecto es grande (unas 10 700 líneas), la explicación está dividida en varios documentos:
este es el **índice general**, y cada módulo tiene el suyo dentro de la carpeta [`explicacion/`](explicacion/).

## Índice

| # | Documento | De qué trata |
|---|---|---|
| 0 | **Este documento** | Qué hace el proyecto, mapa de carpetas, cómo se conectan las partes y glosario |
| 1 | [Arranque y configuración](explicacion/01-arranque-y-configuracion.md) | `manage.py`, `.env`, `requirements.txt` y la carpeta `gestion_campo/` (el "cerebro" de Django) |
| 2 | [Cuentas](explicacion/02-cuentas.md) | Empresas, usuarios, roles, inicio de sesión y permisos |
| 3 | [Configuración de servicios](explicacion/03-configuracion.md) | Tipos de servicio y plantillas de lista de verificación |
| 4 | [Tareas](explicacion/04-tareas.md) | Órdenes de trabajo, lista de verificación y cómo se prueban las reglas |
| 5 | [Entregas](explicacion/05-entregas.md) | El empleado entrega fotos; el administrador aprueba o devuelve |
| 6 | [Viáticos](explicacion/06-viaticos.md) | Dinero para el trabajo de campo: solicitud, anticipo, gastos y liquidación |
| 7 | [Historial y notificaciones](explicacion/07-historial.md) | Bitácora de cambios y avisos a los usuarios |
| 8 | [Reportes](explicacion/08-reportes.md) | Panel de indicadores, reportes por período y exportación CSV |
| 9 | [Frontend: base](explicacion/09-frontend-base.md) | Configuración de React/Vite, cliente de la API, sesión, armazones y componentes |
| 10 | [Frontend: pantallas](explicacion/10-frontend-pantallas.md) | Cada pantalla del empleado y del administrador |

> **Cómo leer los fragmentos de código.** En cada documento verás un bloque de código y, justo debajo,
> una lista donde cada punto toma una línea (o un par de líneas muy relacionadas) y explica qué hace.

---

## 1. ¿Qué hace el proyecto?

TaskControl es una aplicación web para **empresas de servicios de campo**: empresas cuyos técnicos salen a
hacer trabajos fuera de la oficina (instalar aires acondicionados, limpiar oficinas, reparar bombas de agua…).

Tiene dos tipos de usuario:

- **Administrador** (trabaja en la oficina, con computadora):
  - crea **tareas** (órdenes de trabajo) y se las asigna a un empleado;
  - revisa las **entregas** (las fotos y la lista de verificación que manda el empleado) y las **aprueba** o las **devuelve** para que se corrijan;
  - autoriza **viáticos** (dinero para gastos del trabajo: combustible, peajes, comida…), entrega anticipos, revisa los comprobantes y **liquida** (calcula quién le debe a quién);
  - ve un **panel** con indicadores, **reportes** y el **historial** de todo lo que pasó.
- **Empleado** (trabaja en la calle, con el teléfono):
  - ve **sus tareas**, marca la **lista de verificación** y sube **fotos como evidencia**;
  - solicita **viáticos** y registra cada **gasto** con la foto del comprobante;
  - recibe **notificaciones** cuando le asignan algo o le aprueban/devuelven algo.

### Las 8 reglas de negocio

Todo el código gira alrededor de estas reglas (aparecen citadas en los comentarios como "regla 1", "regla 5", etc.):

1. Una tarea pasa a **COMPLETADA** solo cuando un administrador **aprueba** la entrega.
2. Para pedir revisión, el empleado debe tener **todos los ítems obligatorios marcados** y **al menos 1 foto**.
3. **Devolver** una entrega, **rechazar** un viático o **rechazar** un gasto exige escribir una **observación**.
4. Cada devolución hace que el empleado presente una **nueva versión** de la entrega; nunca se borran versiones ni fotos.
5. El empleado **solo ve lo suyo**; el administrador ve **lo de su empresa** (nunca lo de otra empresa).
6. **Saldo = gastos aprobados − anticipo.** Si es mayor que 0, la empresa le reembolsa al empleado; si es menor, el empleado devuelve; si es 0, queda saldado. No se puede liquidar si hay gastos sin revisar.
7. El **anticipo no puede ser mayor** que el monto aprobado.
8. **Todo cambio de estado** queda anotado en el **historial**.

---

## 2. Tecnologías usadas

| Parte | Tecnología | Para qué |
|---|---|---|
| Backend (servidor) | **Python 3.12** + **Django 5.2** | Lógica del negocio, base de datos, seguridad |
| API | **Django REST Framework (DRF)** | Convierte los datos a JSON para que React los use |
| Base de datos | **SQLite** | Un archivo (`db.sqlite3`) donde se guarda todo |
| Imágenes | **Pillow** | Revisar y achicar las fotos que suben los usuarios |
| Frontend (lo que ves) | **React 19** + **TypeScript** | Las pantallas |
| Empaquetador | **Vite** | Servidor de desarrollo y compilación del frontend |
| Estilos | **Tailwind CSS v4** + `index.css` | Colores, tamaños y diseño responsivo |
| Gestor de paquetes | **pnpm** | Instalar las librerías de JavaScript |

---

## 3. Mapa del proyecto

```text
TaskControl/
├── manage.py                 ← programa para manejar Django (migrar, correr el servidor, probar)
├── requirements.txt          ← librerías de Python que hay que instalar
├── .env.example              ← plantilla de la configuración secreta (.env)
├── .gitignore                ← archivos que Git no debe subir
├── README.md                 ← cómo instalar y arrancar
├── CLAUDE.md                 ← reglas y convenciones del proyecto
├── EXPLICACION.md            ← este documento
├── explicacion/              ← un documento por módulo
│
├── gestion_campo/            ← el "proyecto" Django: configuración, rutas y piezas comunes
├── cuentas/                  ← app: empresas, usuarios, sesión
├── configuracion/            ← app: tipos de servicio y plantillas de checklist
├── tareas/                   ← app: tareas y lista de verificación
├── entregas/                 ← app: entregas, fotos y revisiones
├── viaticos/                 ← app: viáticos, gastos y liquidaciones
├── historial/                ← app: historial (bitácora) y notificaciones
├── reportes/                 ← app: panel, reportes y CSV
│
├── frontend/                 ← la aplicación React (todo lo que se ve en pantalla)
│   ├── package.json          ← dependencias y comandos (pnpm dev:todo, pnpm build…)
│   ├── vite.config.ts        ← configuración de Vite
│   ├── scripts/              ← scripts para preparar y arrancar todo con un comando
│   └── src/
│       ├── main.tsx          ← punto de entrada de React
│       ├── App.tsx           ← todas las rutas (qué pantalla va en cada URL)
│       ├── index.css         ← estilos
│       ├── lib/              ← utilidades: hablar con la API, sesión, formatos
│       ├── layouts/          ← armazones: escritorio (admin) y teléfono (empleado)
│       ├── components/       ← piezas reutilizables (botones, íconos, insignias…)
│       └── pages/            ← pantallas (admin/, empleado/ y compartidas)
│
└── docs/uml/                 ← diagramas UML en formato PlantUML
```

### Estructura de una "app" de Django

Las siete carpetas del backend (`cuentas`, `tareas`, …) siguen el mismo molde. Conocerlo ayuda a orientarse:

| Archivo | Para qué sirve |
|---|---|
| `models.py` | **Modelos**: las tablas de la base de datos y los métodos que cambian su estado (`aprobar()`, `liquidar()`…) |
| `api.py` | **Vistas de la API**: reciben la petición de React, revisan permisos, llaman al modelo y responden JSON |
| `urls_api.py` | **Rutas**: qué URL (`/api/tareas/…`) va a qué vista |
| `forms.py` | **Formularios**: validan datos que llegan como archivo (fotos, comprobantes) o filtros |
| `admin.py` | Configuración del **panel de administración de Django** (`/admin/`), para el superusuario |
| `apps.py` | Registro de la app en Django (lo genera Django; casi nunca se toca) |
| `migrations/` | **Migraciones**: instrucciones para crear/modificar las tablas. Las genera Django con `makemigrations` |
| `tests.py` | **Pruebas automáticas**: verifican que las reglas se cumplan |
| `__init__.py` | Archivo vacío que le dice a Python "esta carpeta es un paquete" |

---

## 4. ¿Cómo se conectan las partes?

### 4.1 La idea principal

```text
  Navegador (React)                     Servidor (Django)                       Base de datos
 ┌──────────────────┐   petición HTTP   ┌───────────────────────────────┐        ┌───────────┐
 │ Pantalla         │ ───────────────▶  │ urls.py → api.py (vista)      │        │           │
 │ (pages/*.tsx)    │   /api/...        │   1. ¿tiene permiso?          │  ORM   │ db.sqlite3│
 │   usa lib/api.ts │                   │   2. llama al modelo          │ ─────▶ │  (tablas) │
 │                  │ ◀───────────────  │      (models.py: aprobar()…)  │ ◀───── │           │
 │ muestra los datos│   respuesta JSON  │   3. responde JSON            │        │           │
 └──────────────────┘                   └───────────────────────────────┘        └───────────┘
```

- **React solo muestra y envía.** Nunca decide si algo está permitido.
- **Django decide todo**: quién puede hacer qué, qué ve cada usuario y a qué estado pasa cada cosa.
- **La lógica de los estados vive en los modelos** (por ejemplo, `Entrega.aprobar()`), no en las vistas.
  Así la regla está en un solo lugar y la usan igual la API, las pruebas y el comando de datos de demostración.

### 4.2 Recorrido completo de un clic: "Aprobar entrega"

Sigamos lo que pasa cuando el administrador pulsa **Aprobar** en la pantalla de revisión:

1. **Pantalla** — `frontend/src/pages/admin/RevisarEntrega.tsx` llama a
   `api("entregas/15/aprobar/", { method: "POST", body: { observaciones } })`.
2. **Cliente de la API** — `frontend/src/lib/api.ts` hace un `fetch` a `/api/entregas/15/aprobar/`,
   agrega la cabecera `X-CSRFToken` (protección contra sitios falsos) y la cookie de sesión.
3. **Proxy** (solo en desarrollo) — Vite, en el puerto 5173, reenvía todo lo que empieza con `/api/` a Django en el 8000
   (`frontend/vite.config.ts`).
4. **Rutas** — `gestion_campo/urls.py` ve que empieza con `api/` y busca en `entregas/urls_api.py`, que dice que
   `entregas/<pk>/aprobar/` lo atiende `AprobarView`.
5. **Permisos** — `AprobarView` tiene `permission_classes = [EsAdministrador]` (definido en `gestion_campo/api.py`):
   si el usuario no ha iniciado sesión, no tiene empresa activa o no es administrador, Django responde **403** y no sigue.
6. **Filtro por empresa (regla 5)** — la vista busca la entrega con `entregas_empresa(request.user)`, que solo
   incluye entregas de la empresa del administrador. Si es de otra empresa, responde **404**.
7. **Modelo** — la vista llama a `entrega.aprobar(request.user, observaciones)` (`entregas/models.py`), que, dentro de
   una **transacción** (todo o nada):
   - comprueba que la entrega siga **en revisión** y que el revisor sea administrador de esa empresa;
   - crea la `Revision`, cambia la entrega a **APROBADA** y la tarea a **COMPLETADA** (regla 1);
   - anota el cambio en el **historial** (regla 8) y crea una **notificación** para el empleado.
8. **Errores** — si algo no se cumple, el modelo lanza `ValidationError("Esta entrega ya fue revisada.")`.
   El manejador `manejar_excepcion` de `gestion_campo/api.py` lo convierte en una respuesta **400** con el mensaje,
   y React lo muestra en un cuadro rojo (`ErrorBox`).
9. **Respuesta** — si todo salió bien, la vista responde `{"estado": "APROBADA"}` y la pantalla muestra
   "Entrega aprobada correctamente".

Este mismo patrón (pantalla → `api.ts` → `urls_api.py` → vista con permiso → método del modelo → historial → JSON)
se repite en **todas** las acciones de la aplicación.

### 4.3 Cómo dependen las apps entre sí

```text
                cuentas  (Empresa, Usuario)
                   ▲
        ┌──────────┼──────────────┐
  configuracion  historial      gestion_campo/api.py (permisos)
  (TipoServicio)  (registrar,
        ▲          notificar)
        │           ▲  ▲  ▲
      tareas ───────┘  │  │
        ▲              │  │
   ┌────┴─────┐        │  │
 entregas   viaticos ──┴──┘
   ▲            ▲
   └── reportes ┘  (lee tareas, entregas y viáticos para calcular indicadores)
```

- Todas usan **`cuentas`** (cada registro pertenece a una empresa y a usuarios).
- **`tareas`** necesita **`configuracion`** (cada tarea es de un tipo de servicio).
- **`entregas`** y **`viaticos`** cuelgan de una **tarea**.
- **`historial`** no depende de las demás: ellas lo llaman (`registrar()`, `notificar()`) cada vez que cambian de estado.
- **`reportes`** solo **lee** datos de las otras para calcular.

### 4.4 Los estados (máquinas de estado)

Muchas cosas del sistema tienen un **estado** que cambia con las acciones. Este es el resumen:

```text
TAREA:     PENDIENTE ─iniciar/marcar─▶ EN_PROCESO ─presentar─▶ EN_REVISION ─aprobar─▶ COMPLETADA
                                                                    │
                                                                 devolver
                                                                    ▼
                                                                 DEVUELTA ─presentar─▶ EN_REVISION (nueva versión)

ENTREGA:   EN_REVISION ─aprobar─▶ APROBADA          EN_REVISION ─devolver─▶ DEVUELTA

VIÁTICO:   SOLICITADO ─autorizar (sin anticipo)─▶ AUTORIZADO ─anticipo─▶ ANTICIPO_ENTREGADO
               │      └autorizar (con anticipo)──────────────────────────▲
               └rechazar─▶ RECHAZADO
           AUTORIZADO / ANTICIPO_ENTREGADO ─primer gasto─▶ EN_COMPROBACION
           AUTORIZADO / ANTICIPO_ENTREGADO / EN_COMPROBACION ─liquidar─▶ LIQUIDADO

GASTO:     PENDIENTE ─aprobar─▶ APROBADO           PENDIENTE ─rechazar─▶ RECHAZADO
```

> El estado `CANCELADA` de la tarea existe en el modelo, pero todavía no hay ninguna acción que lo use.

### 4.5 Cómo se arranca

Todo se maneja desde la carpeta `frontend/` con **pnpm** (detalles en el [documento 1](explicacion/01-arranque-y-configuracion.md)
y en el [documento 9](explicacion/09-frontend-base.md)):

| Comando | Qué hace |
|---|---|
| `pnpm preparar` | Primera vez: crea el entorno de Python, instala todo y crea la base de datos |
| `pnpm django cargar_demo` | Carga una empresa de ejemplo con usuarios, tareas y viáticos |
| `pnpm dev:todo` | Arranca Django (puerto 8000) y Vite (puerto 5173) a la vez. Se abre `http://localhost:5173/app/` |
| `pnpm servir` | Compila React y lo sirve solo Django en `http://localhost:8000/app/` |
| `pnpm django test` | Corre las 104 pruebas automáticas |

---

## 5. Glosario para principiantes

| Término | Significado |
|---|---|
| **Backend** | La parte que corre en el servidor (aquí, Django). Guarda los datos y aplica las reglas. |
| **Frontend** | La parte que corre en el navegador (aquí, React). Dibuja las pantallas. |
| **API** | Conjunto de direcciones (`/api/tareas/`, `/api/viaticos/`…) por las que el frontend le pide o envía datos al backend. |
| **JSON** | Formato de texto para intercambiar datos: `{"titulo": "Limpiar", "estado": "PENDIENTE"}`. |
| **HTTP: GET, POST, PATCH, PUT, DELETE** | Tipos de petición: leer, crear/hacer una acción, modificar parte, reemplazar, borrar. |
| **Código de estado** | Número de la respuesta: 200 bien, 201 creado, 204 sin contenido, 400 datos inválidos, 403 sin permiso, 404 no existe. |
| **Modelo** | Clase de Python que representa una tabla de la base de datos (`Tarea`, `Viatico`…). |
| **ORM** | Herramienta de Django para usar la base de datos con Python en vez de SQL: `Tarea.objects.filter(estado="PENDIENTE")`. |
| **QuerySet** | Una consulta de Django a la base de datos, que se puede seguir filtrando antes de ejecutarse. |
| **Migración** | Archivo que le dice a la base de datos cómo crear o cambiar tablas. |
| **ForeignKey (FK)** | Columna que apunta a otra tabla: cada `Tarea` apunta a una `Empresa`. |
| **Transacción** | Grupo de cambios que se guardan **todos juntos o ninguno**. Evita datos a medias si algo falla. |
| **`select_for_update()`** | Bloquea una fila mientras dura la transacción, para que dos personas no la cambien a la vez. |
| **Serializer** | Pieza de DRF que convierte modelos en JSON y valida el JSON que llega. |
| **Vista (View)** | Función o clase que recibe una petición y devuelve una respuesta. |
| **Permiso (permission class)** | Regla que decide si el usuario puede usar una vista (por ejemplo, `EsAdministrador`). |
| **Sesión / cookie** | Al iniciar sesión, Django guarda una cookie en el navegador para reconocerte en cada petición. |
| **CSRF** | Ataque en el que otro sitio intenta hacer peticiones en tu nombre. Django lo impide exigiendo un token secreto (`X-CSRFToken`). |
| **SPA** | *Single Page Application*: una sola página HTML; React cambia lo que se ve sin recargar. Aquí vive en `/app/`. |
| **Componente** | En React, una función que devuelve un pedazo de pantalla (`<Badge>`, `<ErrorBox>`…). |
| **Hook** | Función especial de React que empieza con `use` (`useState`, `useEffect`, `useApi`) para guardar estado o reaccionar a cambios. |
| **Props** | Los datos que un componente recibe de quien lo usa: `<Badge tipo="tarea" estado="PENDIENTE">`. |
| **Estado (React)** | Datos que, al cambiar, hacen que la pantalla se vuelva a dibujar (`useState`). |
| **TypeScript** | JavaScript con **tipos**: el compilador avisa si usas un dato de forma incorrecta. |
| **Proxy** | Intermediario: en desarrollo, Vite reenvía a Django lo que no es de React. |
| **Responsivo** | Diseño que se adapta al tamaño de la pantalla (teléfono, tableta, computadora). |
| **Prueba automática** | Código que ejecuta la aplicación y comprueba que el resultado sea el esperado. |

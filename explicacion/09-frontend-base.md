# 9. Frontend: la base de React

[← Volver al índice](../EXPLICACION.md)

La carpeta **`frontend/`** contiene la aplicación **React** que se ve en el navegador. Es una **SPA**
(una sola página): el navegador descarga una vez `index.html` y el código JavaScript, y a partir de ahí React
cambia lo que se ve sin recargar, pidiéndole datos a Django por la API.

Este documento explica la **base**: configuración, arranque, cómo se habla con la API, la sesión, los
armazones (layouts) y los componentes reutilizables. Las pantallas están en el [documento 10](10-frontend-pantallas.md).

## Archivos de configuración y scripts

| Archivo | Para qué sirve |
|---|---|
| `package.json` | Dependencias de JavaScript y **comandos** (`pnpm dev:todo`, `pnpm build`, `pnpm preparar`…) |
| `pnpm-lock.yaml` | Versiones exactas instaladas (lo maneja pnpm; no se edita a mano) |
| `vite.config.ts` | Configuración de **Vite**: plugins, alias `@`, rutas base y el **proxy** hacia Django |
| `tsconfig.json` | Configuración de **TypeScript** (modo estricto, alias `@/*`) |
| `index.html` | La única página HTML: tiene un `<div id="root">` donde React dibuja todo |
| `scripts/python.mjs` | Encuentra el Python del entorno virtual `.venv` (en Mac, Linux y Windows) |
| `scripts/preparar.mjs` | `pnpm preparar`: crea `.venv`, instala dependencias, copia `.env`, migra la base de datos |
| `scripts/django.mjs` | `pnpm django <comando>`: ejecuta `manage.py` con el Python de `.venv` |
| `dist/` | (No está en Git) El resultado de `pnpm build`, que Django sirve en producción |

## Archivos de `frontend/src/`

| Archivo o carpeta | Para qué sirve |
|---|---|
| `main.tsx` | Punto de entrada: monta `<App />` dentro de `#root` |
| `App.tsx` | **Todas las rutas**: qué pantalla corresponde a cada URL y a cada rol |
| `index.css` | Estilos: tema de colores (`@theme`), clases de componentes y reglas responsivas |
| `vite-env.d.ts` | Tipos de Vite para TypeScript |
| `lib/api.ts` | Función `api()` para hablar con Django (cookies, CSRF y errores) |
| `lib/sesion.tsx` | Contexto de **sesión**: usuario actual, `ingresar()`, `salir()`, `refrescar()` |
| `lib/useApi.ts` | Hook `useApi()`: carga datos de la API y maneja "cargando" y errores |
| `lib/tipos.ts` | Tipos TypeScript de lo que devuelve la API (`TareaResumen`, `ViaticoDetalle`…) |
| `lib/formato.ts` | Formatos de pantalla: fechas dd/mm/aaaa, hora de Santo Domingo, montos RD$ |
| `lib/estados.ts` | Qué color (clase CSS) le toca a cada estado y prioridad |
| `lib/navegacion.ts` | Menús del administrador y del empleado, y `rutaSpa()` para los enlaces de notificaciones |
| `layouts/AdminLayout.tsx` | Armazón de **escritorio** del administrador: menú lateral, barra superior, búsqueda |
| `layouts/MobileLayout.tsx` | Armazón del **empleado**: barra inferior en teléfono, menú lateral en computadora |
| `components/` | Piezas reutilizables (ver tabla de componentes más abajo) |
| `pages/` | Las pantallas (ver [documento 10](10-frontend-pantallas.md)) |

---

## Fragmentos importantes

### 9.1 `package.json` — los comandos

```json
"scripts": {
  "preparar": "node scripts/preparar.mjs",
  "dev": "vite",
  "dev:todo": "concurrently -k -n django,vite -c yellow,cyan \"node scripts/django.mjs runserver\" \"vite\"",
  "servir": "pnpm build && node scripts/django.mjs runserver",
  "django": "node scripts/django.mjs",
  "build": "tsc --noEmit && vite build",
  "preview": "vite preview",
  "format": "oxfmt"
}
```

- `"preparar"` — primera instalación (crea el entorno de Python y la base de datos).
- `"dev"` — solo el servidor de Vite (React) en el puerto 5173.
- `"dev:todo"` — usa la herramienta **concurrently** para arrancar **dos** procesos en la misma terminal: Django (`runserver`, puerto 8000) y Vite. `-k` detiene los dos si uno se cae; `-n` y `-c` les ponen nombre y color en la salida.
- `"servir"` — compila React y luego arranca solo Django, que sirve el resultado.
- `"django"` — atajo para cualquier comando de `manage.py`: `pnpm django migrate`, `pnpm django test`…
- `"build"` — primero `tsc --noEmit` revisa los tipos de TypeScript (si hay un error, se detiene) y luego `vite build` genera `dist/`.
- `"preview"` / `"format"` — vista previa del build y formateo de código.

### 9.2 `vite.config.ts` — el proxy hacia Django

```ts
const DJANGO = process.env.DJANGO_URL || "http://127.0.0.1:8000";

export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/app/" : "/app/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": `${import.meta.dirname}/src` } },
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "^/(?!app(/|$)).*": { target: DJANGO, changeOrigin: false } },
  },
}));
```

- `const DJANGO = process.env.DJANGO_URL || "http://127.0.0.1:8000";` — dirección de Django; se puede cambiar con una variable de entorno.
- `export default defineConfig(({ command }) => ({...}))` — la configuración es una función que recibe qué comando se ejecuta (`serve` o `build`).
- `base: command === "build" ? "/static/app/" : "/app/"` — en desarrollo la app vive en `/app/`; compilada, sus archivos se sirven desde `/static/app/` (Django los sirve como archivos estáticos).
- `plugins: [react(), tailwindcss()]` — activa el soporte de React (JSX, recarga rápida) y de Tailwind CSS.
- `resolve: { alias: { "@": ... } }` — permite escribir `import X from "@/lib/api"` en vez de rutas relativas largas como `../../lib/api`.
- `build: { outDir: "dist", emptyOutDir: true }` — el build va a `dist/` y se limpia antes.
- `port: 5173, strictPort: true` — usa el puerto 5173; si está ocupado, falla en vez de usar otro.
- `proxy: { "^/(?!app(/|$)).*": { target: DJANGO, ... } }` — **lo más importante**: toda ruta que **no** empiece con `/app` (por ejemplo `/api/tareas/` o `/admin/`) se reenvía a Django. La expresión `(?!...)` significa "que no siga…". Así el navegador cree que React y Django están en el mismo sitio (mismo origen), y las cookies de sesión y CSRF funcionan sin configuración extra.

### 9.3 `main.tsx` — encender React

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- `import { StrictMode } from "react";` — modo estricto: en desarrollo, React avisa de malas prácticas.
- `import { createRoot } from "react-dom/client";` — función que conecta React con la página HTML.
- `import App from "./App";` — el componente principal.
- `import "./index.css";` — carga los estilos (Vite los inyecta en la página).
- `createRoot(document.getElementById("root")!)` — busca el `<div id="root">` de `index.html`. El `!` le asegura a TypeScript que existe.
- `.render(<StrictMode><App /></StrictMode>)` — dibuja la aplicación dentro de ese `div`.

### 9.4 `App.tsx` — rutas, protección y pantallas por rol

```tsx
function Protegido() {
  const { usuario, cargando } = useSesion();
  const { pathname } = useLocation();
  if (cargando) {
    return <div className="flex min-h-dvh items-center justify-center bg-surface"><Logo /></div>;
  }
  if (!usuario) return <Navigate to="/ingresar" replace state={{ desde: pathname }} />;
  return esAdministrador(usuario) ? <AdminLayout /> : <MobileLayout />;
}

function PorRol({ admin, empleado }: { admin?: ReactElement; empleado?: ReactElement }) {
  const { usuario } = useSesion();
  const pantalla = esAdministrador(usuario) ? admin : empleado;
  return pantalla ?? <Navigate to="/" replace />;
}

export default function App() {
  return (
    <SesionProvider>
      <BrowserRouter basename="/app">
        <Routes>
          <Route path="ingresar" element={<Login />} />
          <Route element={<Protegido />}>
            <Route index element={<PorRol admin={<Panel />} empleado={<MisTareas />} />} />
            <Route path="tareas/:id" element={<PorRol admin={<TareaAdmin />} empleado={<TareaEmpleado />} />} />
            <Route path="tareas/:id/evidencias" element={<PorRol empleado={<Evidencias />} />} />
            ...
            <Route path="notificaciones" element={<Notificaciones />} />
            <Route path="perfil" element={<Perfil />} />
          </Route>
          <Route path="*" element={<NoEncontrado />} />
        </Routes>
      </BrowserRouter>
    </SesionProvider>
  );
}
```

- `function Protegido()` — un componente "guardián" que envuelve todas las pantallas que exigen sesión.
- `const { usuario, cargando } = useSesion();` — lee la sesión del contexto (ver 9.6).
- `const { pathname } = useLocation();` — la ruta actual, por ejemplo `/tareas/5`.
- `if (cargando) return <div>...<Logo /></div>;` — mientras se pregunta a Django si hay sesión, muestra solo el logo.
- `if (!usuario) return <Navigate to="/ingresar" replace state={{ desde: pathname }} />;` — sin sesión, lleva al inicio de sesión y **recuerda** de dónde venía para volver ahí después de entrar.
- `return esAdministrador(usuario) ? <AdminLayout /> : <MobileLayout />;` — elige el armazón según el rol. Dentro del armazón, `<Outlet />` dibujará la pantalla de la ruta.
- `function PorRol({ admin, empleado })` — permite que **una misma URL** muestre pantallas distintas según el rol.
- `const pantalla = esAdministrador(usuario) ? admin : empleado;` — elige la pantalla del rol.
- `return pantalla ?? <Navigate to="/" replace />;` — si ese rol no tiene pantalla en esa ruta, vuelve al inicio. `??` usa el valor de la derecha cuando el de la izquierda es `null` o `undefined`.
- `<SesionProvider>` — pone la sesión a disposición de toda la app.
- `<BrowserRouter basename="/app">` — activa el enrutador de React; todas las rutas cuelgan de `/app`.
- `<Route path="ingresar" element={<Login />} />` — `/app/ingresar` es público.
- `<Route element={<Protegido />}>` — todas las rutas de adentro pasan por el guardián.
- `<Route index element={<PorRol admin={<Panel />} empleado={<MisTareas />} />} />` — en `/app/` el administrador ve el Panel y el empleado sus tareas.
- `<Route path="tareas/:id" ...>` — `:id` es un **parámetro**: en `/app/tareas/5`, la pantalla lee `id = "5"` con `useParams()`.
- `<Route path="*" element={<NoEncontrado />} />` — cualquier otra ruta muestra "no encontrado".

> Ocultar una pantalla aquí **no es seguridad**: si un empleado escribiera a mano la URL de una acción de administrador,
> igual la API de Django le respondería 403. React solo organiza la interfaz.

### 9.5 `lib/api.ts` — hablar con Django

```ts
export async function api<T>(ruta: string, { method = "GET", body }: Opciones = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const esArchivo = body instanceof FormData;
  if (body !== undefined && !esArchivo) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = leerCookie("csrftoken");

  const respuesta = await fetch(`/api/${ruta}`, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : esArchivo ? body : JSON.stringify(body),
  });
  if (respuesta.status === 204) return undefined as T;
  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) throw new ApiError(respuesta.status, extraerMensajes(datos, respuesta.status));
  return datos as T;
}

export function mensajesDe(error: unknown, defecto = "No se pudo completar la acción."): string[] {
  return error instanceof ApiError ? error.mensajes : [defecto];
}
```

- `export async function api<T>(ruta, { method = "GET", body } = {}): Promise<T>` — función **asíncrona** (devuelve una promesa que se espera con `await`). `<T>` es un **genérico**: quien la llama dice qué tipo de datos espera, por ejemplo `api<TareaDetalle>("tareas/5/")`.
- `const headers = { Accept: "application/json" };` — pide respuestas en JSON.
- `const esArchivo = body instanceof FormData;` — `FormData` se usa para enviar archivos (fotos).
- `if (body !== undefined && !esArchivo) headers["Content-Type"] = "application/json";` — si se envían datos normales, avisa que van en JSON. (Con `FormData`, el navegador pone su propio tipo).
- `if (method !== "GET") headers["X-CSRFToken"] = leerCookie("csrftoken");` — en peticiones que cambian algo, copia el token CSRF de la cookie a una cabecera. Django compara ambos: un sitio malicioso no puede leer tu cookie, así que no puede falsificar la cabecera.
- `const respuesta = await fetch(`/api/${ruta}`, {...})` — `fetch` hace la petición HTTP. `await` espera la respuesta.
- `credentials: "same-origin"` — envía las cookies (sesión) porque es el mismo sitio.
- `body: ... esArchivo ? body : JSON.stringify(body)` — los archivos van tal cual; los objetos se convierten a texto JSON.
- `if (respuesta.status === 204) return undefined as T;` — 204 = sin contenido: no hay nada que leer.
- `const datos = await respuesta.json().catch(() => null);` — lee el JSON; si la respuesta no era JSON, usa `null`.
- `if (!respuesta.ok) throw new ApiError(...)` — si el código no es 2xx (por ejemplo 400 o 403), **lanza** un error con los mensajes en español que mandó Django.
- `return datos as T;` — si todo fue bien, devuelve los datos.
- `export function mensajesDe(error, defecto)` — saca los mensajes de un error para mostrarlos; si el error no vino de la API (por ejemplo, sin internet), usa un mensaje genérico.

### 9.6 `lib/sesion.tsx` — la sesión compartida por toda la app

```tsx
const SesionContext = createContext<Sesion | null>(null);

export function SesionProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  const refrescar = useCallback(async () => {
    const datos = await api<{ usuario: Usuario | null }>("sesion/");
    setUsuario(datos.usuario);
  }, []);

  useEffect(() => {
    refrescar().catch(() => setUsuario(null)).finally(() => setCargando(false));
  }, [refrescar]);

  const ingresar = useCallback(async (username: string, password: string) => {
    const datos = await api<{ usuario: Usuario }>("sesion/", { method: "POST", body: { username, password } });
    setUsuario(datos.usuario);
    return datos.usuario;
  }, []);

  const salir = useCallback(async () => {
    await api("sesion/", { method: "DELETE" });
    setUsuario(null);
    await refrescar();
  }, [refrescar]);

  return <SesionContext.Provider value={{ usuario, cargando, ingresar, salir, refrescar }}>{children}</SesionContext.Provider>;
}

export function useSesion(): Sesion {
  const contexto = useContext(SesionContext);
  if (!contexto) throw new Error("useSesion fuera de SesionProvider");
  return contexto;
}
```

- `const SesionContext = createContext<Sesion | null>(null);` — un **contexto** de React: una "caja" de datos que cualquier componente puede leer sin pasarlos de mano en mano.
- `export function SesionProvider({ children })` — el componente que llena esa caja y envuelve a toda la app.
- `const [usuario, setUsuario] = useState<Usuario | null>(null);` — **estado**: el usuario actual (al principio, ninguno). Cuando se llama a `setUsuario`, React vuelve a dibujar lo que depende de él.
- `const [cargando, setCargando] = useState(true);` — empieza "cargando" hasta saber si hay sesión.
- `const refrescar = useCallback(async () => {...}, []);` — pregunta a `GET /api/sesion/` quién es el usuario y lo guarda. `useCallback` mantiene la misma función entre dibujos (para que los efectos que dependen de ella no se repitan sin motivo).
- `useEffect(() => {...}, [refrescar]);` — un **efecto**: se ejecuta después de dibujar. Aquí, una sola vez al abrir la app: llama a `refrescar`, si falla deja `usuario` en `null`, y al final quita el "cargando".
- `const ingresar = useCallback(async (username, password) => {...})` — envía `POST /api/sesion/` con las credenciales y guarda el usuario que devuelve Django. Si falla, `api()` lanza el error y la pantalla de login lo muestra.
- `const salir = useCallback(async () => {...})` — `DELETE /api/sesion/`, borra el usuario y vuelve a pedir la sesión para recibir una cookie CSRF nueva.
- `return <SesionContext.Provider value={{...}}>{children}</SesionContext.Provider>;` — pone todo en la caja y dibuja la app (`children`) adentro.
- `export function useSesion(): Sesion` — **hook propio** para leer la caja: `const { usuario } = useSesion();`.
- `if (!contexto) throw new Error(...)` — avisa al programador si alguien lo usa fuera del proveedor.

### 9.7 `lib/useApi.ts` — cargar datos en una pantalla

```ts
export function useApi<T>(ruta: string | null) {
  const [datos, setDatos] = useState<T | null>(null);
  const [errores, setErrores] = useState<string[]>([]);
  const [cargando, setCargando] = useState(ruta !== null);

  const recargar = useCallback(async () => {
    if (ruta === null) return;
    setCargando(true);
    try {
      setDatos(await api<T>(ruta));
      setErrores([]);
    } catch (e) {
      setErrores(mensajesDe(e, "No se pudo cargar la información."));
    } finally {
      setCargando(false);
    }
  }, [ruta]);

  useEffect(() => {
    recargar();
  }, [recargar]);

  return { datos, setDatos, errores, setErrores, cargando, recargar };
}
```

- `export function useApi<T>(ruta: string | null)` — hook que casi todas las pantallas usan para pedir datos. Si `ruta` es `null`, no carga nada.
- `const [datos, setDatos] = useState<T | null>(null);` — los datos recibidos (al principio, nada).
- `const [errores, setErrores] = useState<string[]>([]);` — mensajes de error para mostrar.
- `const [cargando, setCargando] = useState(ruta !== null);` — si hay ruta, empieza cargando.
- `const recargar = useCallback(async () => {...}, [ruta]);` — función que pide los datos. Se vuelve a crear cuando cambia la ruta.
- `setCargando(true);` — muestra el estado de carga.
- `try { setDatos(await api<T>(ruta)); setErrores([]); }` — pide los datos, los guarda y limpia errores viejos.
- `catch (e) { setErrores(mensajesDe(e, ...)); }` — si falla, guarda los mensajes.
- `finally { setCargando(false); }` — pase lo que pase, termina el "cargando".
- `useEffect(() => { recargar(); }, [recargar]);` — carga al abrir la pantalla y **cada vez que cambia la ruta** (por ejemplo, al cambiar un filtro, la ruta pasa de `viaticos/` a `viaticos/?estado=LIQUIDADO` y se recarga sola).
- `return { datos, setDatos, errores, setErrores, cargando, recargar };` — devuelve todo para que la pantalla lo use.

Ejemplo de uso en una pantalla:

```tsx
const { datos: tarea, errores } = useApi<TareaDetalle>(`tareas/${id}/`);
```

### 9.8 `lib/formato.ts` — fechas y montos

```ts
const ZONA = "America/Santo_Domingo";
const fechaCorta = new Intl.DateTimeFormat("es-DO", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: ZONA });
const numero = new Intl.NumberFormat("es-DO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const SOLO_FECHA = /^\d{4}-\d{2}-\d{2}$/;

export function fecha(valor: string | Date): string {
  if (typeof valor === "string" && SOLO_FECHA.test(valor)) {
    const [a, m, d] = valor.split("-");
    return `${d}/${m}/${a}`;
  }
  return fechaCorta.format(new Date(valor));
}

export function rd(monto: string | number | null | undefined): string {
  return `RD$ ${numero.format(Number(monto ?? 0))}`;
}
```

- `const ZONA = "America/Santo_Domingo";` — todas las fechas se muestran en hora dominicana, aunque la computadora esté en otro país.
- `new Intl.DateTimeFormat("es-DO", {...})` — `Intl` es la herramienta del navegador para formatos según el idioma y país: aquí, día/mes/año con 2 dígitos.
- `new Intl.NumberFormat("es-DO", {...})` — números siempre con 2 decimales.
- `const SOLO_FECHA = /^\d{4}-\d{2}-\d{2}$/;` — **expresión regular** que reconoce una fecha sin hora como `"2026-11-18"`.
- `export function fecha(valor)` — convierte una fecha de la API a dd/mm/aaaa.
- `if (typeof valor === "string" && SOLO_FECHA.test(valor))` — si es solo fecha (sin hora)…
- `const [a, m, d] = valor.split("-"); return `${d}/${m}/${a}`;` — …la reordena a mano, **sin pasar por zonas horarias** (si no, "2026-11-18" a medianoche UTC podría mostrarse como el 17 en Santo Domingo).
- `return fechaCorta.format(new Date(valor));` — si tiene hora, la convierte a la zona de Santo Domingo.
- `export function rd(monto)` — los montos llegan como texto (`"1500.00"`) y solo se formatean para mostrar: `"RD$ 1,500.00"`. `monto ?? 0` usa 0 si viene vacío.

### 9.9 `layouts/MobileLayout.tsx` — el armazón del empleado

```tsx
export default function MobileLayout() {
  const { refrescar } = useSesion();
  const { pathname } = useLocation();
  const principal = NAV_EMPLEADO.some((item) => item.to === pathname);
  useEffect(() => {
    window.scrollTo(0, 0);
    refrescar().catch(() => null);
  }, [pathname, refrescar]);
  return (
    <div className={`mobile-app ${principal ? "con-menu" : ""}`}>
      <BottomNav />
      <main className="mobile-main"><Outlet /></main>
    </div>
  );
}
```

- `const principal = NAV_EMPLEADO.some((item) => item.to === pathname);` — ¿es una de las 4 pantallas del menú (Tareas, Viáticos, Notificaciones, Perfil)? `.some` devuelve verdadero si alguna coincide.
- `useEffect(() => {...}, [pathname, refrescar]);` — cada vez que cambia la pantalla…
- `window.scrollTo(0, 0);` — …vuelve arriba (como haría una página nueva)…
- `refrescar().catch(() => null);` — …y actualiza la sesión para que el punto rojo de notificaciones esté al día.
- `<div className={`mobile-app ${principal ? "con-menu" : ""}`}>` — la clase `con-menu` le dice al CSS que muestre la barra inferior en el teléfono. En las pantallas de detalle no se muestra (en su lugar hay un botón de acción fijo abajo).
- `<BottomNav />` — el menú: barra inferior en teléfono y tableta; barra lateral fija en computadora (lo decide el CSS con *media queries*).
- `<main className="mobile-main"><Outlet /></main>` — `<Outlet />` es el hueco donde React Router pone la pantalla de la ruta actual.

### 9.10 `index.css` — tema y diseño responsivo

El archivo tiene más de 800 líneas; aquí se juntan, resumidas, las reglas clave del diseño responsivo del empleado.

```css
@import "tailwindcss";

@theme {
  --color-wine: #006a70;
  --color-wine-dark: #00474c;
  --color-surface: #f5f7fa;
}

.mobile-app { --lado: 20px; --menu: 0px; padding-bottom: env(safe-area-inset-bottom); }
.mobile-scroll { padding-inline: var(--lado); }

@media (min-width: 768px) {
  .mobile-app { --lado: 32px; font-size: 16px; }
  .lista-tarjetas { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
}

@media (min-width: 1024px) {
  .mobile-app { --menu: 248px; --lado: max(40px, calc((100vw - var(--menu) - 1400px) / 2)); padding-left: var(--menu); }
  .detalle-grid { grid-template-columns: minmax(0, 1fr) minmax(320px, 400px); column-gap: 24px; }
}
```

- `@import "tailwindcss";` — carga Tailwind, que permite dar estilo con clases cortas en el JSX (`flex`, `mb-4`, `text-sm`…).
- `@theme { --color-wine: #006a70; ... }` — define los colores del tema. Tailwind crea clases a partir de ellos: `text-wine`, `bg-surface`…
- `.mobile-app { --lado: 20px; --menu: 0px; ... }` — **variables CSS** propias: `--lado` es el margen a los costados y `--menu` el ancho del menú lateral (0 en teléfono).
- `padding-bottom: env(safe-area-inset-bottom);` — deja espacio para la barra de inicio del iPhone.
- `.mobile-scroll { padding-inline: var(--lado); }` — el contenido usa ese margen a izquierda y derecha.
- `@media (min-width: 768px) {...}` — **media query**: estas reglas solo se aplican en pantallas de 768 px o más (tabletas).
- `--lado: 32px` — más margen.
- `grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));` — las tarjetas se acomodan en tantas columnas como quepan, cada una de al menos 300 px.
- `@media (min-width: 1024px) {...}` — en computadoras:
- `--menu: 248px` — aparece el menú lateral de 248 px…
- `padding-left: var(--menu);` — …y el contenido se corre a la derecha para no quedar debajo.
- `--lado: max(40px, calc((100vw - var(--menu) - 1400px) / 2));` — en pantallas muy anchas, el margen crece para que el contenido no pase de 1400 px y quede centrado.
- `.detalle-grid { grid-template-columns: ... }` — en el detalle de una tarea, dos columnas: contenido a la izquierda y lista de verificación a la derecha.

---

## Componentes reutilizables (`components/`)

| Componente | Qué dibuja |
|---|---|
| `Avatar` | Círculo con las iniciales del usuario |
| `Badge` | Insignia de color para un estado ("En proceso", "Liquidado"…) usando `lib/estados.ts` |
| `Prioridad` | Insignia de prioridad (Baja, Media, Alta, Urgente) |
| `BottomNav` | Menú del empleado (barra inferior o lateral) con punto rojo de notificaciones |
| `MobileHeader` | Encabezado de las pantallas del empleado: botón Volver, título y acción |
| `Heading` | Encabezado de las pantallas del administrador: fecha, título, descripción y botones |
| `Icon` | Íconos SVG dibujados a mano (no usa librerías externas) |
| `Logo` | Logo de TaskControl (completo o solo el símbolo) |
| `ErrorBox` | Cuadro rojo con mensajes de error |
| `Cargando` | Rectángulos grises animados mientras cargan los datos ("esqueleto") |
| `Progress` | Barra de avance de la lista de verificación |
| `Stat` | Tarjeta de indicador del panel (opcionalmente es un enlace) |
| `Modal` | Ventana emergente; se cierra con Escape o tocando fuera |
| `MenuFila` | Botón "⋯" con un menú de acciones (en tablas y detalle) |
| `Paginacion` | Pie de tabla: "Mostrando 1–20 de 42" y botones de página |
| `Field`, `SectionTitle`, `Switch` | Piezas de los formularios del administrador |

### 9.11 Un componente pequeño: `Badge`

```tsx
import { claseEstado, type TipoEstado } from "@/lib/estados";

export default function Badge({ tipo, estado, children }: { tipo: TipoEstado; estado: string; children: string }) {
  return <span className={`badge ${claseEstado(tipo, estado)}`}>{children}</span>;
}
```

- `import { claseEstado, type TipoEstado } from "@/lib/estados";` — importa la función que decide el color y el tipo `TipoEstado` (`"tarea" | "entrega" | "viatico" | "gasto"`).
- `export default function Badge({ tipo, estado, children }: {...})` — un componente es una función que recibe **props**. Entre llaves se "desarman" las props; después de los dos puntos va su tipo.
- `return <span className={`badge ${claseEstado(tipo, estado)}`}>{children}</span>;` — devuelve JSX (HTML dentro de JavaScript). La clase final es, por ejemplo, `"badge badge-green"`. `children` es el texto que va entre las etiquetas.

Uso: `<Badge tipo="tarea" estado="COMPLETADA">Completada</Badge>` dibuja una insignia verde.

---

## Cómo se conecta con lo demás

- Todas las pantallas usan `useApi()` o `api()` → `fetch("/api/...")` → (proxy de Vite en desarrollo) → Django.
- `lib/tipos.ts` describe en TypeScript las mismas formas de datos que arman las funciones `*_json`, `*_resumen` y `*_detalle` de los `api.py` de Django.
- `lib/sesion.tsx` usa `/api/sesion/` de la app **cuentas**.
- En producción, `pnpm build` crea `frontend/dist/`; `gestion_campo/settings.py` lo registra como archivos estáticos y `gestion_campo/views.py` entrega su `index.html`.

[← Anterior: Reportes](08-reportes.md) · [Índice](../EXPLICACION.md) · [Siguiente: Pantallas →](10-frontend-pantallas.md)

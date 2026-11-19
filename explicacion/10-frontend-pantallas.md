# 10. Frontend: las pantallas

[← Volver al índice](../EXPLICACION.md)

Las pantallas están en **`frontend/src/pages/`**. Cada archivo es un componente de React que, casi siempre,
hace tres cosas:

1. **Carga** datos con `useApi("ruta/")`.
2. **Muestra** esos datos con componentes (`Badge`, `ErrorBox`, `Cargando`…) y clases de Tailwind.
3. **Envía** acciones con `api("ruta/", { method: "POST", body })` y muestra los errores que devuelva Django.

## Archivos

### Compartidas (`pages/`)

| Archivo | Ruta | Qué hace |
|---|---|---|
| `Login.tsx` | `/app/ingresar` | Inicio de sesión con correo o usuario |
| `Notificaciones.tsx` | `/app/notificaciones` | Lista de avisos; tocar uno lo marca leído y abre la tarea o viático. Diseño distinto según el rol |
| `Perfil.tsx` | `/app/perfil` | Datos del usuario y botón para cerrar sesión |
| `NoEncontrado.tsx` | cualquier otra | Mensaje "página no encontrada" |

### Empleado (`pages/empleado/`)

| Archivo | Ruta | Qué hace |
|---|---|---|
| `MisTareas.tsx` | `/app/` | Saludo, filtros (Pendientes, En proceso, Vencidas…) y tarjetas de sus tareas |
| `TareaDetalle.tsx` | `/app/tareas/:id` | Descripción, ubicación (abre mapas), criterios y lista de verificación para marcar; botón Iniciar / Continuar |
| `Evidencias.tsx` | `/app/tareas/:id/evidencias` | Tomar o elegir fotos, comentario y "Solicitar revisión" |
| `Entregas.tsx` | `/app/tareas/:id/entregas` | Historial de versiones; si fue devuelta, muestra las correcciones pedidas |
| `MisViaticos.tsx` | `/app/viaticos` | Resumen (disponible y por comprobar) y tarjetas de sus viáticos |
| `SolicitarViatico.tsx` | `/app/viaticos/solicitar` | Formulario: tarea, concepto y monto |
| `ViaticoDetalle.tsx` | `/app/viaticos/:id` | Montos, gastos registrados con su estado y la liquidación |
| `RegistrarGasto.tsx` | `/app/viaticos/:id/gasto` | Formulario: categoría, fecha, monto, foto del comprobante y nota |

### Administrador (`pages/admin/`)

| Archivo | Ruta | Qué hace |
|---|---|---|
| `Panel.tsx` | `/app/` | Indicadores, cumplimiento por empleado y últimas entregas en revisión |
| `Tareas.tsx` | `/app/tareas` | Tabla de tareas con búsqueda, filtros y paginación |
| `TareaForm.tsx` | `/app/tareas/nueva` y `/app/tareas/:id/editar` | Crear o editar una tarea y su lista de verificación |
| `TareaDetalle.tsx` | `/app/tareas/:id` | Detalle de una tarea, sus versiones de entrega, botón "Revisar entrega" y enlace a su historial |
| `Revisiones.tsx` | `/app/entregas` | Bandeja de entregas pendientes de revisar |
| `RevisarEntrega.tsx` | `/app/entregas/:id` | Ver fotos y lista de verificación; **Aprobar** o **Devolver** |
| `Viaticos.tsx` | `/app/viaticos` | Tabla de viáticos con filtros por estado y empleado |
| `ViaticoDetalle.tsx` | `/app/viaticos/:id` | Autorizar, rechazar, entregar anticipo, revisar gastos y liquidar |
| `Usuarios.tsx` | `/app/usuarios` | Crear, editar, activar y desactivar usuarios de la empresa |
| `Servicios.tsx` | `/app/servicios` | Tipos de servicio y sus plantillas de lista de verificación |
| `Reportes.tsx` | `/app/reportes` | Pestañas de reportes, gráfico, tabla y exportación CSV |
| `Historial.tsx` | `/app/historial` | Bitácora con filtros, paginación y exportación CSV |

---

## Fragmentos importantes

### 10.1 `Login.tsx` — enviar el formulario de inicio de sesión

```tsx
export default function Login() {
  const { usuario, ingresar } = useSesion();
  const navigate = useNavigate();
  const desde = (useLocation().state as { desde?: string } | null)?.desde ?? "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errores, setErrores] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to={desde} replace />;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setErrores([]);
    setEnviando(true);
    try {
      await ingresar(username.trim(), password);
      navigate(desde, { replace: true });
    } catch (err) {
      setErrores(mensajesDe(err, "No se pudo conectar con el servidor."));
    } finally {
      setEnviando(false);
    }
  };
  ...
  <input id="usuario" ... value={username} onChange={(e) => setUsername(e.target.value)} />
  ...
  <button className="primary-button" type="submit" disabled={enviando || !username || !password}>
    {enviando ? "Ingresando…" : "Iniciar sesión"}
  </button>
```

- `const { usuario, ingresar } = useSesion();` — toma de la sesión el usuario actual y la función para entrar.
- `const navigate = useNavigate();` — función para cambiar de pantalla desde el código.
- `const desde = (useLocation().state as ...)?.desde ?? "/";` — si el guardián `Protegido` nos mandó aquí, recuerda a qué pantalla quería ir el usuario; si no, al inicio. `?.` evita un error si `state` es `null`.
- `const [username, setUsername] = useState("");` (y las demás) — estado del formulario: lo que se escribe, los errores y si se está enviando.
- `if (usuario) return <Navigate to={desde} replace />;` — si ya hay sesión, no tiene sentido mostrar el login.
- `const enviar = async (e: FormEvent) => {` — se ejecuta al enviar el formulario.
- `e.preventDefault();` — evita que el navegador recargue la página (comportamiento normal de un `<form>`).
- `setErrores([]); setEnviando(true);` — limpia errores viejos y bloquea el botón.
- `await ingresar(username.trim(), password);` — llama a `POST /api/sesion/`.
- `navigate(desde, { replace: true });` — si entró, lo lleva a donde iba. `replace` evita que el botón "Atrás" vuelva al login.
- `catch (err) { setErrores(mensajesDe(err, ...)); }` — si Django dijo "usuario o contraseña incorrectos", muestra ese mensaje.
- `finally { setEnviando(false); }` — vuelve a habilitar el botón.
- `<input ... value={username} onChange={(e) => setUsername(e.target.value)} />` — **campo controlado**: React guarda cada letra en el estado y el campo muestra lo que hay en el estado.
- `disabled={enviando || !username || !password}` — el botón está desactivado mientras envía o si falta algún dato.
- `{enviando ? "Ingresando…" : "Iniciar sesión"}` — el texto cambia mientras espera.

### 10.2 `empleado/MisTareas.tsx` — filtros sin volver a pedir datos

```tsx
const FILTROS = [
  { etiqueta: "Todas", aplica: () => true },
  { etiqueta: "Pendientes", aplica: (t: TareaResumen) => t.estado === "PENDIENTE" },
  { etiqueta: "En proceso", aplica: (t: TareaResumen) => t.estado === "EN_PROCESO" },
  { etiqueta: "Devueltas", aplica: (t: TareaResumen) => t.estado === "DEVUELTA" },
  { etiqueta: "En revisión", aplica: (t: TareaResumen) => t.estado === "EN_REVISION" },
  { etiqueta: "Vencidas", aplica: (t: TareaResumen) => t.vencida },
];

export default function MisTareas() {
  const { datos: tareas, errores, cargando } = useApi<TareaResumen[]>("mis-tareas/");
  const [filtro, setFiltro] = useState("Todas");
  const aplica = FILTROS.find((f) => f.etiqueta === filtro)!.aplica;
  const visibles = tareas?.filter(aplica) ?? [];
  ...
        <div className="chips chips-sangrado no-scrollbar pb-4">
          {FILTROS.map((f) => (
            <button key={f.etiqueta} onClick={() => setFiltro(f.etiqueta)} className={filtro === f.etiqueta ? "active" : ""} aria-pressed={filtro === f.etiqueta}>
              {f.etiqueta}
            </button>
          ))}
        </div>
        ...
        <div className="lista-tarjetas">{visibles.map((t) => <TaskCard key={t.id} tarea={t} />)}</div>
```

- `const FILTROS = [...]` — cada filtro tiene una etiqueta y una **función** `aplica` que dice si una tarea pasa el filtro.
- `{ etiqueta: "Vencidas", aplica: (t) => t.vencida }` — usa el dato `vencida` que calculó Django.
- `useApi<TareaResumen[]>("mis-tareas/")` — pide **una sola vez** las tareas del empleado.
- `const [filtro, setFiltro] = useState("Todas");` — el filtro elegido.
- `const aplica = FILTROS.find(...)!.aplica;` — busca la función del filtro activo.
- `const visibles = tareas?.filter(aplica) ?? [];` — filtra en el navegador (rápido, sin volver a llamar a la API). Si aún no hay tareas, lista vacía.
- `{FILTROS.map((f) => <button ...>)}` — dibuja un botón por filtro. `map` convierte cada elemento del arreglo en JSX.
- `key={f.etiqueta}` — React necesita una `key` única en las listas para saber qué elemento cambió.
- `onClick={() => setFiltro(f.etiqueta)}` — al tocar, cambia el filtro; React vuelve a dibujar con la nueva lista.
- `className={filtro === f.etiqueta ? "active" : ""}` — el botón activo se pinta distinto.
- `aria-pressed={...}` — accesibilidad: los lectores de pantalla saben qué botón está presionado.
- `<div className="lista-tarjetas">{visibles.map((t) => <TaskCard key={t.id} tarea={t} />)}</div>` — una tarjeta por tarea visible; la clase `lista-tarjetas` las pone en 1, 2, 3 o 4 columnas según el ancho de la pantalla.

### 10.3 `empleado/TareaDetalle.tsx` — una acción que actualiza la pantalla

```tsx
const { datos: tarea, setDatos, errores, setErrores } = useApi<Tarea>(`tareas/${id}/`);
const [ocupado, setOcupado] = useState(false);

const accion = async (fn: () => Promise<Tarea>) => {
  setOcupado(true);
  try {
    setDatos(await fn());
    setErrores([]);
  } catch (e) {
    setErrores(mensajesDe(e));
  } finally {
    setOcupado(false);
  }
};

const iniciada = tarea && tarea.estado !== "PENDIENTE";
const marcar = (itemId: number, completado: boolean) =>
  accion(() => api<Tarea>(`items/${itemId}/marcar/`, { method: "POST", body: { completado } }));
const iniciar = () => accion(() => api<Tarea>(`tareas/${id}/iniciar/`, { method: "POST" }));
...
{tarea.items.map((item) => (
  <button key={item.id} disabled={!iniciada || !tarea.abierta || ocupado} onClick={() => marcar(item.id, !item.completado)}
          role="checkbox" aria-checked={item.completado}>
    <span className={`checkbox ${item.completado ? "checked" : ""}`}>{item.completado && <Icon name="check" size={14} />}</span>
    <span>{item.descripcion}{item.obligatorio && <b className="ml-1 text-wine" aria-label="obligatorio">*</b>}</span>
  </button>
))}
```

- `useApi<Tarea>(`tareas/${id}/`)` — carga la tarea. `id` viene de la URL con `useParams()`.
- `const accion = async (fn) => {...}` — una función **reutilizable** para cualquier acción: recibe otra función `fn` que llama a la API.
- `setDatos(await fn());` — la API responde con la tarea **actualizada** y se reemplaza en pantalla. No hace falta volver a pedirla.
- `catch (e) { setErrores(mensajesDe(e)); }` — por ejemplo: "La tarea no admite cambios en el checklist en su estado actual."
- `const iniciada = tarea && tarea.estado !== "PENDIENTE";` — si ya se inició.
- `const marcar = (itemId, completado) => accion(() => api(...))` — marcar un ítem es `POST /api/items/<id>/marcar/`.
- `const iniciar = () => accion(() => api(...))` — iniciar es `POST /api/tareas/<id>/iniciar/`.
- `{tarea.items.map((item) => (<button ...>))}` — un botón por ítem de la lista.
- `disabled={!iniciada || !tarea.abierta || ocupado}` — no se puede marcar si la tarea no se inició, si está cerrada o mientras se envía otra acción. (Igual el servidor lo vuelve a comprobar).
- `onClick={() => marcar(item.id, !item.completado)}` — invierte el valor: si estaba marcado, lo desmarca.
- `role="checkbox" aria-checked={item.completado}` — accesibilidad: se anuncia como casilla de verificación.
- `{item.completado && <Icon name="check" />}` — `&&` dibuja el ícono solo si el ítem está completado.
- `{item.obligatorio && <b ...>*</b>}` — un asterisco en los obligatorios.

### 10.4 `empleado/Evidencias.tsx` — validar fotos en el teléfono y enviarlas

```tsx
const MAX_FOTOS = 10;
const MAX_BYTES = 10 * 1024 * 1024;
const TIPOS = ["image/jpeg", "image/png"];

const agregar = (lista: FileList | null) => {
  if (!lista) return;
  const nuevos: Foto[] = [];
  const problemas: string[] = [];
  for (const archivo of Array.from(lista)) {
    if (!TIPOS.includes(archivo.type)) problemas.push(`${archivo.name}: solo se permiten fotos JPG o PNG.`);
    else if (archivo.size > MAX_BYTES) problemas.push(`${archivo.name}: la foto supera los 10 MB.`);
    else nuevos.push({ archivo, url: URL.createObjectURL(archivo) });
  }
  const espacio = MAX_FOTOS - fotos.length;
  if (nuevos.length > espacio) problemas.push(`Puedes adjuntar hasta ${MAX_FOTOS} fotos por entrega.`);
  setFotos([...fotos, ...nuevos.slice(0, Math.max(0, espacio))]);
  setErrores(problemas);
};

const enviar = async () => {
  const datos = new FormData();
  fotos.forEach((f) => datos.append("fotos", f.archivo));
  datos.append("comentario", comentario.trim());
  setEnviando(true);
  try {
    await api(`tareas/${id}/entregas/`, { method: "POST", body: datos });
    navigate(`/tareas/${id}/entregas`, { replace: true, state: { enviada: true } });
  } catch (e) {
    setErrores(mensajesDe(e));
  } finally {
    setEnviando(false);
  }
};

<input ref={camara} type="file" accept="image/jpeg,image/png" capture="environment" hidden onChange={(e) => { agregar(e.target.files); e.target.value = ""; }} />
```

- `MAX_FOTOS`, `MAX_BYTES`, `TIPOS` — los mismos límites que el servidor. Se validan **también aquí** para avisar al instante y no gastar datos móviles subiendo una foto que será rechazada.
- `const agregar = (lista: FileList | null) => {` — se llama cuando el usuario toma o elige fotos.
- `for (const archivo of Array.from(lista)) {` — recorre cada archivo elegido.
- `if (!TIPOS.includes(archivo.type)) problemas.push(...)` — rechaza formatos que no sean JPG o PNG.
- `else if (archivo.size > MAX_BYTES) problemas.push(...)` — rechaza las de más de 10 MB.
- `else nuevos.push({ archivo, url: URL.createObjectURL(archivo) });` — acepta la foto y crea una URL temporal para mostrar la vista previa sin subirla todavía.
- `const espacio = MAX_FOTOS - fotos.length;` — cuántas fotos más caben.
- `setFotos([...fotos, ...nuevos.slice(0, Math.max(0, espacio))]);` — agrega las nuevas sin pasarse de 10. `...` (spread) copia los elementos de un arreglo dentro de otro.
- `const enviar = async () => {` — al pulsar "Solicitar revisión".
- `const datos = new FormData();` — un "sobre" para enviar archivos.
- `fotos.forEach((f) => datos.append("fotos", f.archivo));` — mete cada foto con el mismo nombre `fotos` (Django las recibe como una lista).
- `datos.append("comentario", comentario.trim());` — el comentario.
- `await api(`tareas/${id}/entregas/`, { method: "POST", body: datos });` — envía todo a `PresentarView`.
- `navigate(..., { state: { enviada: true } })` — si salió bien, va al historial de entregas y le pasa un dato para que muestre "Entrega enviada a revisión".
- `<input type="file" accept="image/jpeg,image/png" capture="environment" hidden ...>` — un selector de archivos oculto. `capture="environment"` abre directamente la **cámara trasera** del teléfono. El botón visible "Tomar foto" hace clic en este input con `camara.current?.click()`.
- `e.target.value = ""` — limpia el input para que se pueda volver a elegir la misma foto.

### 10.5 `admin/Tareas.tsx` — filtros guardados en la URL

```tsx
const [params, setParams] = useSearchParams();
const filtro = (clave: string) => params.get(clave) ?? "";
const pagina = Number(params.get("page") ?? 1);
const ruta = `tareas/${query({ q: filtro("q"), estado: filtro("estado"), prioridad: filtro("prioridad"), empleado: filtro("empleado"), desde: filtro("desde"), hasta: filtro("hasta"), page: pagina > 1 ? pagina : "" })}`;
const { datos, errores, cargando } = useApi<Pagina<TareaResumen>>(ruta);

function cambiar(clave: string, valor: string) {
  const nuevos = new URLSearchParams(params);
  if (valor) nuevos.set(clave, valor);
  else nuevos.delete(clave);
  if (clave !== "page") nuevos.delete("page");
  setParams(nuevos, { replace: true });
}
```

- `const [params, setParams] = useSearchParams();` — lee y cambia los parámetros de la URL (lo que va después de `?`).
- `const filtro = (clave) => params.get(clave) ?? "";` — atajo para leer un filtro.
- `const pagina = Number(params.get("page") ?? 1);` — la página actual (1 si no se indica).
- `const ruta = `tareas/${query({...})}`;` — arma la ruta de la API con los filtros: `tareas/?estado=PENDIENTE&prioridad=ALTA`. `query()` (de `lib/api.ts`) omite los vacíos.
- `useApi<Pagina<TareaResumen>>(ruta)` — como la ruta cambia con cada filtro, `useApi` recarga solo.
- `function cambiar(clave, valor) {` — se llama al cambiar un filtro.
- `const nuevos = new URLSearchParams(params);` — copia los parámetros actuales.
- `if (valor) nuevos.set(clave, valor); else nuevos.delete(clave);` — pone o quita el filtro.
- `if (clave !== "page") nuevos.delete("page");` — al cambiar un filtro, vuelve a la página 1.
- `setParams(nuevos, { replace: true });` — actualiza la URL. Así los filtros **sobreviven** a recargar la página y se pueden compartir con un enlace.

### 10.6 `admin/RevisarEntrega.tsx` — aprobar o devolver

```tsx
const revisar = async (accion: "aprobar" | "devolver") => {
  setOcupado(true);
  try {
    await api(`entregas/${id}/${accion}/`, { method: "POST", body: { observaciones } });
    refrescar();
    if (accion === "devolver") return navigate("/entregas", { replace: true });
    setAprobada(true);
    setErrores([]);
    recargar();
  } catch (err) {
    setErrores(mensajesDe(err));
  } finally {
    setOcupado(false);
  }
};
...
<button onClick={() => revisar("devolver")} disabled={ocupado || !observaciones.trim()}>Confirmar devolución</button>
```

- `const revisar = async (accion: "aprobar" | "devolver") => {` — el tipo `"aprobar" | "devolver"` solo permite esas dos palabras; TypeScript avisa si se escribe otra.
- `await api(`entregas/${id}/${accion}/`, {...})` — llama a `/api/entregas/<id>/aprobar/` o `/devolver/` (el recorrido completo está en el [índice](../EXPLICACION.md#42-recorrido-completo-de-un-clic-aprobar-entrega)).
- `refrescar();` — actualiza la sesión para que el contador de "Entregas en revisión" del menú baje.
- `if (accion === "devolver") return navigate("/entregas", ...)` — tras devolver, vuelve a la bandeja.
- `setAprobada(true); ... recargar();` — tras aprobar, muestra el aviso verde y recarga la entrega (ahora con estado "Aprobada").
- `catch (err) { setErrores(mensajesDe(err)); }` — por ejemplo: "Esta entrega ya fue revisada."
- `disabled={ocupado || !observaciones.trim()}` — el botón "Confirmar devolución" está desactivado mientras la observación esté vacía (regla 3, también verificada en el servidor).

---

## Cómo se conecta con lo demás

| Pantalla | Rutas de la API que usa | Modelo / método en Django |
|---|---|---|
| `Login` | `POST /api/sesion/` | `cuentas.api.SesionView` + `LoginForm` |
| `MisTareas` | `GET /api/mis-tareas/` | `tareas.api.MisTareasView` |
| `empleado/TareaDetalle` | `GET /api/tareas/:id/`, `POST /api/tareas/:id/iniciar/`, `POST /api/items/:id/marcar/` | `Tarea.iniciar()`, `ItemChecklist.marcar()` |
| `Evidencias` | `POST /api/tareas/:id/entregas/` | `Entrega.presentar()` |
| `RevisarEntrega` | `GET /api/entregas/:id/`, `POST …/aprobar/`, `POST …/devolver/` | `Entrega.aprobar()`, `Entrega.devolver()` |
| `MisViaticos` / `admin/Viaticos` | `GET /api/viaticos/` | `viaticos.api.ViaticosView` |
| `SolicitarViatico` | `POST /api/viaticos/` | `Viatico.solicitar()` |
| `RegistrarGasto` | `POST /api/viaticos/:id/gastos/` | `Viatico.registrar_gasto()` |
| `admin/ViaticoDetalle` | `POST /api/viaticos/:id/autorizar/`, `…/rechazar/`, `…/anticipo/`, `…/liquidar/`, `POST /api/gastos/:id/aprobar/` o `…/rechazar/` | `Viatico.autorizar()`, `rechazar()`, `entregar_anticipo()`, `liquidar()`, `Gasto.aprobar()`, `Gasto.rechazar()` |
| `TareaForm` | `GET /api/tareas/opciones/`, `POST /api/tareas/`, `PATCH /api/tareas/:id/` | `Tarea.crear_checklist()`, `actualizar_checklist()`, `registrar_asignacion()` |
| `Servicios` | `/api/servicios/…` | `TipoServicio.eliminar()`, `guardar_plantilla()` |
| `Usuarios` | `/api/usuarios/…` | `UsuarioAdminSerializer` |
| `Panel` / `Reportes` | `GET /api/panel/`, `GET /api/reportes/:tipo/` | `reportes.servicios` |
| `Historial` | `GET /api/historial/` | `historial.api.HistorialView` |
| `Notificaciones` | `GET /api/notificaciones/`, `POST …/:id/leer/`, `POST …/leer-todas/` | `historial.api` |

[← Anterior: Frontend base](09-frontend-base.md) · [Volver al índice](../EXPLICACION.md)

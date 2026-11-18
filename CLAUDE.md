# TaskControl — gestión de tareas y viáticos (Django + React)

## Stack
- Backend: Python 3.12, Django 5.2, Django REST Framework, SQLite, Pillow. Sin Celery.
- Frontend: React 19 + TypeScript 5.7 + Vite 8 + Tailwind CSS v4 (`@tailwindcss/vite`, sin tailwind.config ni PostCSS), pnpm. Diseño base de Figma Make.
- Toda la interfaz es la SPA de React (ya no hay plantillas Django; `/` redirige a `/app/`). El diseño de referencia es el export de Figma Make «TaskControl web app mockup».

## Apps
cuentas, configuracion, tareas, entregas, viaticos, historial, reportes. Proyecto: gestion_campo. Frontend en `frontend/`.

## Arquitectura frontend
- SPA en `frontend/` (estructura Figma Make: `src/main.tsx`, `src/App.tsx`, `src/index.css`, alias `@` → `src`). Rutas con React Router.
- API JSON en `/api/` con DRF: un `api.py` (serializers + vistas) y `urls_api.py` por app. Autenticación por sesión de Django + CSRF; mismo origen (proxy de Vite a Django en desarrollo, Django sirve el build en producción).
- El servidor decide todo: permisos, filtro por empresa (regla 5) y transiciones de estado. React solo presenta y envía; ocultar un botón nunca sustituye al permiso en la API.
- Las vistas de la API llaman a los métodos del modelo (aprobar(), devolver(), liquidar()…); los `ValidationError` se devuelven como 400 con el mensaje en español y React los muestra.
- Archivos (fotos, comprobantes) por endpoints protegidos, nunca por `/media/` directo. Exportación CSV por la API.
- Montos como string decimal en JSON (nunca float); fechas ISO en la API y dd/mm/aaaa en pantalla (`Intl` con `es-DO` y zona America/Santo_Domingo).
- Componentes con export default; utilidades de Tailwind en JSX; tema (colores, fuentes) en `src/index.css` con `@theme`.
- La SPA vive en `/app/` (React Router con basename `/app`). Desarrollo: `pnpm dev:todo` desde `frontend/` (`runserver` en :8000 + Vite en :5173; abrir http://localhost:5173/app/; el proxy manda lo demás a Django). Producción: `pnpm build` y Django sirve `frontend/dist` en `/static/app/`.
- Menús en `src/lib/navegacion.ts`. Una misma ruta puede mostrar pantalla distinta por rol (`PorRol` en `App.tsx`); pantallas en `src/pages/admin` y `src/pages/empleado`.
- Las notificaciones e historial enlazan a rutas de la SPA (`/app/tareas/<id>`, `/app/entregas/<id>`, `/app/viaticos/<id>`), ver `historial/servicios.py`.
- Administrador: armazón de escritorio (menú lateral, cajón bajo `lg`). Empleado: armazón de teléfono (barra inferior).

## Modelos (resumen)
- Empresa(nombre, rnc, telefono, activa)
- Usuario(AbstractUser): empresa FK, rol {EMPLEADO, ADMINISTRADOR}
- TipoServicio(empresa, nombre); PlantillaChecklist(tipo_servicio, nombre, activa); ItemPlantilla(plantilla, descripcion, orden, obligatorio)
- Tarea(empresa, tipo_servicio, asignado_a, creado_por, titulo, descripcion, ubicacion, criterios_aceptacion, prioridad {BAJA,MEDIA,ALTA,URGENTE}, fecha_limite, estado {PENDIENTE,EN_PROCESO,EN_REVISION,DEVUELTA,COMPLETADA,CANCELADA}, completada_en)
- ItemChecklist(tarea, descripcion, orden, obligatorio, completado, marcado_en)
- Entrega(tarea, empleado, version, comentario, estado {EN_REVISION,APROBADA,DEVUELTA}, presentada_en); Evidencia(entrega, archivo ImageField, descripcion); Revision(entrega 1:1, revisor, decision, observaciones)
- Viatico(tarea, empleado, autorizado_por, concepto, monto_solicitado, monto_aprobado, anticipo_entregado, estado {SOLICITADO,AUTORIZADO,RECHAZADO,ANTICIPO_ENTREGADO,EN_COMPROBACION,LIQUIDADO}); Gasto(viatico, categoria, fecha, monto, comprobante, estado {PENDIENTE,APROBADO,RECHAZADO}, observacion); Liquidacion(viatico 1:1, total_gastos, total_anticipo, saldo, resultado {REEMBOLSO,DEVOLUCION,SALDADO})
- Historial(empresa, usuario, entidad, entidad_id, accion, detalle, fecha); Notificacion(usuario, mensaje, enlace, leida)
- Montos: DecimalField(12,2) en RD$.

## Reglas de negocio
1. La tarea pasa a COMPLETADA solo cuando un administrador aprueba la entrega.
2. Para solicitar revisión: todos los ítems obligatorios marcados y al menos 1 foto.
3. Devolver, rechazar un viático o rechazar un gasto exige observación.
4. Cada devolución crea una nueva versión de la entrega; nunca se borran versiones ni evidencias.
5. El empleado solo ve sus registros; el administrador, los de su empresa (filtrar siempre por empresa).
6. Saldo = gastos aprobados − anticipo (> 0 reembolso, < 0 devolución, = 0 saldado). No se liquida con gastos pendientes.
7. El anticipo no puede superar el monto aprobado.
8. Todo cambio de estado se registra en Historial.

## Convenciones
- Interfaz en español, zona horaria America/Santo_Domingo, fechas dd/mm/aaaa.
- Mobile-first (el empleado usa el teléfono). Botones de al menos 44 px.
- Permisos con mixins/decoradores o permission classes de DRF en el servidor, nunca solo en la plantilla o en React.
- Lógica de estados en métodos del modelo (aprobar(), devolver(), liquidar()), no en las vistas ni en la API.
- Fotos JPG/PNG de hasta 10 MB, redimensionadas a 1920 px con Pillow (validar también en el cliente antes de subir).
- Pruebas con django.test (también para la API) para reglas 1, 2, 5 y 6.
- Frontend: `pnpm build` sin errores de TypeScript; strings con apóstrofo entre comillas dobles.

## Forma de trabajar
- Responde solo con código y una lista breve de archivos cambiados. Sin explicaciones salvo que las pida.
- No repitas archivos completos que no cambiaron; edita solo lo necesario.
- Un módulo por vez. Al terminar, corre las migraciones y las pruebas (y `pnpm build` si tocaste `frontend/`), y para.
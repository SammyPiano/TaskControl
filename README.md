# CampoTrack

Gestión de tareas de campo y viáticos. Backend Django + API REST, frontend React (SPA en `/app/`), base de datos SQLite.

## Requisitos

- Python 3.12 o superior
- Node.js 20 o superior y [pnpm](https://pnpm.io/installation)

## Primera vez

```bash
cd frontend
pnpm preparar
```

Crea `.venv`, instala las dependencias de Python y del frontend, copia `.env.example` a `.env` y aplica las migraciones. Se puede repetir sin problema.

Luego, para tener con qué entrar:

```bash
pnpm django cargar_demo       # empresa de demostración (usuarios y clave en la salida)
# o
pnpm django createsuperuser
```

## Día a día (desde `frontend/`)

| Comando | Qué hace |
|---|---|
| `pnpm dev:todo` | Django (:8000) + Vite (:5173) en una terminal, con recarga al instante. Abrir http://localhost:5173/app/ |
| `pnpm servir` | Compila el frontend y lo sirve solo Django. Abrir http://localhost:8000/app/ |
| `pnpm django <comando>` | Cualquier comando de `manage.py` con el Python de `.venv` (`migrate`, `test`, `shell`…) |

`Ctrl+C` detiene todo.

Usa `pnpm dev:todo` mientras cambias pantallas de React; `pnpm servir` cuando solo usas la app o tocas el backend.

## Pruebas

```bash
pnpm django test
pnpm build
```

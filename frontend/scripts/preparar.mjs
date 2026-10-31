// Primera vez: entorno virtual, dependencias, .env y migraciones. Se puede repetir sin problema.
import { copyFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { RAIZ, VENV, ejecutar, pythonDelSistema, pythonDelVenv } from "./python.mjs";

function paso(texto) {
  console.log(`\n▸ ${texto}`);
}

if (!pythonDelVenv()) {
  const sistema = pythonDelSistema();
  if (!sistema) {
    console.error("Se necesita Python 3.12 o superior instalado (python3, python o py).");
    process.exit(1);
  }
  paso("Creando entorno virtual en .venv");
  ejecutar(sistema[0], [...sistema.slice(1), "-m", "venv", VENV]);
}
const python = pythonDelVenv();

paso("Instalando dependencias de Python");
ejecutar(python, ["-m", "pip", "install", "--upgrade", "pip"]);
ejecutar(python, ["-m", "pip", "install", "-r", "requirements.txt"]);

const env = join(RAIZ, ".env");
if (!existsSync(env)) {
  paso("Creando .env desde .env.example");
  copyFileSync(join(RAIZ, ".env.example"), env);
}

paso("Aplicando migraciones (SQLite)");
ejecutar(python, ["manage.py", "migrate"]);

paso("Instalando dependencias del frontend");
// En Windows pnpm es un .cmd y necesita shell
ejecutar("pnpm", ["install"], { cwd: join(RAIZ, "frontend"), shell: process.platform === "win32" });

console.log(`
Listo. Siguientes pasos (desde frontend/):
  pnpm django cargar_demo      datos de demostración (opcional)
  pnpm django createsuperuser  o crear su propio usuario
  pnpm dev:todo                arrancar Django + Vite → http://localhost:5173/app/
`);

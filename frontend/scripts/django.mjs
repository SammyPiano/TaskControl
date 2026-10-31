// Ejecuta manage.py con el Python de .venv: pnpm django <comando> [args]
import { spawn } from "node:child_process";
import { join } from "node:path";
import { RAIZ, pythonDelVenv } from "./python.mjs";

const python = pythonDelVenv();
if (!python) {
  console.error("No se encontró el entorno virtual (.venv). Ejecute primero «pnpm preparar».");
  process.exit(1);
}

const hijo = spawn(python, [join(RAIZ, "manage.py"), ...process.argv.slice(2)], { cwd: RAIZ, stdio: "inherit" });
for (const senal of ["SIGINT", "SIGTERM"]) process.on(senal, () => hijo.kill(senal));
hijo.on("exit", (codigo) => process.exit(codigo ?? 0));

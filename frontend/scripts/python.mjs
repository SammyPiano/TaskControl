// Ubica el Python del entorno virtual (.venv en la raíz) en Mac/Linux y Windows.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const VENV = join(RAIZ, ".venv");

export function pythonDelVenv() {
  const candidatos = [join(VENV, "bin", "python"), join(VENV, "Scripts", "python.exe")];
  return candidatos.find((ruta) => existsSync(ruta)) ?? null;
}

// Python del sistema 3.12 o superior, para crear el entorno virtual.
export function pythonDelSistema() {
  const candidatos = [["python3"], ["python"], ["py", "-3"]];
  for (const [cmd, ...args] of candidatos) {
    const r = spawnSync(cmd, [...args, "-c", "import sys; print(sys.version_info >= (3, 12))"], {
      encoding: "utf-8",
    });
    if (r.status === 0 && r.stdout.trim() === "True") return [cmd, ...args];
  }
  return null;
}

export function ejecutar(cmd, args, opciones = {}) {
  const r = spawnSync(cmd, args, { cwd: RAIZ, stdio: "inherit", ...opciones });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

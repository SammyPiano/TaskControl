import type { ReactElement } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router";
import Logo from "@/components/Logo";
import AdminLayout from "@/layouts/AdminLayout";
import MobileLayout from "@/layouts/MobileLayout";
import { esAdministrador, SesionProvider, useSesion } from "@/lib/sesion";
import Login from "@/pages/Login";
import NoEncontrado from "@/pages/NoEncontrado";
import Notificaciones from "@/pages/Notificaciones";
import Perfil from "@/pages/Perfil";
import Historial from "@/pages/admin/Historial";
import Panel from "@/pages/admin/Panel";
import Reportes from "@/pages/admin/Reportes";
import RevisarEntrega from "@/pages/admin/RevisarEntrega";
import Revisiones from "@/pages/admin/Revisiones";
import Servicios from "@/pages/admin/Servicios";
import TareaAdmin from "@/pages/admin/TareaDetalle";
import TareaForm from "@/pages/admin/TareaForm";
import Tareas from "@/pages/admin/Tareas";
import Usuarios from "@/pages/admin/Usuarios";
import ViaticoAdmin from "@/pages/admin/ViaticoDetalle";
import Viaticos from "@/pages/admin/Viaticos";
import Entregas from "@/pages/empleado/Entregas";
import Evidencias from "@/pages/empleado/Evidencias";
import MisTareas from "@/pages/empleado/MisTareas";
import MisViaticos from "@/pages/empleado/MisViaticos";
import RegistrarGasto from "@/pages/empleado/RegistrarGasto";
import SolicitarViatico from "@/pages/empleado/SolicitarViatico";
import TareaEmpleado from "@/pages/empleado/TareaDetalle";
import ViaticoEmpleado from "@/pages/empleado/ViaticoDetalle";

/** Exige sesión y elige el armazón según el rol: escritorio (admin) o teléfono (empleado). */
function Protegido() {
  const { usuario, cargando } = useSesion();
  const { pathname } = useLocation();
  if (cargando) {
    return <div className="flex min-h-dvh items-center justify-center bg-surface"><Logo /></div>;
  }
  if (!usuario) return <Navigate to="/ingresar" replace state={{ desde: pathname }} />;
  return esAdministrador(usuario) ? <AdminLayout /> : <MobileLayout />;
}

/** Misma ruta, pantalla distinta por rol. Sin pantalla para el rol → inicio. El permiso real lo decide la API. */
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
            <Route path="tareas" element={<PorRol admin={<Tareas />} empleado={<Navigate to="/" replace />} />} />
            <Route path="tareas/nueva" element={<PorRol admin={<TareaForm />} />} />
            <Route path="tareas/:id" element={<PorRol admin={<TareaAdmin />} empleado={<TareaEmpleado />} />} />
            <Route path="tareas/:id/editar" element={<PorRol admin={<TareaForm />} />} />
            <Route path="tareas/:id/evidencias" element={<PorRol empleado={<Evidencias />} />} />
            <Route path="tareas/:id/entregas" element={<PorRol empleado={<Entregas />} />} />
            <Route path="entregas" element={<PorRol admin={<Revisiones />} />} />
            <Route path="entregas/:id" element={<PorRol admin={<RevisarEntrega />} />} />
            <Route path="viaticos" element={<PorRol admin={<Viaticos />} empleado={<MisViaticos />} />} />
            <Route path="viaticos/solicitar" element={<PorRol empleado={<SolicitarViatico />} />} />
            <Route path="viaticos/:id" element={<PorRol admin={<ViaticoAdmin />} empleado={<ViaticoEmpleado />} />} />
            <Route path="viaticos/:id/gasto" element={<PorRol empleado={<RegistrarGasto />} />} />
            <Route path="usuarios" element={<PorRol admin={<Usuarios />} />} />
            <Route path="servicios" element={<PorRol admin={<Servicios />} />} />
            <Route path="reportes" element={<PorRol admin={<Reportes />} />} />
            <Route path="historial" element={<PorRol admin={<Historial />} />} />
            <Route path="notificaciones" element={<Notificaciones />} />
            <Route path="perfil" element={<Perfil />} />
          </Route>
          <Route path="*" element={<NoEncontrado />} />
        </Routes>
      </BrowserRouter>
    </SesionProvider>
  );
}

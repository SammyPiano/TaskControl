"""
Datos de demostración con los ejemplos del diseño de Figma (Servicios Técnicos del Caribe).
Todo pasa por los métodos del modelo, así que historial, notificaciones y estados quedan coherentes.

    python manage.py cargar_demo
"""

import unicodedata
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from configuracion.models import guardar_plantilla, TipoServicio
from cuentas.models import Empresa, Usuario
from entregas.models import Entrega
from historial.models import Notificacion
from tareas.models import Tarea
from viaticos.models import Gasto, Viatico

RNC = "131000999"
CLAVE = "TaskControl2025"
D = Decimal

COLORES = [(0, 106, 112), (40, 104, 178), (35, 122, 72), (182, 75, 18), (100, 116, 139), (154, 101, 0)]


def foto(texto, n=0):
    """Foto JPG generada (no depende de internet). Sin tildes: la fuente por defecto de Pillow no las tiene."""
    texto = unicodedata.normalize("NFKD", texto.replace("·", "-")).encode("ascii", "ignore").decode()
    imagen = Image.new("RGB", (1200, 800), COLORES[n % len(COLORES)])
    dibujo = ImageDraw.Draw(imagen)
    for i in range(0, 1200, 60):
        dibujo.line([(i, 800), (i + 400, 0)], fill=tuple(min(c + 25, 255) for c in COLORES[n % len(COLORES)]), width=18)
    dibujo.rectangle([60, 640, 1140, 740], fill=(255, 255, 255))
    dibujo.text((90, 675), texto, fill=(31, 41, 51), font_size=40)
    salida = BytesIO()
    imagen.save(salida, "JPEG", quality=85)
    return ContentFile(salida.getvalue(), name=f"demo_{n}.jpg")


class Command(BaseCommand):
    help = "Carga una empresa de demostración con usuarios, tareas, entregas y viáticos del diseño."

    def handle(self, *args, **opciones):
        if Empresa.objects.filter(rnc=RNC).exists():
            raise CommandError("Los datos de demostración ya están cargados (empresa RNC 131000999).")
        with transaction.atomic():
            self.cargar()
        self.stdout.write(self.style.SUCCESS(
            "Datos de demostración cargados.\n"
            f"  Administradora: laura@stcaribe.com / {CLAVE}\n"
            f"  Empleado:       cmartinez@stcaribe.com / {CLAVE}"
        ))

    def usuario(self, username, nombre, apellido, rol=Usuario.Rol.EMPLEADO, **extra):
        return Usuario.objects.create_user(
            username, email=f"{username}@stcaribe.com", password=CLAVE, first_name=nombre, last_name=apellido,
            empresa=self.empresa, rol=rol, **extra,
        )

    def tarea(self, titulo, tipo, empleado, prioridad, dias, ubicacion, descripcion, criterios, marcar=0):
        tarea = Tarea.objects.create(
            empresa=self.empresa, tipo_servicio=tipo, asignado_a=empleado, creado_por=self.laura, titulo=titulo,
            descripcion=descripcion, ubicacion=ubicacion, criterios_aceptacion=criterios, prioridad=prioridad,
            fecha_limite=self.hoy + timedelta(days=dias),
        )
        tarea.copiar_plantilla(tipo.plantillas.get(activa=True))
        tarea.registrar_asignacion(self.laura)
        for item in tarea.items.all()[:marcar]:
            item.marcar(True)
        return tarea

    def entregar(self, tarea, fotos, comentario="", hace_min=0):
        tarea.items.update(completado=True, marcado_en=timezone.now())
        entrega = Entrega.presentar(
            tarea, tarea.asignado_a, [(foto(f"{tarea.titulo[:38]} · {i + 1}", i), "") for i in range(fotos)], comentario
        )
        if hace_min:
            Entrega.objects.filter(pk=entrega.pk).update(presentada_en=timezone.now() - timedelta(minutes=hace_min))
        return entrega

    def gasto(self, viatico, categoria, monto, detalle, estado=None):
        g = viatico.registrar_gasto(viatico.empleado, foto(f"Comprobante · {detalle}", 4), categoria, self.hoy, D(monto), detalle)
        if estado == "APROBADO":
            g.aprobar(self.laura)
        return g

    def cargar(self):
        self.hoy = timezone.localdate()
        self.empresa = Empresa.objects.create(nombre="Servicios Técnicos del Caribe", rnc=RNC, telefono="(809) 555-0100")
        self.laura = self.usuario("laura", "Laura", "Méndez", Usuario.Rol.ADMINISTRADOR, cargo="Administradora", zona="Santo Domingo")
        Usuario.objects.filter(pk=self.laura.pk).update(email="laura@stcaribe.com")
        carlos = self.usuario("cmartinez", "Carlos", "Martínez", cargo="Técnico de mantenimiento", telefono="(809) 555-0148", zona="Santo Domingo Este")
        ana = self.usuario("aperez", "Ana", "Pérez", cargo="Técnica electricista", telefono="(829) 555-0172", zona="Santiago")
        jose = self.usuario("jramirez", "José", "Ramírez", cargo="Técnico plomero", telefono="(849) 555-0133", zona="La Romana")
        miguel = self.usuario("msantos", "Miguel", "Santos", cargo="Auxiliar de limpieza", zona="Santo Domingo")
        rosa = self.usuario("rdiaz", "Rosa", "Díaz", cargo="Técnica de refrigeración", zona="Santo Domingo Oeste")

        tipos = {}
        for nombre, items in {
            "Instalación de A/C": ["Verificar voltaje y amperaje", "Limpiar filtros y bandeja de drenaje", "Comprobar nivel y soporte", "Registrar temperatura final", ("Fotografiar placa del equipo", False), "Drenaje sin fugas"],
            "Mantenimiento de A/C": ["Verificar voltaje del equipo", "Limpiar filtros y bandeja", "Revisar presión del refrigerante", ("Comprobar drenaje", False), "Registrar temperatura final"],
            "Mantenimiento de planta": ["Inspeccionar área de trabajo", "Verificar nivel de aceite y refrigerante", "Probar arranque automático", "Revisar baterías", "Registrar horas de uso", "Registrar evidencia final"],
            "Reparación hidráulica": ["Identificar la avería", "Cerrar suministro de agua", "Reemplazar piezas dañadas", "Prueba de presión", "Registrar evidencia final"],
            "Limpieza profunda": ["Inspeccionar áreas", "Limpieza de superficies", "Limpieza de cristales", "Desinfección de baños", ("Retiro de desechos", False)],
        }.items():
            tipos[nombre] = TipoServicio.objects.create(empresa=self.empresa, nombre=nombre)
            guardar_plantilla(tipos[nombre], [
                {"descripcion": i[0], "obligatorio": i[1]} if isinstance(i, tuple) else {"descripcion": i} for i in items
            ])

        A, M, B, U = Tarea.Prioridad.ALTA, Tarea.Prioridad.MEDIA, Tarea.Prioridad.BAJA, Tarea.Prioridad.URGENTE

        # Carlos (empleado de la vista móvil)
        ac = self.tarea("Mantenimiento preventivo de A/C", tipos["Mantenimiento de A/C"], carlos, A, 0,
                        "Clínica Central · Av. Bolívar 302, Gazcue, Santo Domingo",
                        "Realizar mantenimiento preventivo de dos unidades de aire acondicionado en el área de recepción y validar su correcto funcionamiento.",
                        "Equipo sin ruidos ni vibraciones.\nTemperatura de salida entre 16 °C y 20 °C.\nAdjuntar mínimo 1 fotografía.", marcar=3)
        self.tarea("Reparación de bomba de agua", tipos["Reparación hidráulica"], carlos, U, -1,
                   "Residencial Las Palmas · Piantini, Santo Domingo",
                   "La bomba del edificio no arranca. Diagnosticar y reparar.", "Bomba operando sin ruidos.\nPresión estable en todos los pisos.")
        limpieza = self.tarea("Limpieza profunda de oficinas", tipos["Limpieza profunda"], carlos, M, 1,
                              "Grupo Arco · Naco, Santo Domingo", "Limpieza profunda del piso 3 antes de la auditoría.",
                              "Superficies sin polvo.\nBaños desinfectados.\nFotos de cada área.")
        split = self.tarea("Instalación de aire acondicionado split", tipos["Instalación de A/C"], carlos, U, 2,
                           "Residencial Las Américas · Santo Domingo Este",
                           "Instalar unidad split de 18,000 BTU y verificar el sistema eléctrico y drenaje.",
                           "Equipo nivelado, sin ruidos, temperatura entre 16 °C y 20 °C y drenaje sin fugas.")

        # Viáticos de Carlos (se solicitan antes de cerrar las tareas)
        combustible = Viatico.solicitar(split, carlos, "Combustible y peajes", D("2350"))
        combustible.autorizar(self.laura, D("2350"), D("2000"))
        materiales = Viatico.solicitar(ac, carlos, "Compra de materiales", D("4780"))
        materiales.autorizar(self.laura, D("4200"))
        self.gasto(materiales, Gasto.Categoria.MATERIALES, "3850", "Filtros y refrigerante")
        planta_tarea = self.tarea("Mantenimiento de planta eléctrica", tipos["Mantenimiento de planta"], jose, B, 3,
                                  "Centro Médico Cibao · Santiago", "Mantenimiento trimestral de la planta de emergencia.", "Arranque automático en menos de 10 s.")
        alimentacion_tarea = self.tarea("Revisión de cuarto frío", tipos["Mantenimiento de A/C"], carlos, M, -5,
                                        "Residencial Palma Real · Santo Domingo", "Revisión del cuarto frío del supermercado.", "Temperatura interior bajo 4 °C.")
        alimentacion = Viatico.solicitar(alimentacion_tarea, carlos, "Alimentación jornada extendida", D("850"))
        alimentacion.autorizar(self.laura, D("850"), D("850"))
        self.gasto(alimentacion, Gasto.Categoria.ALIMENTACION, "850", "Almuerzo y cena", "APROBADO")
        alimentacion.liquidar(self.laura)
        self.entregar(alimentacion_tarea, 2, "Cuarto frío a 3 °C.").aprobar(self.laura)

        for categoria, monto, detalle, estado in [
            (Gasto.Categoria.COMBUSTIBLE, "1500", "Estación Isla · Santiago", "APROBADO"),
            (Gasto.Categoria.PEAJE, "350", "Autopista Duarte", None),
            (Gasto.Categoria.ALIMENTACION, "500", "Jornada extendida", None),
        ]:
            self.gasto(combustible, categoria, monto, detalle, estado)
        Viatico.solicitar(planta_tarea, jose, "Transporte a Santiago", D("1800"))

        # Entregas: devuelta, en revisión con versión anterior, y otras en revisión
        self.entregar(limpieza, 2, "Áreas listas.", hace_min=60 * 20).devolver(
            self.laura, "La foto del compresor no permite verificar el número de serie. Adjunta una imagen más clara y registra la temperatura final.")
        self.entregar(split, 2, "Instalación terminada.", hace_min=60 * 18).devolver(self.laura, "Se requieren evidencias más claras del drenaje.")
        self.entregar(split, 4, "Instalación terminada. La temperatura de salida quedó en 18 °C y el cliente validó el funcionamiento.", hace_min=18)

        planta = self.tarea("Mantenimiento preventivo de planta eléctrica", tipos["Mantenimiento de planta"], ana, A, 1,
                            "Centro Médico Cibao · Santiago", "Mantenimiento preventivo de la planta de 150 kW.", "Arranque automático correcto.\nSin fugas de aceite.")
        self.entregar(planta, 6, "Planta probada con carga.", hace_min=46)
        hidraulico = self.tarea("Reparación de sistema hidráulico", tipos["Reparación hidráulica"], jose, M, 2,
                                "Hotel Costa Sur · La Romana", "Fuga en la línea principal del área de piscina.", "Prueba de presión sin pérdidas.")
        self.entregar(hidraulico, 3, "Se reemplazó la válvula principal.", hace_min=120)

        # Tareas completadas y pendientes para el panel y los reportes
        for empleado, tipo, titulo, ubicacion in [
            (carlos, "Mantenimiento de A/C", "Mantenimiento de A/C en recepción", "Torre Empresarial · Piantini"),
            (carlos, "Instalación de A/C", "Instalación de A/C en oficina 4B", "Torre Empresarial · Piantini"),
            (ana, "Mantenimiento de planta", "Revisión de planta de emergencia", "Plaza Central · Santiago"),
            (ana, "Mantenimiento de planta", "Cambio de baterías de planta", "Colegio Las Américas · Santiago"),
            (jose, "Reparación hidráulica", "Reparación de tubería en cocina", "Restaurante Mar Azul · La Romana"),
            (miguel, "Limpieza profunda", "Limpieza post-remodelación", "Banco Popular · Naco"),
            (rosa, "Mantenimiento de A/C", "Mantenimiento de chiller", "Hospital Metropolitano · Santo Domingo Oeste"),
            (rosa, "Instalación de A/C", "Instalación de cassette 24,000 BTU", "Farmacia Carol · Los Alcarrizos"),
        ]:
            t = self.tarea(titulo, tipos[tipo], empleado, M, 4, ubicacion, "Servicio programado.", "Trabajo verificado por el cliente.")
            self.entregar(t, 2, "Servicio completado.").aprobar(self.laura)
        self.entregar(planta_tarea, 3, "Planta en servicio.").aprobar(self.laura)
        self.tarea("Limpieza de ductos de ventilación", tipos["Limpieza profunda"], miguel, M, -2,
                   "Supermercado Bravo · Santo Domingo", "Limpieza de ductos del área de cajas.", "Ductos sin acumulación de polvo.")
        self.tarea("Mantenimiento de A/C en sala de servidores", tipos["Mantenimiento de A/C"], rosa, A, 5,
                   "Grupo Arco · Naco", "Mantenimiento preventivo de las dos unidades de precisión.", "Temperatura de la sala bajo 22 °C.", marcar=2)

        # Algunas notificaciones antiguas ya leídas, para que no todo aparezca como nuevo
        for u in (carlos, self.laura):
            antiguas = list(Notificacion.objects.filter(usuario=u).order_by("-creada_en").values_list("pk", flat=True)[4:])
            Notificacion.objects.filter(pk__in=antiguas).update(leida=True)

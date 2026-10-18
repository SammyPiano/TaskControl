from django.contrib.auth.models import AbstractUser
from django.db import models


class Empresa(models.Model):
    nombre = models.CharField(max_length=150)
    rnc = models.CharField("RNC", max_length=11, unique=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        EMPLEADO = "EMPLEADO", "Empleado"
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
        blank=True,
    )
    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.EMPLEADO)
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    zona = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_empleado(self):
        return self.rol == self.Rol.EMPLEADO

    @property
    def iniciales(self):
        partes = [p for p in (self.first_name, self.last_name) if p] or [self.username]
        return "".join(p[0] for p in partes[:2]).upper()

    @property
    def tiene_empresa_activa(self):
        return self.empresa_id is not None and self.empresa.activa

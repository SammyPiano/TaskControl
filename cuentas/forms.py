from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Usuario


class LoginForm(AuthenticationForm):
    """Acepta el nombre de usuario o el correo electrónico."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "empresa_inactiva": "Su empresa no está activa. Contacte al administrador.",
    }

    def clean(self):
        identificador = (self.cleaned_data.get("username") or "").strip()
        if "@" in identificador:
            usuario = Usuario.objects.filter(email__iexact=identificador).only("username").first()
            if usuario:
                self.cleaned_data["username"] = usuario.username
        return super().clean()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser and not user.tiene_empresa_activa:
            raise ValidationError(self.error_messages["empresa_inactiva"], code="empresa_inactiva")

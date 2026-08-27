"""
Formulários do fluxo de criação de processo e escolha de verificação
(D-09, D-10 — 07-CONTEXT.md).

`MultipleFileInput`/`MultipleFileField` são o par oficial do Django 5 para
upload múltiplo. Nunca instanciar o widget de arquivo nativo passando o
atributo HTML de múltiplos arquivos direto em `attrs`: isso levanta
`ValueError` na definição da classe do formulário — ou seja, no import do
módulo, não na submissão — e derruba `manage.py check`, a suíte inteira e
todo plano que importe `views.py`.
"""

from __future__ import annotations

from django import forms
from django.conf import settings

from . import uploads
from .models import Processo


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = forms.FileField.clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(self, item, initial) for item in data]
        return single_file_clean(self, data, initial)


class NovoProcessoForm(forms.Form):
    nome = forms.CharField(max_length=200, label="Nome do processo")
    documento_unico = forms.FileField(
        required=False,
        label="PDF do processo completo",
        help_text=(
            "Caminho recomendado: envie um único PDF com todo o processo. "
            "O sistema identifica sozinho as peças que o compõem."
        ),
    )
    pecas = MultipleFileField(
        required=False,
        widget=MultipleFileInput(),
        label="Peças separadas",
    )

    def clean(self):
        cleaned_data = super().clean()
        pecas = cleaned_data.get("pecas")
        if not isinstance(pecas, list):
            pecas = [pecas] if pecas else []
        cleaned_data["pecas"] = pecas
        documento_unico = cleaned_data.get("documento_unico")

        if documento_unico and pecas:
            raise forms.ValidationError(
                "Envie o PDF do processo completo ou as peças separadas — não os dois."
            )
        if not documento_unico and not pecas:
            raise forms.ValidationError("Envie ao menos um documento do processo.")

        maximo = settings.SYSDOC_WEB_MAX_ARQUIVOS
        try:
            if documento_unico:
                uploads.validar_conjunto([documento_unico], maximo)
                uploads.validar_arquivo(documento_unico)
            else:
                uploads.validar_conjunto(pecas, maximo)
                for arquivo in pecas:
                    uploads.validar_arquivo(arquivo)
        except uploads.ArquivoRecusado as exc:
            raise forms.ValidationError(exc.messages[0] if exc.messages else str(exc)) from exc

        return cleaned_data


class VerificacaoForm(forms.Form):
    tipo = forms.ChoiceField(
        choices=Processo._meta.get_field("tipo_verificacao").choices,
        widget=forms.RadioSelect,
        label="Tipo de contratação",
    )

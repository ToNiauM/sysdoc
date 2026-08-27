"""
Modelos `Processo`/`AnaliseJob` (D-14, D-15, D-18 — 07-CONTEXT.md).

A `UniqueConstraint` condicional em `AnaliseJob.Meta.constraints` é a
implementação de "uma análise por vez" no nível do banco: duas requisições
concorrentes tentando `AnaliseJob.objects.create()` colidem na constraint,
não num `if` de leitura prévia que uma segunda thread do servidor de
aplicação poderia driblar.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

STATUS_ATIVOS = ("na_fila", "em_execucao")
STATUS_FINAIS = ("concluida", "falhou", "interrompida")


class Processo(models.Model):
    TIPO_VERIFICACAO_CHOICES = [
        ("geral", "Contratação em geral"),
        ("tic", "Solução de TIC"),
    ]

    nome = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    tipo_verificacao = models.CharField(
        max_length=8, blank=True, default="", choices=TIPO_VERIFICACAO_CHOICES
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="processos"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return self.nome


class AnaliseJob(models.Model):
    STATUS_CHOICES = [
        ("na_fila", "Na fila"),
        ("em_execucao", "Em execução"),
        ("concluida", "Concluída"),
        ("falhou", "Falhou"),
        ("interrompida", "Interrompida"),
    ]

    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=16, default="na_fila", choices=STATUS_CHOICES)
    etapa = models.CharField(max_length=120, blank=True, default="")
    itens_concluidos = models.PositiveIntegerField(default=0)
    itens_total = models.PositiveIntegerField(default=0)
    mensagem_erro = models.TextField(blank=True, default="")
    slot = models.PositiveSmallIntegerField(default=1)
    criado_em = models.DateTimeField(auto_now_add=True)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["slot"],
                condition=Q(status__in=STATUS_ATIVOS),
                name="uma_analise_ativa_por_vez",
            )
        ]

    def __str__(self) -> str:
        return f"{self.processo.nome} ({self.status})"

    @property
    def ativo(self) -> bool:
        return self.status in STATUS_ATIVOS

    @property
    def percentual(self) -> int:
        if not self.itens_total:
            return 0
        return int(100 * self.itens_concluidos / self.itens_total)

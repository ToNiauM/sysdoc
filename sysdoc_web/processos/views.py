# Convenção deste app: toda view é decorada com @login_required.
# Não existe view pública além da tela de login (D-07).
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def inicio(request):
    return render(request, "processos/inicio.html", {})

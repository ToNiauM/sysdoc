/*
 * Polling da tela de análise (D-16 — 07-CONTEXT.md).
 *
 * Sem canal push do navegador, sem framework e sem CDN externo. Todo texto
 * vindo do servidor é escrito por atribuição direta de texto no DOM
 * (T-07-06-02) — o conteúdo vem de um job de análise que executou código de
 * terceiros, então nunca é seguro tratá-lo como marcação de página.
 */
(function () {
  "use strict";

  var raiz = document.querySelector("[data-url-situacao]");
  if (!raiz) {
    return;
  }

  var url = raiz.getAttribute("data-url-situacao");
  if (!url) {
    return;
  }

  var INTERVALO_MS = 2000;
  var LIMITE_FALHAS_CONSECUTIVAS = 3;
  var MENSAGEM_SEM_SERVIDOR = "Não foi possível falar com o servidor. Atualize a página.";

  var elementoSituacao = document.getElementById("situacao");
  var elementoEtapa = document.getElementById("etapa");
  var elementoBarra = document.getElementById("barra");
  var elementoErro = document.getElementById("erro");

  var falhasConsecutivas = 0;
  var temporizador = null;
  var emPausa = false;

  function destinoSeguro(destino) {
    // Recusa qualquer destino absoluto ou com esquema (T-07-06-03) — só
    // navega para um caminho relativo gerado por `reverse()` no servidor.
    return typeof destino === "string" && destino.startsWith("/");
  }

  function mostrarErro(mensagem) {
    if (!elementoErro) {
      return;
    }
    elementoErro.textContent = mensagem;
    elementoErro.hidden = false;
  }

  function aplicarSituacao(dados) {
    if (elementoSituacao) {
      elementoSituacao.textContent = dados.situacao;
    }
    if (elementoEtapa) {
      elementoEtapa.textContent = dados.etapa;
    }
    if (elementoBarra) {
      elementoBarra.style.width = dados.percentual + "%";
    }
  }

  function agendarProximoCiclo() {
    temporizador = window.setTimeout(iniciarCiclo, INTERVALO_MS);
  }

  function tratarSucesso(dados) {
    falhasConsecutivas = 0;
    aplicarSituacao(dados);

    if (!dados.concluida) {
      agendarProximoCiclo();
      return;
    }

    if (dados.sucesso && destinoSeguro(dados.url_resultado)) {
      window.location.assign(dados.url_resultado);
      return;
    }

    if (!dados.sucesso) {
      mostrarErro(dados.mensagem || "Não foi possível concluir a análise.");
    }
  }

  function tratarFalha() {
    falhasConsecutivas += 1;
    if (falhasConsecutivas >= LIMITE_FALHAS_CONSECUTIVAS) {
      mostrarErro(MENSAGEM_SEM_SERVIDOR);
      return;
    }
    agendarProximoCiclo();
  }

  function consultar() {
    fetch(url, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    })
      .then(function (resposta) {
        if (!resposta.ok) {
          throw new Error("resposta http " + resposta.status);
        }
        return resposta.json();
      })
      .then(tratarSucesso)
      .catch(tratarFalha);
  }

  function iniciarCiclo() {
    if (document.visibilityState === "hidden") {
      emPausa = true;
      return;
    }
    emPausa = false;
    consultar();
  }

  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible" && emPausa) {
      emPausa = false;
      window.clearTimeout(temporizador);
      consultar();
    }
  });

  iniciarCiclo();
})();

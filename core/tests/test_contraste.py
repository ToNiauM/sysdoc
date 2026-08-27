"""Prova de `core/tests/contraste.py` — a fonte única da fórmula WCAG 2.x
deste repositório (DS-03/DS-04/QA-03).

Duas famílias de asserção, deliberadamente separadas:

1. **Âncoras matemáticas** (21:1, 1:1, simetria, luminância 0,0 e 1,0) — são
   propriedades do algoritmo, não medições. Valem com igualdade estrita: se
   uma delas se mover, a implementação deixou de ser WCAG 2.x.
2. **Pares medidos à mão no `07-REVIEW.md`** (CR-02 e CR-03) — a revisão
   publicou 2 casas decimais, então valem com `delta=0.05`. Cada asserção cita
   a origem no comentário. Essa rastreabilidade existe para impedir que alguém,
   no futuro, "ajuste" um número esperado até o teste passar: mudar qualquer um
   deles é contradizer uma medição registrada na revisão, e o comentário diz
   exatamente onde ela está.

O helper NÃO é coletado como suíte (`contraste.py` não casa com `test*.py`) e
não importa Django nem `core.tema` — é isso que permite às suítes de
`.template-tests/` carregá-lo por caminho com `importlib`.
"""

from django.test import SimpleTestCase

from core.tests.contraste import contraste, luminancia_relativa, tokens_do_input_css


class LuminanciaRelativaTests(SimpleTestCase):
    """As duas pontas da escala e a rejeição de entrada malformada."""

    def test_preto_tem_luminancia_zero(self):
        self.assertEqual(luminancia_relativa("#000000"), 0.0)

    def test_branco_tem_luminancia_um(self):
        self.assertEqual(luminancia_relativa("#ffffff"), 1.0)

    def test_maiusculas_e_minusculas_dao_o_mesmo_valor(self):
        self.assertEqual(
            luminancia_relativa("#889FEB"), luminancia_relativa("#889feb")
        )

    def test_hex_de_tres_digitos_levanta_value_error(self):
        # IN-10: um `#abc` não pode virar cor errada em silêncio dentro de uma
        # asserção de acessibilidade — a forma curta é recusada, não expandida.
        with self.assertRaises(ValueError):
            luminancia_relativa("#abc")

    def test_string_sem_cerquilha_e_fora_do_alfabeto_hex_levanta_value_error(self):
        with self.assertRaises(ValueError):
            luminancia_relativa("xyzxyz")

    def test_a_mensagem_do_erro_cita_a_entrada_recebida(self):
        with self.assertRaises(ValueError) as capturado:
            luminancia_relativa("#abc")
        self.assertIn("#abc", str(capturado.exception))


class ContrasteAncorasMatematicasTests(SimpleTestCase):
    """Propriedades do algoritmo — igualdade estrita, sem tolerância."""

    def test_branco_sobre_preto_e_exatamente_21(self):
        self.assertAlmostEqual(contraste("#ffffff", "#000000"), 21.0, delta=1e-9)

    def test_cor_sobre_ela_mesma_e_exatamente_1(self):
        for cor in ("#000000", "#ffffff", "#1e40af", "#22211d", "#a07400"):
            with self.subTest(cor=cor):
                self.assertAlmostEqual(contraste(cor, cor), 1.0, delta=1e-9)

    def test_a_ordem_dos_argumentos_nao_importa(self):
        pares = (
            ("#ffffff", "#1e40af"),
            ("#0f0e0d", "#889feb"),
            ("#192035", "#22211d"),
        )
        for a, b in pares:
            with self.subTest(par=(a, b)):
                self.assertEqual(contraste(a, b), contraste(b, a))


class ContrastePraresMedidosNaRevisaoTests(SimpleTestCase):
    """Os quatro pares que o `07-REVIEW.md` mediu à mão. Tolerância de ±0,05
    porque a revisão publicou 2 casas decimais."""

    def test_branco_sobre_a_marca_no_escuro_reprova_aa(self):
        # CR-02 (07-REVIEW.md) — o DEFEITO do G-02: 2,56:1, abaixo até do piso
        # de 3:1 para texto grande.
        self.assertAlmostEqual(contraste("#ffffff", "#889feb"), 2.56, delta=0.05)

    def test_tinta_escura_sobre_a_marca_no_escuro_aprova_aa(self):
        # CR-02 (07-REVIEW.md) — o CONSERTO do G-02: 7,54:1 com `--cor-page`
        # do escuro como texto sobre `bg-brand`.
        self.assertAlmostEqual(contraste("#0f0e0d", "#889feb"), 7.54, delta=0.05)

    def test_branco_sobre_a_marca_no_claro_aprova_aa(self):
        # CR-02 (07-REVIEW.md) — o valor de ANTES da fase, quando `bg-brand`
        # era sempre o claro: 8,72:1.
        self.assertAlmostEqual(contraste("#ffffff", "#1e40af"), 8.72, delta=0.05)

    def test_a_quarta_fatia_do_donut_e_invisivel_no_escuro(self):
        # CR-03 (07-REVIEW.md) — o defeito do G-03: `brand-tint` do escuro
        # sobre `surface-2` do escuro é literalmente o mesmo tom, 1,00:1.
        self.assertAlmostEqual(contraste("#192035", "#22211d"), 1.00, delta=0.05)


class TokensDoInputCssTests(SimpleTestCase):
    """A leitura dos dois blocos de `input.css`, com a fusão que o helper
    existe para fazer."""

    def setUp(self):
        self.claro, self.escuro = tokens_do_input_css()

    def test_o_bloco_claro_traz_os_tokens_de_root(self):
        self.assertEqual(self.claro["page"], "#f9f9f7")
        self.assertEqual(self.claro["brand"], "#1e40af")
        self.assertEqual(self.claro["secundaria"], "#a07400")

    def test_o_escuro_tem_valor_proprio_onde_declara_override(self):
        self.assertEqual(self.escuro["page"], "#0f0e0d")
        self.assertNotEqual(self.escuro["page"], self.claro["page"])
        self.assertEqual(self.escuro["brand"], "#889feb")

    def test_o_escuro_herda_o_claro_onde_nao_declara_override(self):
        # input.css:93-96 — o bloco escuro só declara o que tem valor próprio;
        # `secundaria`, `destructive` e `baseline` herdam o claro. Sem a fusão,
        # medir `--cor-destructive` no escuro daria KeyError.
        self.assertEqual(self.escuro["secundaria"], self.claro["secundaria"])
        self.assertEqual(self.escuro["destructive"], self.claro["destructive"])
        self.assertEqual(self.escuro["baseline"], self.claro["baseline"])

    def test_todo_token_do_claro_existe_no_escuro_depois_da_fusao(self):
        self.assertEqual(set(self.claro) - set(self.escuro), set())

    def test_os_valores_lidos_sao_hex_de_seis_digitos_utilizaveis(self):
        # A prova de que a leitura serve de entrada para `contraste()`: se um
        # valor viesse malformado, `luminancia_relativa` levantaria ValueError.
        for nome, valor in {**self.claro, **self.escuro}.items():
            with self.subTest(token=nome):
                self.assertIsInstance(luminancia_relativa(valor), float)

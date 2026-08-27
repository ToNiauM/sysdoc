/** @type {import('tailwindcss').Config} */

// ARQUIVO DO NÚCLEO — não edite. Os VALORES vivem em
// core/static/src/input.css; este arquivo só aponta para eles via
// var(--cor-*). Cores próprias do seu domínio vão em
// core/static/src/dominio.css. Chega verbatim ao sistema gerado: nenhuma
// interpolação, nenhuma derivação em JS — a cor institucional entra só pela
// variável de ambiente correspondente no .env (core/tema.py resolve em
// runtime).
//
// A régua de tamanhos de fonte é a ÚNICA chave declarada fora do `extend`, e
// isso é deliberado: dentro do `extend` ela ACRESCENTA ao default do Tailwind,
// então `text-2xl` … `text-9xl` continuariam existindo e gerando regra, com o
// gate de teste como única barreira. Fora do `extend` o Tailwind SUBSTITUI o
// mapa e simplesmente não gera nada além dos 6 degraus — o teto de 20px passa
// a ser propriedade da build. `colors`, `borderRadius` e `fontFamily` seguem
// no `extend` de propósito: precisam SOMAR ao default (`text-white`,
// `bg-red-600`, `rounded-full` e afins continuam em uso nos templates).
module.exports = {
  darkMode: ["selector", '[data-tema="escuro"]'],
  // O SysDoc não usa o diretório `apps/` do template original — as telas do
  // fluxo do pregoeiro vivem em `sysdoc_web/templates`. Sem esse glob, o
  // Tailwind não vê nenhuma classe das nossas telas e a build sai sem os
  // estilos delas (as classes do núcleo apareceriam, as nossas não).
  content: ["./core/templates/**/*.html", "./sysdoc_web/templates/**/*.html"],
  safelist: [
    "results",
    "module",
    "form-row",
    "btn",
    "btn--primaria",
    "btn--secundaria",
    "btn--neutro",
    "btn--destrutiva",
  ],
  theme: {
    fontSize: {
      xs: ["11px", { lineHeight: "1.4" }],
      sm: ["12px", { lineHeight: "1.4" }],
      base: ["13px", { lineHeight: "1.5" }],
      md: ["14px", { lineHeight: "1.5" }],
      lg: ["16px", { lineHeight: "1.4" }],
      xl: ["20px", { lineHeight: "1.3" }],
    },
    extend: {
      colors: {
        page: "var(--cor-page)",
        surface: "var(--cor-surface)",
        "surface-2": "var(--cor-surface-2)",
        "surface-3": "var(--cor-surface-3)",
        ink: "var(--cor-ink)",
        "ink-2": "var(--cor-ink-2)",
        muted: "var(--cor-muted)",
        grid: "var(--cor-grid)",
        baseline: "var(--cor-baseline)",
        destructive: "var(--cor-destructive)",
        "danger-tint": "var(--cor-danger-tint)",
        "warn-bg": "var(--cor-warn-bg)",
        "warn-tx": "var(--cor-warn-tx)",
        secundaria: "var(--cor-secundaria)",
        brand: "var(--cor-brand)",
        "brand-hover": "var(--cor-brand-hover)",
        "brand-ink": "var(--cor-brand-ink)",
        "brand-tint": "var(--cor-brand-tint)",
        "brand-tx": "var(--cor-brand-tx)",
        "seq-750": "var(--cor-seq-750)",
        "seq-600": "var(--cor-seq-600)",
        "seq-450": "var(--cor-seq-450)",
        "seq-300": "var(--cor-seq-300)",
      },
      borderRadius: {
        DEFAULT: "2px",
        sm: "2px",
        md: "2px",
        lg: "2px",
        xl: "2px",
        "2xl": "2px",
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
      },
    },
  },
  plugins: [],
};

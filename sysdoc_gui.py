#!/usr/bin/env python3
"""
Interface grafica simples para o SysDoc.

Mantem o fluxo principal em sysdoc.py e apenas executa os comandos
deterministicos em subprocessos, exibindo a saida em uma janela.
"""

from __future__ import annotations

import queue
import shutil
import subprocess
import sys
import threading
import os
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    X,
    Button,
    Entry,
    Frame,
    Label,
    Listbox,
    Scrollbar,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
)


ROOT = Path(__file__).resolve().parent
IGNORED_DIRS = {".git", ".claude", "__pycache__", "backup", "dist", "skills", "templates"}


class SysDocGui:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("SysDoc")
        self.root.geometry("980x640")
        self.project_var = StringVar()
        self.model_var = StringVar(value=os.environ.get("SYSDOC_OPENAI_MODEL", "gpt-5.4-mini"))
        self.status_var = StringVar(value="Pronto.")
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.running = False

        self._build()
        self.refresh_projects()
        self.root.after(100, self._drain_output)

    def _build(self) -> None:
        top = Frame(self.root, padx=10, pady=10)
        top.pack(fill=X)

        Label(top, text="Projeto").pack(side=LEFT)
        self.project_entry = Entry(top, textvariable=self.project_var)
        self.project_entry.pack(side=LEFT, fill=X, expand=True, padx=8)
        Button(top, text="Selecionar pasta", command=self.choose_folder).pack(side=LEFT, padx=2)
        Button(top, text="Atualizar", command=self.refresh_projects).pack(side=LEFT, padx=2)

        model_bar = Frame(self.root, padx=10)
        model_bar.pack(fill=X, pady=(0, 8))
        Label(model_bar, text="Modelo OpenAI").pack(side=LEFT)
        self.model_entry = Entry(model_bar, textvariable=self.model_var, width=28)
        self.model_entry.pack(side=LEFT, padx=8)

        main = Frame(self.root, padx=10)
        main.pack(fill=BOTH, expand=True)

        left = Frame(main)
        left.pack(side=LEFT, fill=BOTH, padx=(0, 10))
        Label(left, text="Projetos detectados").pack(anchor="w")

        list_frame = Frame(left)
        list_frame.pack(fill=BOTH, expand=True)
        self.project_list = Listbox(list_frame, width=32, height=20)
        self.project_list.pack(side=LEFT, fill=BOTH, expand=True)
        self.project_list.bind("<<ListboxSelect>>", self.select_project)
        scrollbar = Scrollbar(list_frame, command=self.project_list.yview)
        scrollbar.pack(side=RIGHT, fill="y")
        self.project_list.config(yscrollcommand=scrollbar.set)

        Button(left, text="Novo projeto a partir do modelo", command=self.create_project).pack(fill=X, pady=(8, 0))

        right = Frame(main)
        right.pack(side=LEFT, fill=BOTH, expand=True)

        actions = Frame(right)
        actions.pack(fill=X)
        for label, command in [
            ("Status", "status"),
            ("Preparar", "prepare"),
            ("Analisar com LLM", "analyze"),
            ("Validar", "validate"),
            ("Renderizar", "render"),
            ("Publicar", "publish"),
        ]:
            Button(actions, text=label, command=lambda c=command: self.run_command(c)).pack(side=LEFT, padx=2)

        self.log = Text(right, wrap="word", height=28)
        self.log.pack(fill=BOTH, expand=True, pady=8)

        bottom = Frame(self.root, padx=10, pady=8)
        bottom.pack(fill=X)
        Label(bottom, textvariable=self.status_var).pack(side=LEFT)
        Button(bottom, text="Limpar log", command=lambda: self.log.delete("1.0", END)).pack(side=RIGHT)

    def refresh_projects(self) -> None:
        current = self.project_var.get()
        self.project_list.delete(0, END)
        for path in sorted(ROOT.iterdir()):
            if not path.is_dir() or path.name in IGNORED_DIRS:
                continue
            if (path / "ETP.pdf").exists() or (path / "TR.pdf").exists() or (path / "dados_consolidados.json").exists():
                self.project_list.insert(END, path.name)
        if current:
            self.project_var.set(current)

    def select_project(self, _event=None) -> None:
        selection = self.project_list.curselection()
        if selection:
            self.project_var.set(self.project_list.get(selection[0]))

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=str(ROOT), title="Selecionar pasta do projeto")
        if not folder:
            return
        path = Path(folder)
        try:
            self.project_var.set(str(path.resolve().relative_to(ROOT)))
        except ValueError:
            self.project_var.set(str(path))

    def create_project(self) -> None:
        target = filedialog.askdirectory(initialdir=str(ROOT), title="Escolha onde criar o projeto")
        if not target:
            return
        name = Path(target).name
        template = ROOT / "templates" / "projeto-padrao"
        if not template.exists():
            messagebox.showerror("SysDoc", "Modelo templates/projeto-padrao nao encontrado.")
            return
        destination = Path(target)
        if any(destination.iterdir()):
            if not messagebox.askyesno("SysDoc", f"A pasta {name} nao esta vazia. Copiar o modelo mesmo assim?"):
                return
        shutil.copytree(template, destination, dirs_exist_ok=True)
        self.project_var.set(str(destination.resolve().relative_to(ROOT)) if ROOT in destination.resolve().parents else str(destination))
        self.refresh_projects()
        self._append(f"Projeto preparado em: {destination}\n")

    def run_command(self, command: str) -> None:
        if self.running:
            messagebox.showinfo("SysDoc", "Aguarde o comando em execucao terminar.")
            return

        project = self.project_var.get().strip()
        args = [sys.executable, "sysdoc.py", command]
        if command != "status":
            if not project:
                messagebox.showwarning("SysDoc", "Selecione ou informe uma pasta de projeto.")
                return
            args.append(project)
        if command == "analyze":
            model = self.model_var.get().strip()
            if model:
                args.extend(["--model", model])

        self.running = True
        self.status_var.set(f"Executando: {' '.join(args)}")
        self._append(f"\n$ {' '.join(args)}\n")
        threading.Thread(target=self._worker, args=(args,), daemon=True).start()

    def _worker(self, args: list[str]) -> None:
        try:
            process = subprocess.Popen(
                args,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.output_queue.put(line)
            code = process.wait()
            self.output_queue.put(f"\n[finalizado com codigo {code}]\n")
        except Exception as exc:
            self.output_queue.put(f"\n[erro] {exc}\n")
        finally:
            self.output_queue.put("__SYS_DOC_DONE__")

    def _drain_output(self) -> None:
        try:
            while True:
                item = self.output_queue.get_nowait()
                if item == "__SYS_DOC_DONE__":
                    self.running = False
                    self.status_var.set("Pronto.")
                    self.refresh_projects()
                else:
                    self._append(item)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_output)

    def _append(self, text: str) -> None:
        self.log.insert(END, text)
        self.log.see(END)


def main() -> None:
    root = Tk()
    SysDocGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()

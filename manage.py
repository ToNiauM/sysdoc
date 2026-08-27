#!/usr/bin/env python3
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sysdoc_web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Ele está instalado e disponível "
            "no seu PYTHONPATH? Você esqueceu de ativar um ambiente virtual? "
            "Instale com: pip install -e \".[web]\""
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

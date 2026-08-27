import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def django_web(tmp_path_factory):
    pytest.importorskip("django")

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sysdoc_web.settings")
    os.environ.setdefault("SYSDOC_WEB_DEBUG", "1")
    os.environ.setdefault("DJANGO_SECRET_KEY", "chave-apenas-para-testes")
    os.environ.setdefault(
        "SYSDOC_WEB_DATA_DIR", str(tmp_path_factory.mktemp("sysdoc_web_dados"))
    )

    import django
    from django.test.runner import DiscoverRunner
    from django.test.utils import setup_test_environment, teardown_test_environment

    django.setup()
    setup_test_environment()

    runner = DiscoverRunner(verbosity=0)
    old_config = runner.setup_databases()

    yield runner

    runner.teardown_databases(old_config)
    teardown_test_environment()

from typing import Callable, cast

import pytest

pytest.importorskip("fastapi")

from leropa.web.utils import create_jinja_context


def test_translation_function() -> None:
    ctx_en = create_jinja_context()
    tr_en = cast(Callable[[str, str], str], ctx_en["tr"])
    assert tr_en("ask_button", "Ask") == "Ask"

    ctx_ro = create_jinja_context(lang="ro")
    tr_ro = cast(Callable[[str, str], str], ctx_ro["tr"])
    assert tr_ro("ask_button", "Ask") == "Întreabă"
    assert tr_ro("missing", "Fallback") == "Fallback"

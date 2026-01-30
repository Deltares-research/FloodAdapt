from pathlib import Path
from textwrap import dedent

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase


def test_get_postprocessing_hook_none_when_not_configured(test_db: IDatabase):
    test_db.config.post_processing_hook = None
    hook = test_db.get_postprocessing_hook()
    assert hook is None


def test_get_postprocessing_hook_missing_file_raises(test_db: IDatabase):
    test_db.config.post_processing_hook = "postprocessing/missing.py"

    with pytest.raises(FileNotFoundError):
        test_db.get_postprocessing_hook(reload=True)


def test_get_postprocessing_hook_without_postprocess_raises(test_db: IDatabase):
    hook_rel = Path("postprocessing", "bad_hook.py")
    hook_abs = test_db.base_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text("def something_else(): pass")
    test_db.config.post_processing_hook = hook_rel.as_posix()

    with pytest.raises(AttributeError):
        test_db.get_postprocessing_hook(reload=True)


def test_get_postprocessing_hook_valid_hook(test_db: IDatabase):
    hook_rel = Path("postprocessing", "good_hook.py")
    hook_abs = test_db.base_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text(
        dedent(
            """
            def postprocess(results_path):
                return results_path
            """
        )
    )

    test_db.config.post_processing_hook = hook_rel.as_posix()

    hook = test_db.get_postprocessing_hook(reload=True)

    assert callable(hook)


def test_get_postprocessing_hook_is_cached(test_db: IDatabase):
    hook_rel = Path("postprocessing", "cached_hook.py")
    hook_abs = test_db.base_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text("def postprocess(): return 1")
    test_db.config.post_processing_hook = hook_rel.as_posix()

    hook1 = test_db.get_postprocessing_hook()
    hook2 = test_db.get_postprocessing_hook()

    assert hook1 is hook2

    hook1 = test_db.get_postprocessing_hook(reload=True)
    hook2 = test_db.get_postprocessing_hook(reload=True)

    assert hook1 is not hook2

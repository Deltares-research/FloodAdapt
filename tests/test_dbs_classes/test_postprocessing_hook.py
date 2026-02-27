from pathlib import Path
from textwrap import dedent

import pytest

from flood_adapt.config.database import PostProcessingHook
from flood_adapt.dbs_classes.interface.database import IDatabase


def test_get_postprocessing_hook_none_when_not_configured(test_db: IDatabase):
    test_db.config.post_processing_hooks = None
    hook = test_db.get_postprocessing_hooks()
    assert hook is None


def test_get_postprocessing_hook_missing_file_raises(test_db: IDatabase):
    test_db.config.post_processing_hooks = [
        PostProcessingHook(name="missing_hook", path="postprocessing/missing.py")
    ]

    with pytest.raises(FileNotFoundError):
        test_db.get_postprocessing_hooks(reload=True)


def test_get_postprocessing_hook_without_postprocess_raises(test_db: IDatabase):
    hook_rel = Path("postprocessing", "bad_hook.py")
    hook_abs = test_db.static_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text("def something_else(): pass")
    test_db.config.post_processing_hooks = [
        PostProcessingHook(name="bad_hook", path=hook_rel.as_posix())
    ]

    with pytest.raises(AttributeError):
        test_db.get_postprocessing_hooks(reload=True)


def test_get_postprocessing_hook_invalid_hook_raises_incorrect_args(test_db: IDatabase):
    hook_rel = Path("postprocessing", "bad_hook.py")
    hook_abs = test_db.static_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text(
        dedent(
            """
            def postprocess(database, scenario):
                return results_path
            """
        )
    )

    test_db.config.post_processing_hooks = [
        PostProcessingHook(name="bad_hook", path=hook_rel.as_posix())
    ]

    with pytest.raises(TypeError, match=r"must accept exactly 3 arguments"):
        _ = test_db.get_postprocessing_hooks(reload=True)


def test_get_postprocessing_hook_valid_hook(test_db: IDatabase):
    hook_rel = Path("postprocessing", "good_hook.py")
    hook_abs = test_db.static_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text(
        dedent(
            """
            def postprocess(database, scenario, results_path):
                return results_path
            """
        )
    )

    test_db.config.post_processing_hooks = [
        PostProcessingHook(name="good_hook", path=hook_rel.as_posix())
    ]

    hooks = test_db.get_postprocessing_hooks(reload=True)

    assert hooks is not None
    assert "good_hook" in hooks
    for hook in hooks.values():
        assert callable(hook)
        assert hook("not", "relevant", Path("expected")) == Path("expected")


def test_get_postprocessing_hook_is_cached(test_db: IDatabase):
    hook_rel = Path("postprocessing", "cached_hook.py")
    hook_abs = test_db.static_path / hook_rel
    hook_abs.parent.mkdir(parents=True, exist_ok=True)

    hook_abs.write_text("def postprocess(database, scenario, results_path): return 1")
    test_db.config.post_processing_hooks = [
        PostProcessingHook(name="cached_hook", path=hook_rel.as_posix())
    ]

    hook1 = test_db.get_postprocessing_hooks()
    hook2 = test_db.get_postprocessing_hooks()

    assert hook1 is hook2

    hook1 = test_db.get_postprocessing_hooks(reload=True)
    hook2 = test_db.get_postprocessing_hooks(reload=True)

    assert hook1 is not hook2

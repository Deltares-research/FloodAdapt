import importlib.util as importlib_util
import inspect
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field

PostProcessingFunction = Callable[..., None]


class PostProcessingHook(BaseModel):
    """A post-processing hook definition.

    Attributes
    ----------
    name : str
        The name of the hook.
    path : str
        The file path to the hook relative to the database's static path.
    """

    name: str = Field(description="The name of the hook")
    path: str = Field(description="File path relative to the database's static path")


class DatabaseConfig(BaseModel):
    """The expected variables and data types of attributes of the DatabaseConfig class.

    All Path attributes are expected to be strings representing file paths relative to the database root.

    Attributes
    ----------
    post_processing_hooks : list[PostProcessingHook] | None
        List of post-processing hooks to run after scenario execution. Defaults to None.
    ignore_postprocess_errors : bool
        Whether to ignore errors raised in the post-processing hook. Defaults to False.
    """

    post_processing_hooks: list[PostProcessingHook] | None = Field(
        default=None,
        description="List of post-processing hooks to run after scenario execution. If None, no post-processing hooks will be run.",
    )
    ignore_postprocess_errors: bool = Field(
        default=False,
        description="Whether to ignore errors raised in the post-processing hook",
    )

    def load_postprocess_hooks(
        self, static_path: Path
    ) -> dict[str, PostProcessingFunction] | None:
        if not self.post_processing_hooks:
            return None

        hooks = {}
        for hook in self.post_processing_hooks:
            hook_path = static_path / hook.path
            if not hook_path.exists():
                raise FileNotFoundError(
                    f"Post-processing hook {hook.name} not found: {hook_path}"
                )

            spec = importlib_util.spec_from_file_location(
                f"fa_postprocess_hook_{hook.name}", hook_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(
                    f"Could not load post-processing hook {hook.name} from {hook_path}"
                )

            module = importlib_util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "postprocess"):
                raise AttributeError(
                    f"Post-processing hook {hook.name} at {hook_path} does not define `postprocess()`"
                )

            sig = inspect.signature(module.postprocess)
            params = list(sig.parameters.values())

            if len(params) != 3:
                raise TypeError(
                    f"Post-processing hook {hook.name} at {hook_path} must accept exactly "
                    f"3 arguments (Database, Scenario, Path), got {len(params)}"
                )

            if sig.return_annotation not in (inspect.Signature.empty, None):
                raise TypeError(
                    f"Post-processing hook {hook.name} at {hook_path} must return None"
                )

            hooks[hook.name] = module.postprocess
        return hooks

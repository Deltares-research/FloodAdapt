import importlib.util as importlib_util
import inspect
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field

PostProcessingFunction = Callable[..., None]


class DatabaseConfig(BaseModel):
    """The expected variables and data types of attributes of the DatabaseConfig class.

    All Path attributes are expected to be strings representing file paths relative to the database root.

    Attributes
    ----------
    post_processing_hooks : dict[str, str] | None
        Dictionary mapping post-processing hook names to their file paths relative to the database's static path. Defaults to None.
    ignore_postprocess_errors : bool
        Whether to ignore errors raised in the post-processing hook. Defaults to False.
    """

    post_processing_hooks: dict[str, str] | None = Field(
        default=None,
        description="Dictionary mapping post-processing hook names to their file paths relative to the database's static path. If None, no post-processing hooks will be run.",
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
        for name, rel_path in self.post_processing_hooks.items():
            hook_path = static_path / rel_path
            if not hook_path.exists():
                raise FileNotFoundError(
                    f"Post-processing hook {name} not found: {hook_path}"
                )

            spec = importlib_util.spec_from_file_location(
                f"fa_postprocess_hook_{name}", hook_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(
                    f"Could not load post-processing hook {name} from {hook_path}"
                )

            module = importlib_util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "postprocess"):
                raise AttributeError(
                    f"Post-processing hook {name} at {hook_path} does not define `postprocess()`"
                )

            sig = inspect.signature(module.postprocess)
            params = list(sig.parameters.values())

            if len(params) != 3:
                raise TypeError(
                    f"Post-processing hook {name} at {hook_path} must accept exactly "
                    f"3 arguments (Database, Scenario, Path), got {len(params)}"
                )

            if sig.return_annotation not in (inspect.Signature.empty, None):
                raise TypeError(
                    f"Post-processing hook {name} at {hook_path} must return None"
                )

            hooks[name] = module.postprocess
        return hooks

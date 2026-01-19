from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """The expected variables and data types of attributes of the DatabaseConfig class.

    All Path attributes are expected to be strings representing file paths relative to the database root.

    Attributes
    ----------
    post_processing_hook : str | None
        Path to a post-processing hook script. Defaults to None.
    """

    post_processing_hook: str | None = Field(
        default=None,
        description="Path to a post-processing hook script relative to the database root.",
    )
    ignore_postprocess_errors: bool = Field(
        default=False,
        description="Whether to ignore errors raised in the post-processing hook",
    )

import contextlib
import os


@contextlib.contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    From https://github.com/laurent-laporte-pro/stackoverflow-q2059482/blob/master/demo/environ_ctx.py

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


@contextlib.contextmanager
def cleared_envvars(*vars_to_clear):
    """
    Temporarily clears specified environment variables and restores them after exiting the context.

    :param vars_to_clear: Environment variables to clear.
    """
    original_env = {var: os.environ.get(var, None) for var in vars_to_clear}

    try:
        for var in vars_to_clear:
            del os.environ[var]
        yield
    finally:
        for var, value in original_env.items():
            if value is not None:
                os.environ[var] = value
            else:
                os.unsetenv(var)

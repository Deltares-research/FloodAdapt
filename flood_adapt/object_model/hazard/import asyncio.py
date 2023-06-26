import asyncio


async def run(cmd: str):
    proc = await asyncio.create_subprocess_shell(
        cmd, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    print(f"[{cmd!r} exited with {proc.returncode}]")
    if stdout:
        print(f"[stdout]\n{stdout.decode()}")
    if stderr:
        print(f"[stderr]\n{stderr.decode()}")


asyncio.run(run("timeout /t 30"))

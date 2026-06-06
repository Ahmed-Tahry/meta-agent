import asyncio
import os
import tempfile
from pathlib import Path

DOCKERFILE_DIR = Path(__file__).resolve().parents[2] / "docker"
DEFAULT_IMAGE = "meta-agent-sandbox"
MEMORY_LIMIT = "256m"
PIDS_LIMIT = "50"
NETWORK_MODE = "none"


class SandboxError(Exception):
    pass


class SandboxTimeout(SandboxError):
    pass


class SandboxExecutionError(SandboxError):
    def __init__(self, stdout: str, stderr: str) -> None:
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(stderr or stdout)


class Sandbox:
    def __init__(self, image: str = DEFAULT_IMAGE) -> None:
        self.image = image
        self._built = False

    async def build(self) -> None:
        proc = await asyncio.create_subprocess_exec(
            "docker", "build",
            "-t", self.image,
            "-f", str(DOCKERFILE_DIR / "sandbox.Dockerfile"),
            str(DOCKERFILE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise SandboxError(f"Docker build failed:\n{stderr.decode()}")
        self._built = True

    async def run(self, code: str, timeout: int = 30) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
        try:
            tmp.write(code)
            tmp.close()

            cmd = [
                "docker", "run", "--rm",
                "--network", NETWORK_MODE,
                "--memory", MEMORY_LIMIT,
                "--pids-limit", PIDS_LIMIT,
                "-v", f"{tmp.name}:/sandbox/script.py",
                self.image,
                "python", "/sandbox/script.py",
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise SandboxTimeout(
                    f"Sandbox execution timed out after {timeout}s"
                )

            out = stdout.decode()
            err = stderr.decode()

            if proc.returncode != 0:
                raise SandboxExecutionError(out, err)

            return out

        finally:
            os.unlink(tmp.name)

    async def cleanup(self) -> None:
        cmds = [
            ["docker", "container", "prune", "-f"],
            ["docker", "image", "prune", "-f"],
        ]
        for cmd in cmds:
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.wait()

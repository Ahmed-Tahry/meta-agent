from src.config import SANDBOX_TIMEOUT
from src.tools import Tool
from src.tools.sandbox import Sandbox, SandboxError, SandboxExecutionError, SandboxTimeout
from src.task_logger import get_current_logger

_sandbox = Sandbox()
_sandbox_built = False
_sandbox_build_tried = False


async def code_executor(code: str, language: str = "python") -> str:
    global _sandbox_built, _sandbox_build_tried
    log = get_current_logger()

    if language != "python":
        return (
            f"Cannot execute {language} code. "
            "Only Python is supported in the sandboxed environment."
        )

    if not _sandbox_built and not _sandbox_build_tried:
        _sandbox_build_tried = True
        if log:
            log.log("SANDBOX", "Building sandbox Docker image (first use)")
        try:
            await _sandbox.build()
            _sandbox_built = True
            if log:
                log.log("SANDBOX", "Sandbox image built successfully")
        except SandboxError as e:
            if log:
                log.log("SANDBOX", "Failed to build sandbox image", str(e))
            return (
                f"Failed to build sandbox image. "
                f"Code ({len(code)} chars) could not be executed."
            )
        except FileNotFoundError:
            if log:
                log.log("SANDBOX", "Docker not available")
            return (
                "Docker is not available. Install Docker and start the daemon."
            )

    try:
        result = await _sandbox.run(code, timeout=SANDBOX_TIMEOUT)
        return result.strip() or "(no output)"
    except SandboxTimeout:
        return f"Execution timed out after {SANDBOX_TIMEOUT}s."
    except SandboxExecutionError as e:
        return (e.stdout or "") + ("\n" + e.stderr if e.stderr else "")
    except SandboxError as e:
        return f"Sandbox error: {e}"
    except FileNotFoundError:
        return "Docker is not available. Install Docker and start the daemon."


tool_code_executor = Tool(
    name="code_executor",
    fn=code_executor,
    description="Execute Python code in a sandboxed Docker environment",
)

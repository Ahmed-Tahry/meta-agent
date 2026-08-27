from src.config import SANDBOX_TIMEOUT
from src.task_logger import get_current_logger
from src.tools import Tool
from src.tools.sandbox import Sandbox, SandboxError, SandboxExecutionError, SandboxTimeout

_sandbox = Sandbox()


async def code_executor(code: str, language: str = "python") -> str:
    log = get_current_logger()

    if language != "python":
        return (
            f"Cannot execute {language} code. "
            "Only Python is supported in the sandboxed environment."
        )

    if not _sandbox._built:
        if log:
            log.log("SANDBOX", "Building sandbox Docker image (first use)")
        try:
            await _sandbox.build()
            if log:
                log.log("SANDBOX", "Sandbox image built successfully")
        except SandboxError as e:
            if log:
                log.log("SANDBOX", "Failed to build sandbox image", str(e))
            return f"Failed to build sandbox image. Code ({len(code)} chars) could not be executed."
        except FileNotFoundError:
            if log:
                log.log("SANDBOX", "Docker not available")
            return "Docker is not available. Install Docker and start the daemon."

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

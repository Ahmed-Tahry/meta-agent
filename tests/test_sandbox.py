import asyncio

import pytest

from src.tools.sandbox import Sandbox, SandboxError, SandboxExecutionError, SandboxTimeout


@pytest.fixture
def sandbox():
    return Sandbox(image="test-sandbox")


class TestSandboxBuild:
    @pytest.mark.asyncio
    async def test_build_success(self, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b""))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        s = Sandbox(image="test-build")
        await s.build()
        assert s._built is True

    @pytest.mark.asyncio
    async def test_build_failure(self, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b"error"))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        s = Sandbox(image="test-build-fail")
        with pytest.raises(SandboxError, match="Docker build failed"):
            await s.build()
        assert s._built is False


class TestSandboxRun:
    @pytest.mark.asyncio
    async def test_run_success(self, mocker, tmp_path):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"hello from sandbox", b""))
        mocked = mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        s = Sandbox(image="test-run")
        s._built = True
        result = await s.run("print('hello')")

        assert result == "hello from sandbox"
        mocked.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_failure(self, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b"ZeroDivisionError"))
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        s = Sandbox(image="test-run-fail")
        s._built = True

        with pytest.raises(SandboxExecutionError) as exc:
            await s.run("1/0")
        assert "ZeroDivisionError" in str(exc.value)

    @pytest.mark.asyncio
    async def test_run_timeout(self, mocker):
        async def never_finish():
            await asyncio.sleep(3600)

        mock_proc = mocker.AsyncMock()
        mock_proc.communicate = never_finish
        mock_proc.kill = mocker.Mock()
        mock_proc.wait = mocker.AsyncMock()
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        s = Sandbox(image="test-timeout")
        s._built = True

        with pytest.raises(SandboxTimeout, match="timed out"):
            await s.run("print('hi')", timeout=0.1)


class TestSandboxCleanup:
    @pytest.mark.asyncio
    async def test_cleanup(self, mocker):
        mock_proc = mocker.AsyncMock()
        mock_proc.returncode = 0
        mocker.patch("asyncio.create_subprocess_exec", return_value=mock_proc)

        s = Sandbox(image="test-cleanup")
        await s.cleanup()


class TestSandboxIntegration:
    @pytest.mark.asyncio
    async def test_real_sandbox_e2e(self):
        docker = pytest.importorskip("docker")
        try:
            docker.from_env().ping()
        except Exception:
            pytest.skip("Docker not available")

        s = Sandbox()
        await s.build()
        result = await s.run("print('hello from sandbox')")
        assert "hello from sandbox" in result
        await s.cleanup()

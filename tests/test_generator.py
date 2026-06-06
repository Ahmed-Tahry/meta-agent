import pytest

from src.tools import Tool
from src.tools.generator import ToolGenerator
from src.tools.sandbox import SandboxExecutionError, SandboxTimeout


SAMPLE_CODE = """\
async def my_tool(input_text: str) -> str:
    return f"Processed: {input_text}"
"""


@pytest.fixture
def mock_llm(mocker):
    def _make(response_text: str):
        mock = mocker.AsyncMock()
        msg = mocker.MagicMock()
        msg.content = response_text
        mock.ainvoke = mocker.AsyncMock(return_value=msg)
        return mock
    return _make


@pytest.fixture
def mock_sandbox(mocker):
    s = mocker.AsyncMock()
    s._built = False
    s.build = mocker.AsyncMock()
    s.run = mocker.AsyncMock(return_value="Function executed successfully")
    s.cleanup = mocker.AsyncMock()
    return s


class TestExtractCode:
    def test_extract_plain_code(self):
        gen = ToolGenerator()
        result = gen._extract_code("async def foo(): pass")
        assert result == "async def foo(): pass"

    def test_extract_with_markdown_fences(self):
        code = "```\nasync def foo():\n    pass\n```"
        gen = ToolGenerator()
        result = gen._extract_code(code)
        assert result == "async def foo():\n    pass"

    def test_extract_with_language_tag(self):
        code = "```python\nasync def foo():\n    pass\n```"
        gen = ToolGenerator()
        result = gen._extract_code(code)
        assert result == "async def foo():\n    pass"


class TestMakeFn:
    def test_make_fn_from_code(self):
        gen = ToolGenerator()
        fn = gen._make_fn(SAMPLE_CODE, "my_tool")
        assert callable(fn)

    @pytest.mark.asyncio
    async def test_make_fn_runs(self, mock_sandbox):
        mock_sandbox.run.return_value = "Processed: hello"
        gen = ToolGenerator(sandbox=mock_sandbox)
        fn = gen._make_fn(SAMPLE_CODE, "my_tool")
        result = await fn("hello")
        assert result == "Processed: hello"


class TestLLMGenerate:
    @pytest.mark.asyncio
    async def test_llm_generate_basic(self, mock_llm, mock_sandbox):
        llm = mock_llm(SAMPLE_CODE)
        gen = ToolGenerator(sandbox=mock_sandbox, llm=llm)
        code = await gen._llm_generate("my_tool", "Do something")
        assert "async def my_tool" in code

    @pytest.mark.asyncio
    async def test_llm_generate_includes_error_feedback(self, mock_llm, mock_sandbox):
        llm = mock_llm(SAMPLE_CODE)
        gen = ToolGenerator(sandbox=mock_sandbox, llm=llm)
        await gen._llm_generate("my_tool", "Do something", error_feedback="NameError: x not defined")
        call_args = llm.ainvoke.call_args[0][0]
        combined = " ".join(m.content for m in call_args)
        assert "NameError" in combined


class TestTestInSandbox:
    @pytest.mark.asyncio
    async def test_sandbox_success(self, mock_sandbox):
        gen = ToolGenerator(sandbox=mock_sandbox)
        result = await gen._test_in_sandbox("my_tool", SAMPLE_CODE)
        assert result is True

    @pytest.mark.asyncio
    async def test_sandbox_execution_error(self, mocker, mock_sandbox):
        mock_sandbox.run = mocker.AsyncMock(side_effect=SandboxExecutionError("", "SyntaxError"))
        gen = ToolGenerator(sandbox=mock_sandbox)
        result = await gen._test_in_sandbox("my_tool", "bad code")
        assert "SyntaxError" in result

    @pytest.mark.asyncio
    async def test_sandbox_timeout(self, mocker, mock_sandbox):
        mock_sandbox.run = mocker.AsyncMock(side_effect=SandboxTimeout("timed out"))
        gen = ToolGenerator(sandbox=mock_sandbox)
        result = await gen._test_in_sandbox("my_tool", "loop")
        assert "timed out" in result


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(self, mock_llm, mock_sandbox):
        llm = mock_llm(SAMPLE_CODE)
        mock_sandbox.run.side_effect = [None, "Processed: world"]
        gen = ToolGenerator(sandbox=mock_sandbox, llm=llm)
        tool = await gen.generate("my_tool", "Process input text")

        assert isinstance(tool, Tool)
        assert tool.name == "my_tool"
        assert "Process input text" in tool.description

        result = await tool.run(input_text="world")
        assert "world" in result

    @pytest.mark.asyncio
    async def test_generate_retry_then_success(self, mocker, mock_llm, mock_sandbox):
        bad_code = "async def my_tool(input_text: str) -> str:\n    return x"
        llm_calls = [bad_code, SAMPLE_CODE]
        llm = mock_llm("")
        llm.ainvoke = mocker.AsyncMock()
        llm.ainvoke.side_effect = [
            mocker.MagicMock(content=bad_code),
            mocker.MagicMock(content=SAMPLE_CODE),
        ]

        mock_sandbox.run = mocker.AsyncMock()
        mock_sandbox.run.side_effect = [
            SandboxExecutionError("", "NameError: name 'x' is not defined"),
            None,
            "Processed: world",
        ]

        gen = ToolGenerator(sandbox=mock_sandbox, llm=llm)
        tool = await gen.generate("my_tool", "Process input text")

        assert isinstance(tool, Tool)
        assert llm.ainvoke.call_count == 2
        result = await tool.run(input_text="world")
        assert "world" in result

    @pytest.mark.asyncio
    async def test_generate_all_fail_fallback(self, mocker, mock_llm, mock_sandbox):
        bad_code = "async def my_tool(input_text: str) -> str:\n    return x"

        llm = mock_llm("")
        llm.ainvoke = mocker.AsyncMock(return_value=mocker.MagicMock(content=bad_code))

        mock_sandbox.run = mocker.AsyncMock(
            side_effect=SandboxExecutionError("", "NameError: name 'x' is not defined")
        )

        gen = ToolGenerator(sandbox=mock_sandbox, llm=llm)
        tool = await gen.generate("my_tool", "Process input text")

        assert isinstance(tool, Tool)
        assert tool.name == "my_tool"
        result = await tool.run(input_text="world")
        assert "Failed to generate" in result
        assert "3" in result  # mentions attempt count


class TestFallbackTool:
    def test_fallback_tool_returns_error_message(self):
        gen = ToolGenerator()
        tool = gen._fallback_tool("broken_tool", "Do X", "SyntaxError")
        assert tool.name == "broken_tool"
        assert "Do X" in tool.description

    @pytest.mark.asyncio
    async def test_fallback_tool_run(self):
        gen = ToolGenerator()
        tool = gen._fallback_tool("broken", "Do the thing", "Error detail")
        result = await tool.run(input_text="anything")
        assert "Failed to generate" in result
        assert "broken" in result
        assert "Error detail" in result


class TestGenerateIntegration:
    @pytest.mark.asyncio
    async def test_generate_register_and_use(self, mock_llm, mock_sandbox):
        llm = mock_llm(SAMPLE_CODE)
        mock_sandbox.run.side_effect = [None, "Processed: hello"]
        gen = ToolGenerator(sandbox=mock_sandbox, llm=llm)
        tool = await gen.generate("my_tool", "Reverse the input string")

        assert isinstance(tool, Tool)
        assert tool.name == "my_tool"

        result = await tool.run(input_text="hello")
        assert result == "Processed: hello"

import pytest
from src.tools.registry import Tool
from src.tools import ToolRegistry, tool_registry


@pytest.fixture
def registry():
    return ToolRegistry()


@pytest.fixture
def sample_tool():
    async def my_fn(query: str) -> str:
        return f"result for {query}"
    return Tool(name="test_tool", fn=my_fn, description="A test tool")


class TestTool:
    @pytest.mark.asyncio
    async def test_tool_run(self):
        async def fn(x: str) -> str:
            return f"hello {x}"
        tool = Tool(name="greet", fn=fn, description="greeting")
        result = await tool.run(x="world")
        assert result == "hello world"


class TestToolRegistry:
    def test_register_and_get(self, registry, sample_tool):
        registry.register(sample_tool)
        retrieved = registry.get("test_tool")
        assert retrieved is sample_tool

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_list(self, registry, sample_tool):
        assert registry.list() == []
        registry.register(sample_tool)
        assert registry.list() == ["test_tool"]

    def test_get_multiple(self, registry):
        async def fn1(): pass
        async def fn2(): pass
        t1 = Tool(name="a", fn=fn1)
        t2 = Tool(name="b", fn=fn2)
        t3 = Tool(name="c", fn=fn1)
        registry.register(t1)
        registry.register(t2)
        registry.register(t3)

        result = registry.get_multiple(["a", "c", "nonexistent"])
        assert result == [t1, t3]

    def test_overwrite_tool(self, registry, sample_tool):
        registry.register(sample_tool)
        async def new_fn(): pass
        new_tool = Tool(name="test_tool", fn=new_fn, description="overwritten")
        registry.register(new_tool)
        assert registry.get("test_tool") is new_tool


class TestGlobalRegistry:
    def test_prebuilt_tools_registered(self):
        tools = tool_registry.list()
        assert "web_search" in tools
        assert "file_reader" in tools
        assert "code_executor" in tools

    def test_get_prebuilt(self):
        tool = tool_registry.get("web_search")
        assert tool is not None
        assert tool.name == "web_search"
        assert tool.description != ""

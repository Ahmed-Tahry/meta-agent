import pytest

from src.tools import Tool, ToolRegistry
from src.tools.composer import ToolComposer


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture
def composer(registry: ToolRegistry) -> ToolComposer:
    return ToolComposer(registry)


class TestToolComposer:
    @pytest.mark.asyncio
    async def test_pipeline_execution(self, registry, composer):
        async def first(query: str) -> str:
            return f"A({query})"

        async def second(path: str) -> str:
            return f"B({path})"

        registry.register(Tool(name="t1", fn=first, description="first"))
        registry.register(Tool(name="t2", fn=second, description="second"))

        pipeline = composer.compose(["t1", "t2"], name="t1|t2")
        out = await pipeline.run(input_text="hello")
        assert out == "B(A(hello))"

    def test_pipeline_caching(self, registry, composer):
        async def first(query: str) -> str:
            return query

        async def second(path: str) -> str:
            return path

        registry.register(Tool(name="t1", fn=first, description="first"))
        registry.register(Tool(name="t2", fn=second, description="second"))

        p1 = composer.compose(["t1", "t2"])
        p2 = composer.compose(["t1", "t2"])
        assert p1 is p2

    @pytest.mark.asyncio
    async def test_error_propagation(self, registry, composer):
        async def first(query: str) -> str:
            return query

        async def second(path: str) -> str:
            raise RuntimeError("boom")

        registry.register(Tool(name="t1", fn=first, description="first"))
        registry.register(Tool(name="t2", fn=second, description="second"))

        pipeline = composer.compose(["t1", "t2"])
        with pytest.raises(RuntimeError, match="boom"):
            await pipeline.run(input_text="x")

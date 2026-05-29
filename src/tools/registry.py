from typing import Any, Callable, Coroutine


class Tool:
    def __init__(
        self,
        name: str,
        fn: Callable[..., Coroutine[Any, Any, str]],
        description: str = "",
    ) -> None:
        self.name = name
        self.fn = fn
        self.description = description

    async def run(self, **kwargs: Any) -> str:
        return await self.fn(**kwargs)

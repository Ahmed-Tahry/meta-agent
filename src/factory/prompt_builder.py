from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT
from src.types.agent_spec import AgentSpec


class PromptBuilder:
    def __init__(self, use_fallback: bool = False) -> None:
        self._llm: ChatGoogleGenerativeAI | None = None
        self._use_fallback = use_fallback

    def _get_llm(self) -> ChatGoogleGenerativeAI:
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                timeout=LLM_TIMEOUT,
            )
        return self._llm

    async def build(self, spec: AgentSpec, base_prompt: str = "") -> str:
        if self._use_fallback or not GEMINI_API_KEY:
            return self._fallback_prompt(spec, base_prompt)

        prompt = (
            "Create a concise system prompt for an autonomous agent.\n"
            "The prompt must include objective, constraints, output format, and tool usage guidance.\n\n"
            f"Role: {spec.role}\n"
            f"Goal: {spec.goal}\n"
            f"Tools: {', '.join(spec.tools) if spec.tools else 'none'}\n"
            f"Constraints: {spec.constraints or 'none'}\n"
            f"Output format: {spec.output_format}\n"
            f"Base guidance: {base_prompt or 'none'}"
        )

        messages = [
            SystemMessage(content="You write high-quality system prompts for specialist agents."),
            HumanMessage(content=prompt),
        ]

        response = await self._get_llm().ainvoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        content = content.strip()
        if not content:
            return self._fallback_prompt(spec, base_prompt)
        return content

    def _fallback_prompt(self, spec: AgentSpec, base_prompt: str = "") -> str:
        tools = ", ".join(spec.tools) if spec.tools else "none"
        constraints = spec.constraints or "none"
        prefix = base_prompt.strip() if base_prompt else "You are a helpful specialist agent."
        return (
            f"{prefix}\n\n"
            f"Role: {spec.role}\n"
            f"Primary objective: {spec.goal}\n"
            f"Available tools: {tools}\n"
            f"Constraints: {constraints}\n"
            f"Required output format: {spec.output_format}\n"
            "If tools do not provide useful data, produce the best possible answer from available context"
            " and clearly state assumptions instead of returning an empty response."
        )

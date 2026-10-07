"""从进程环境读取模型配置与密钥的适配器。"""

import os
from typing import Literal

from agentscope.credential import CredentialBase, OpenAICredential
from agentscope.model import ModelCard, OpenAIChatModel


class EnvironmentModelCredential(CredentialBase):
    """AgentScope credential marker for a model whose secret stays in .env."""

    type: Literal["cnlc_env_model"] = "cnlc_env_model"

    @classmethod
    def get_chat_model_class(cls):
        return EnvironmentOpenAIChatModel


class EnvironmentOpenAIChatModel(OpenAIChatModel):
    """OpenAI-compatible model that reads credentials from process env."""

    @classmethod
    def list_models(cls, custom_yaml_dir=None):
        model_name = os.getenv("MODEL_NAME", "").strip()
        if not model_name:
            return []
        cards = super().list_models(custom_yaml_dir)
        matching = [card for card in cards if card.name == model_name]
        if matching:
            return matching
        return [
            ModelCard(
                name=model_name,
                label=model_name,
                status="active",
                context_size=_positive_env_int("MODEL_CONTEXT_SIZE", 128000),
                output_size=_positive_env_int("MODEL_OUTPUT_SIZE", 8192),
                parameter_schema=cls.Parameters.model_json_schema(),
                parameters_overrides={},
            )
        ]

    def __init__(self, credential, model, parameters=None, **kwargs):
        api_key = os.getenv("MODEL_API_KEY", "").strip()
        if not api_key:
            raise ValueError("MODEL_API_KEY 未配置。")
        base_url = os.getenv("MODEL_BASE_URL", "").strip() or None
        runtime_credential = OpenAICredential(
            api_key=api_key,
            base_url=base_url,
            name="CNLC environment model",
        )
        super().__init__(
            credential=runtime_credential,
            model=model,
            parameters=parameters,
            **kwargs,
        )


def _positive_env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{name} 必须是正整数。") from error
    if parsed <= 0:
        raise ValueError(f"{name} 必须是正整数。")
    return parsed

"""Provider registry for ADM generation backends."""

from adm_pipeline.providers.base import ProviderConfig, SectionProvider
from adm_pipeline.providers.lmstudio_openai_compat import LMStudioProvider
from adm_pipeline.providers.mock import MockProvider
from adm_pipeline.providers.openai_responses import OpenAIResponsesProvider
from adm_pipeline.providers.openrouter import OpenRouterProvider

__all__ = [
    "ProviderConfig",
    "SectionProvider",
    "MockProvider",
    "OpenAIResponsesProvider",
    "LMStudioProvider",
    "OpenRouterProvider",
]

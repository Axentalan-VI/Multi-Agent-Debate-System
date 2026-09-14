"""Runtime configuration for a debate."""
import os
import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

DEFAULT_AZURE_API_VERSION = "2025-01-01-preview"
AZURE_HOST_SUFFIXES = (".openai.azure.com", ".cognitiveservices.azure.com", ".services.ai.azure.com")
_DEPLOYMENT_PATH = re.compile(r"/openai/deployments/([^/]+)")


@dataclass(frozen=True)
class Endpoint:
    base_url: str | None  # OpenAI-style client (OpenAI, compatible proxies, Azure's /openai/v1 API)
    azure_endpoint: str | None  # classic Azure OpenAI resource, addressed by deployment + api-version
    api_version: str | None
    deployment: str | None  # from a pasted Azure deployment URL


def resolve_endpoint(url: str | None) -> Endpoint:
    """Interpret a <MODEL>_ENDPOINT value.

    A classic Azure deployment URL can be pasted whole (/deployments/<name>/chat/completions?api-version=...):
    it is split into the resource, the deployment name and the api-version.
    """
    if not url:
        return Endpoint(base_url=None, azure_endpoint=None, api_version=None, deployment=None)
    parts = urlsplit(url)
    is_azure = (parts.hostname or "").endswith(AZURE_HOST_SUFFIXES)
    if not is_azure or "/openai/v1" in parts.path:
        return Endpoint(base_url=url, azure_endpoint=None, api_version=None, deployment=None)
    deployment = _DEPLOYMENT_PATH.search(parts.path)
    return Endpoint(
        base_url=None,
        azure_endpoint=f"{parts.scheme}://{parts.netloc}",
        api_version=parse_qs(parts.query).get("api-version", [DEFAULT_AZURE_API_VERSION])[0],
        deployment=deployment.group(1) if deployment else None,
    )


@dataclass(frozen=True)
class ModelSettings:
    """Connection settings for one model.

    Only the name of the key's environment variable is stored, never the key, so saved
    transcripts cannot leak it.
    """

    default_model: str  # used when the endpoint does not name an Azure deployment
    endpoint: str | None  # empty means OpenAI's default API
    api_key_env: str

    @classmethod
    def from_env(cls, prefix: str, default_model: str) -> "ModelSettings":
        return cls(
            default_model=default_model,
            endpoint=os.getenv(f"{prefix}_ENDPOINT") or None,
            api_key_env=f"{prefix}_API_KEY",
        )

    @property
    def api_key(self) -> str | None:
        return os.getenv(self.api_key_env) or None

    @property
    def resolved_endpoint(self) -> Endpoint:
        return resolve_endpoint(self.endpoint)

    @property
    def model(self) -> str:
        """Model name sent with requests (the deployment name on Azure)."""
        return self.resolved_endpoint.deployment or self.default_model


@dataclass(frozen=True)
class DebateConfig:
    # Read at instantiation so values from .env apply after load_dotenv().
    debater_model: ModelSettings = field(default_factory=lambda: ModelSettings.from_env("GPT4O_MINI", "gpt-4o-mini"))
    moderator_model: ModelSettings = field(default_factory=lambda: ModelSettings.from_env("GPT4O_MINI", "gpt-4o-mini"))
    judge_model: ModelSettings = field(default_factory=lambda: ModelSettings.from_env("GPT4O", "gpt-4o"))
    debater_temperature: float = 0.8
    moderator_temperature: float = 0.2
    judge_temperature: float = 0.0
    rounds: int = 2
    word_limit: int = 250
    judge_consistency_runs: bool = True
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.rounds < 0:
            raise ValueError("rounds must be >= 0")
        if self.word_limit < 50:
            raise ValueError("word_limit must be >= 50")

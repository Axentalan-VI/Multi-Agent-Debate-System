import json
from dataclasses import asdict

import pytest
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from debate import DebateConfig
from debate.agents import make_debater_llm, make_judge
from debate.config import DEFAULT_AZURE_API_VERSION, Endpoint, resolve_endpoint

MINI_URL = (
    "https://mini-resource.openai.azure.com/openai/deployments/team-mini/chat/completions?api-version=2024-10-21"
)
FULL_URL = (
    "https://full-resource.openai.azure.com/openai/deployments/team-4o/chat/completions"
    "?api-version=2025-01-01-preview"
)


def test_no_url_uses_openai_default():
    assert resolve_endpoint(None) == Endpoint(base_url=None, azure_endpoint=None, api_version=None, deployment=None)


def test_openai_compatible_url_is_passed_through():
    url = "https://proxy.example.com/v1"
    assert resolve_endpoint(url) == Endpoint(base_url=url, azure_endpoint=None, api_version=None, deployment=None)


def test_azure_deployment_url_is_split_into_resource_deployment_and_api_version():
    assert resolve_endpoint(MINI_URL) == Endpoint(
        base_url=None,
        azure_endpoint="https://mini-resource.openai.azure.com",
        api_version="2024-10-21",
        deployment="team-mini",
    )


def test_azure_resource_url_without_version_gets_default():
    endpoint = resolve_endpoint("https://my-resource.openai.azure.com/")
    assert (endpoint.azure_endpoint, endpoint.api_version, endpoint.deployment) == (
        "https://my-resource.openai.azure.com",
        DEFAULT_AZURE_API_VERSION,
        None,
    )


def test_azure_v1_url_uses_openai_client():
    url = "https://my-resource.openai.azure.com/openai/v1/"
    assert resolve_endpoint(url) == Endpoint(base_url=url, azure_endpoint=None, api_version=None, deployment=None)


@pytest.fixture
def two_resources(monkeypatch) -> DebateConfig:
    monkeypatch.setenv("GPT4O_MINI_ENDPOINT", MINI_URL)
    monkeypatch.setenv("GPT4O_MINI_API_KEY", "key-mini")
    monkeypatch.setenv("GPT4O_ENDPOINT", FULL_URL)
    monkeypatch.setenv("GPT4O_API_KEY", "key-4o")
    return DebateConfig()


def test_each_model_uses_its_own_endpoint_deployment_and_key(two_resources):
    debater = make_debater_llm(two_resources)
    judge = make_judge(two_resources).first.bound

    assert isinstance(debater, AzureChatOpenAI) and isinstance(judge, AzureChatOpenAI)
    assert (
        debater.azure_endpoint,
        debater.deployment_name,
        debater.openai_api_version,
        debater.openai_api_key.get_secret_value(),
    ) == ("https://mini-resource.openai.azure.com", "team-mini", "2024-10-21", "key-mini")
    assert (
        judge.azure_endpoint,
        judge.deployment_name,
        judge.openai_api_version,
        judge.openai_api_key.get_secret_value(),
    ) == ("https://full-resource.openai.azure.com", "team-4o", "2025-01-01-preview", "key-4o")


def test_moderator_uses_the_mini_model(two_resources):
    assert two_resources.moderator_model == two_resources.debater_model


def test_api_keys_are_never_stored_in_config(two_resources):
    saved = json.dumps(asdict(two_resources))
    assert "key-mini" not in saved and "key-4o" not in saved


def test_empty_endpoint_uses_openai_api_with_default_model(monkeypatch):
    monkeypatch.delenv("GPT4O_MINI_ENDPOINT", raising=False)
    monkeypatch.setenv("GPT4O_MINI_API_KEY", "sk-test")

    llm = make_debater_llm(DebateConfig())

    assert type(llm) is ChatOpenAI
    assert llm.model_name == "gpt-4o-mini"
    assert str(llm.root_client.base_url).rstrip("/") == "https://api.openai.com/v1"

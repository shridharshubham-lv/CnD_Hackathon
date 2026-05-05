import os
import re

from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

_api_key = os.getenv("AZURE_OPENAI_API_KEY")
_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
_azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
_embeddings_deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")

_missing_vars = [
    name
    for name, value in {
        "AZURE_OPENAI_API_KEY": _api_key,
        "AZURE_OPENAI_ENDPOINT": _azure_endpoint,
        "AZURE_OPENAI_DEPLOYMENT": _deployment,
        "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT": _embeddings_deployment,
    }.items()
    if not value
]

if _missing_vars:
    raise RuntimeError(
        "Missing Azure OpenAI environment variables: " + ", ".join(_missing_vars)
    )

_client = AzureOpenAI(
    api_key=_api_key,
    api_version=_api_version,
    azure_endpoint=_azure_endpoint,
)


def chat(system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
    """Call Azure OpenAI chat completion. Strips ```json fences from response."""
    response = _client.chat.completions.create(
        model=_deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
    )
    text = response.choices[0].message.content.strip()
    # Strip ```json ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text


def embed(text: str) -> list[float]:
    """Call Azure OpenAI embeddings. Returns embedding vector as list of floats."""
    response = _client.embeddings.create(
        model=_embeddings_deployment,
        input=text,
    )
    return response.data[0].embedding

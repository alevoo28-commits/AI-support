import json
import os
import urllib.request

from dotenv import load_dotenv


def _list_models(endpoint: str, token: str) -> list[str]:
    url = endpoint.rstrip("/") + "/models"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "api-key": token,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return [m.get("id") for m in payload.get("data", []) if isinstance(m.get("id"), str)]


def main() -> None:
    load_dotenv()

    endpoint = os.getenv("GITHUB_MODELS_BASE_URL", "https://models.github.ai/inference")
    model = os.getenv("GITHUB_LLM_MODEL", "openai/gpt-5")

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("Falta GITHUB_TOKEN (ponlo en .env o en el entorno).")

    # Import dentro de main para que el error sea claro si faltan dependencias.
    from azure.ai.inference import ChatCompletionsClient
    from azure.ai.inference.models import SystemMessage, UserMessage
    from azure.core.credentials import AzureKeyCredential

    client = ChatCompletionsClient(endpoint=endpoint, credential=AzureKeyCredential(token))

    try:
        response = client.complete(
            messages=[
                SystemMessage("You are a helpful assistant."),
                UserMessage("What is the capital of France?"),
            ],
            model=model,
        )
        print("OK:", response.choices[0].message.content)
        return
    except Exception as e:
        print("ERROR calling model:")
        print(e)
        print("\nIntentando listar modelos disponibles en /models...")
        try:
            ids = _list_models(endpoint, token)
            print(f"Modelos detectados ({len(ids)}):")
            for mid in ids[:50]:
                print("-", mid)
            if len(ids) > 50:
                print(f"... y {len(ids) - 50} más")
        except Exception as le:
            print("No se pudo listar /models:")
            print(le)
        raise


if __name__ == "__main__":
    main()

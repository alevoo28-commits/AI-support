import os
import json
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
    if isinstance(payload, list):
        data = payload
    elif isinstance(payload, dict):
        data = payload.get("data", [])
    else:
        data = []

    ids: list[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        mid = item.get("id")
        if isinstance(name, str) and name:
            ids.append(name)
        elif isinstance(mid, str) and mid:
            ids.append(mid)
    # de-dup
    out: list[str] = []
    seen: set[str] = set()
    for m in ids:
        if m in seen:
            continue
        seen.add(m)
        out.append(m)
    return out


def main() -> None:
    load_dotenv()

    base_url = os.getenv("GITHUB_MODELS_BASE_URL", "https://models.inference.ai.azure.com")
    model = os.getenv("GITHUB_LLM_MODEL", "gpt-4o-mini")
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise SystemExit("Falta GITHUB_TOKEN (ponlo en .env o en el entorno).")

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    llm = ChatOpenAI(
        base_url=base_url,
        api_key=token,
        model=model,
        # No forzar temperature: algunos modelos en GitHub Models solo aceptan el default.
        streaming=False,
    )

    try:
        resp = llm.invoke(
            [
                SystemMessage(content="You are a helpful assistant."),
                HumanMessage(content="What is the capital of France? Answer with one word."),
            ]
        )
        print("OK:", getattr(resp, "content", resp))
        return
    except Exception as e:
        print("ERROR calling model via LangChain:")
        print(e)
        print("\nIntentando listar modelos disponibles en /models...")
        try:
            ids = _list_models(base_url, token)
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

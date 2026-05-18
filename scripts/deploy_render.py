#!/usr/bin/env python3
"""
Render.com ga avtomatik deploy qilish skripti.

Ishlatish:
  set RENDER_API_KEY=rnd_xxxxx
  set BOT_TOKEN=8935835776:AAFbgb4heejrQnRNkHJiuwpfZFh2Dws8p-Q
  set GEMINI_API_KEY=AIza_xxxxx
  set MONGODB_URI=mongodb+srv://...
  python scripts/deploy_render.py
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

GITHUB_REPO = "https://github.com/bzuf5555/bzuf-marketing"
SERVICE_NAME = "bzuf-marketing-bot"
RENDER_API = "https://api.render.com/v1"


def req(method: str, path: str, body: dict | None = None) -> dict:
    api_key = os.environ["RENDER_API_KEY"]
    url = RENDER_API + path
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"[ERROR] {method} {path}: {e.code} — {e.read().decode()}")
        sys.exit(1)


def main() -> None:
    required = ["RENDER_API_KEY", "BOT_TOKEN", "GEMINI_API_KEY", "MONGODB_URI"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[ERROR] Env o'zgaruvchilar yetishmaydi: {', '.join(missing)}")
        sys.exit(1)

    print("🔍 Render owner aniqlanmoqda...")
    owners = req("GET", "/owners?limit=1")
    owner_id = owners[0]["owner"]["id"]
    print(f"✅ Owner: {owner_id}")

    print("🔍 Mavjud servislar tekshirilmoqda...")
    services = req("GET", f"/services?limit=20&name={SERVICE_NAME}")
    existing = next((s for s in services if s["service"]["name"] == SERVICE_NAME), None)

    env_vars = [
        {"key": "BOT_TOKEN",       "value": os.environ["BOT_TOKEN"]},
        {"key": "GEMINI_API_KEY",  "value": os.environ["GEMINI_API_KEY"]},
        {"key": "MONGODB_URI",     "value": os.environ["MONGODB_URI"]},
        {"key": "PYTHON_VERSION",  "value": "3.11.0"},
    ]

    if existing:
        service_id = existing["service"]["id"]
        service_url = existing["service"]["serviceDetails"]["url"]
        print(f"✅ Mavjud servis topildi: {service_id}")
        print("🔄 Env vars yangilanmoqda...")
        for ev in env_vars:
            req("PUT", f"/services/{service_id}/env-vars", [ev])
        print("🚀 Deploy boshlandi...")
        req("POST", f"/services/{service_id}/deploys", {"clearCache": "do_not_clear"})
    else:
        print("🆕 Yangi servis yaratilmoqda...")
        payload = {
            "type": "web_service",
            "name": SERVICE_NAME,
            "ownerId": owner_id,
            "repo": GITHUB_REPO,
            "branch": "main",
            "rootDir": ".",
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "python main.py",
            "plan": "free",
            "region": "frankfurt",
            "healthCheckPath": "/health",
            "envVars": env_vars,
        }
        result = req("POST", "/services", payload)
        service = result.get("service", result)
        service_id = service.get("id", "")
        service_url = service.get("serviceDetails", {}).get("url", "")
        print(f"✅ Servis yaratildi: {service_id}")

    print(f"\n⏳ Deploy jarayoni kuzatilmoqda...")
    for attempt in range(30):
        time.sleep(10)
        deploys = req("GET", f"/services/{service_id}/deploys?limit=1")
        if deploys:
            status = deploys[0]["deploy"]["status"]
            print(f"   [{attempt+1}/30] Status: {status}")
            if status == "live":
                break
            if status in ("build_failed", "deactivated", "canceled"):
                print(f"[ERROR] Deploy muvaffaqiyatsiz: {status}")
                sys.exit(1)

    if not service_url:
        services_info = req("GET", f"/services/{service_id}")
        service_url = services_info.get("service", {}).get("serviceDetails", {}).get("url", "")

    webhook_url = f"https://{service_url}/{os.environ['BOT_TOKEN']}"
    print(f"\n🔗 Webhook o'rnatilmoqda: {webhook_url}")

    import urllib.parse
    tg_url = (
        f"https://api.telegram.org/bot{os.environ['BOT_TOKEN']}/setWebhook"
        f"?url={urllib.parse.quote(webhook_url, safe=':/')}"
    )
    with urllib.request.urlopen(tg_url) as resp:
        tg_result = json.loads(resp.read())
    print(f"✅ Webhook: {tg_result}")

    print(f"""
╔══════════════════════════════════════════╗
║  ✅  DEPLOY MUVAFFAQIYATLI!              ║
╠══════════════════════════════════════════╣
║  🌐  URL: https://{service_url:<22}║
║  🤖  Bot: @BzUFMarketBot                 ║
║  📊  Health: /health                     ║
╚══════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()

"""Prova di sola lettura delle statistiche Instagram: non pubblica e non scrive niente.

Chiede all'API quali metriche rispondono per l'account e per i post già usciti e stampa
l'esito nel log del giro (vedi .github/workflows/statistiche.yml). Serve a scegliere i nomi
giusti prima di cambiare bot/learn.py. Il token non viene mai stampato.

Uso: python -m bot.probe
"""

import json
import os
import time

import requests

GRAPH = "https://graph.instagram.com/v26.0"

# metriche per tipo di contenuto, come da documentazione (agg. settembre e ottobre 2026)
REELS = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions", "reposts",
         "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate"]
FEED = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions", "reposts",
        "follows", "profile_visits", "profile_activity"]


def get(path: str, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=40)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:300]}
    return r.status_code, body


def short(body, limit: int = 600) -> str:
    return json.dumps(body, ensure_ascii=False)[:limit]


def error_text(body) -> str:
    err = body.get("error", {}) if isinstance(body, dict) else {}
    return f"{err.get('code', '?')}/{err.get('error_subcode', '-')}: {err.get('error_user_msg') or err.get('message') or short(body, 200)}"


def account(user_id: str) -> None:
    print("\n=== ACCOUNT ===")
    code, body = get("me", fields="username,followers_count,follows_count,media_count")
    print(f"profilo: {code} {short(body, 300)}")
    now = int(time.time())
    since, until = now - 7 * 86400, now
    tests = [
        ("reach per follower/non follower (follow_type)", dict(metric="reach", breakdown="follow_type")),
        ("reach per tipo di contenuto (media_product_type)", dict(metric="reach", breakdown="media_product_type")),
        ("reach senza suddivisione", dict(metric="reach")),
        ("views per follower (follower_type)", dict(metric="views", breakdown="follower_type")),
        ("views per follower (follow_type)", dict(metric="views", breakdown="follow_type")),
        ("views per tipo di contenuto", dict(metric="views", breakdown="media_product_type")),
        ("accounts_engaged", dict(metric="accounts_engaged")),
        ("total_interactions", dict(metric="total_interactions")),
        ("likes,comments,saves,shares", dict(metric="likes,comments,saves,shares")),
    ]
    for label, extra in tests:
        code, body = get(f"{user_id}/insights", period="day", metric_type="total_value",
                         since=since, until=until, **extra)
        print(f"\n[{label}] HTTP {code}")
        print("  " + (short(body.get("data", body)) if code == 200 else error_text(body)))


def media(user_id: str) -> None:
    print("\n=== POST ===")
    code, body = get(f"{user_id}/media", fields="id,media_type,media_product_type,timestamp,permalink", limit=12)
    if code != 200:
        print(f"elenco post non disponibile: {error_text(body)}")
        return
    for item in body.get("data", []):
        product = item.get("media_product_type")
        metrics = REELS if product == "REELS" else FEED
        print(f"\n--- {item['id']} | {item.get('media_type')} / {product} | {item.get('timestamp')}")
        for metric in metrics:
            code, res = get(f"{item['id']}/insights", metric=metric)
            if code == 200:
                data = res.get("data", [])
                value = data[0]["values"][0]["value"] if data and data[0].get("values") else "(insieme vuoto)"
                print(f"  {metric}: {value}")
            else:
                print(f"  {metric}: ERRORE {error_text(res)}")
        if product != "REELS":
            code, res = get(f"{item['id']}/insights", metric="profile_activity", breakdown="action_type")
            print(f"  profile_activity per action_type: {short(res.get('data', res), 300) if code == 200 else 'ERRORE ' + error_text(res)}")


def main() -> None:
    user_id = os.environ["IG_USER_ID"]
    account(user_id)
    media(user_id)
    print("\nFatto: nessun dato è stato scritto o pubblicato.")


if __name__ == "__main__":
    main()

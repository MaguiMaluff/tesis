import time
import requests

class InstagramGraph:
    def __init__(self, api_version: str, access_token: str):
        self.base = f"https://graph.instagram.com/{api_version}"
        self.access_token = access_token

    def get(self, path: str, params=None):
        url = f"{self.base}/{path.lstrip('/')}"
        params = dict(params or {})
        params["access_token"] = self.access_token
        r = requests.get(url, params=params, timeout=30)
        return r.status_code, r.json() if r.headers.get("content-type","").startswith("application/json") else None, r.text

    def paginate(self, path: str, params: dict, max_pages=20, sleep_s=0.15):
        out = []
        after = None
        for _ in range(max_pages):
            p = dict(params)
            if after:
                p["after"] = after

            status, js, raw = self.get(path, p)
            if status != 200:
                raise RuntimeError(f"API error {status} on {path}: {raw}")

            out.extend((js or {}).get("data", []))

            cursors = ((js or {}).get("paging") or {}).get("cursors") or {}
            after = cursors.get("after")
            if not after:
                break
            time.sleep(sleep_s)
        return out

    def list_conversations(self, ig_user_id: str, limit=50, max_pages=10):
        return self.paginate(
            f"{ig_user_id}/conversations",
            params={
                "platform": "instagram",
                "limit": limit,
                "fields": "id,updated_time,participants"
            },
            max_pages=max_pages,
    )
    def list_messages(self, conversation_id: str, limit=50, max_pages=20):
        return self.paginate(
            f"{conversation_id}/messages",
            params={"limit": limit, "fields": "id,from,to,message,created_time"},
            max_pages=max_pages,
        )
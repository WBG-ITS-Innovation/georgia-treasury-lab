import re
import requests

class EventSkill:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def detect(self, text: str) -> dict:
        match = re.search(r"(20\d{2}|19\d{2})", text)
        if not match:
            return {"events": [], "relevance_flag": False}

        year = match.group(1)
        url = f"https://gnews.io/api/v4/search?q=world+bank&from={year}-01-01&to={year}-12-31&max=3&lang=en&token={self.api_key}"

        try:
            response = requests.get(url)
            data = response.json()
            articles = data.get("articles", [])
            titles = [a["title"] for a in articles[:3]]
            return {
                "events": titles,
                "relevance_flag": bool(titles)
            }
        except Exception:
            return {"events": [], "relevance_flag": False}

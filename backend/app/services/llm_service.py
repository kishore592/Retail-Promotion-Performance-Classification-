import json
from app.config.settings import settings

class LLMService:
    def __init__(self):
        self.enabled = bool(settings.openai_api_key)
        self.client = None
        if self.enabled:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.openai_api_key)

    def structured_or_fallback(self, system: str, user: str, fallback: dict):
        if not self.client:
            return fallback
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                response_format={"type":"json_object"},
                temperature=0,
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return fallback

llm_service = LLMService()

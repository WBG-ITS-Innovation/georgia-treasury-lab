class SecuritySkill:
    def detect(self, text: str) -> list:
        text = text.lower()
        keywords = ["security", "evacuation", "threat", "safety", "escort", "risk", "emergency"]
        return [word for word in keywords if word in text]

import re

class EntitySkill:
    def extract_entities(self, text: str) -> list:
        pattern = r"(Executive Director|Alternate Executive Director|Advisor|Deputy Director|Counsel|Legal Advisor)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)"
        matches = re.findall(pattern, text)
        return [{"name": name.strip(), "role": role.strip()} for role, name in matches]

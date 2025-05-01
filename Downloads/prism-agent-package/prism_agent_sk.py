import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from skills.ocr_skill import OCRSkill
from skills.db_skill import DatabaseSkill
from skills.security_skill import SecuritySkill
from skills.event_skill import EventSkill
from skills.entity_skill import EntitySkill

load_dotenv()

async def run_agent(image_path: str):
    kernel = Kernel()
    api_key = os.getenv("OPENAI_API_KEY")
    gnews_key = os.getenv("GNEWS_API_KEY")

    if not gnews_key:
        raise EnvironmentError("GNEWS_API_KEY not set")

    if api_key:
        kernel.add_service(OpenAIChatCompletion("openai", "gpt-3.5-turbo", api_key))

    # Instantiate modular skills
    ocr = OCRSkill()
    db = DatabaseSkill()
    security = SecuritySkill()
    events = EventSkill(api_key=gnews_key)
    entity_skill = EntitySkill()

    # === Step 1: OCR
    text = ocr.extract_text(image_path)
    if not text:
        print("No text detected.")
        return

    # === Step 2: Entity Extraction (Regex only)
    entities = entity_skill.extract_entities(text)

    # === Step 3: DB Match
    matched_eds, matched_lawyers = db.lookup_entities(entities)

    # === Step 4: Security language
    security_hits = security.detect(text)

    # === Step 5: Events
    events_info = events.detect(text)

    # === Step 6: Flag detection
    ed_flags = []
    legal_flags = []
    security_flags = []
    event_flags = []

    if matched_eds:
        ed_names = [e["name"] for e in matched_eds]
        if len(ed_names) >= 2:
            ed_flags.append("Sensitive communication between EDs: " + ", ".join(ed_names))
        else:
            ed_flags.append(f"Executive Director identified: {ed_names[0]}")
    else:
        ed_flags.append("No Executive Directors found")

    if matched_lawyers:
        lawyer_names = [l["name"] for l in matched_lawyers]
        legal_flags.append("Legal role(s) detected: " + ", ".join(lawyer_names))
    else:
        legal_flags.append("No legal advisors found")

    if security_hits:
        security_flags.append("Security/Safety terms detected: " + ", ".join(security_hits))
    else:
        security_flags.append("No security language detected")

    if events_info.get("relevance_flag"):
        event_flags.append("Major events found: " + ", ".join(events_info["events"]))
    else:
        event_flags.append("No major events detected")

    flags_summary = ed_flags + legal_flags + security_flags + event_flags

    score = round(min(1.0,
        0.3 * bool(matched_eds) +
        0.3 * bool(matched_lawyers) +
        0.2 * bool(security_hits) +
        0.2 * events_info.get("relevance_flag", False)
    ), 2)

    output = {
        "text_excerpt": text[:300] + "...",
        "entities_extracted": entities,
        "matched_eds": matched_eds,
        "matched_lawyers": matched_lawyers,
        "flags_detected": flags_summary,
        "flag_details": {
            "executive_directors": ed_flags,
            "legal_roles": legal_flags,
            "security_terms": security_flags,
            "event_context": event_flags
        },
        "events_detected": events_info,
        "confidence_score": score
    }

    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prism_agent_sk.py <image_path>")
        sys.exit(1)
    asyncio.run(run_agent(sys.argv[1]))

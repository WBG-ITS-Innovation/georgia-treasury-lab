import os
import sys
import json
import asyncio

from skills.ocr_skill import OCRSkill
from skills.entity_skill import EntitySkill
from skills.db_skill import DatabaseSkill
from skills.security_skill import SecuritySkill
from skills.event_skill import EventSkill

async def run_agent(image_path: str):
    # Load agent skills
    ocr = OCRSkill()
    entity_skill = EntitySkill(api_key=os.getenv("OPENAI_API_KEY"))
    db_skill = DatabaseSkill()
    security = SecuritySkill()
    event_skill = EventSkill(api_key=os.getenv("GNEWS_API_KEY"))

    # Step 1: OCR to extract raw text
    text = await ocr.extract_text(image_path)
    if not text:
        print("[Agent] No text extracted from image.")
        return

    # Step 2: Extract names and roles (via regex, add GPT once integrated and regex as fallback)
    entities = await entity_skill.extract_entities(text)

    # Step 3: Match against EDs and Legal databases
    matched_eds, matched_lawyers = db_skill.lookup_entities(entities) ### look up both exceptions

    # Step 4: Detect security terms
    security_hits = security.detect(text)

    # Step 5: Detect major events based on date in document
    events_info = event_skill.detect_events(text) ### using GNews via free membership

    # Step 6: Flag any rule-based exceptions
    flags = []

    # ED Exception
    if matched_eds:
        ed_names = [e["name"] for e in matched_eds]
        if len(ed_names) >= 2:
            flags.append(f"Sensitive communication between multiple Executive Directors: {', '.join(ed_names)}")
        else:
            flags.append(f"Executive Director identified: {ed_names[0]}")

    # Legal Exception
    if matched_lawyers:
        lawyer_names = [l["name"] for l in matched_lawyers]
        flags.append(f"Potential Attorney-Client communication detected: {', '.join(lawyer_names)}")

    # Security Exception
    if security_hits:
        flags.append(f"Security/Safety exception triggered due to mention of: {', '.join(security_hits)}")

    # Event Exception
    if events_info.get("relevance_flag") and events_info.get("events"):
        flags.append(f"Contextual events flagged from the same year: {', '.join(events_info['events'])}")

    # Step 7: Confidence score
    score = 0.0
    if matched_eds: score += 0.3
    if matched_lawyers: score += 0.3
    if security_hits: score += 0.2
    if events_info.get("relevance_flag"): score += 0.2
    score = min(1.0, round(score, 2))

    # Step 8: Final output
    result = {
        "text_excerpt": text[:300] + "...",
        "entities_extracted": entities,
        "matched_eds": matched_eds,
        "matched_lawyers": matched_lawyers,
        "flags_detected": flags,
        "events_detected": events_info,
        "confidence_score": score
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python prism_agent_runner.py <image_path>")
        sys.exit(1)

    asyncio.run(run_agent(sys.argv[1]))

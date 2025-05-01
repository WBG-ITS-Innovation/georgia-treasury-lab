import asyncio
from semantic_kernel import Kernel
from skills.ocr_skill import OCRSkill
from skills.entity_skill import EntitySkill
from skills.database_skill import DatabaseSkill
from skills.security_skill import SecuritySkill
from skills.event_skill import EventSkill
import json

async def run_agent(image_path: str):
    kernel = Kernel()

    # Load Skills
    ocr_skill = kernel.import_skill(OCRSkill(), "OCRSkill")
    entity_skill = kernel.import_skill(EntitySkill(), "EntitySkill")
    db_skill = kernel.import_skill(DatabaseSkill(), "DatabaseSkill")
    security_skill = kernel.import_skill(SecuritySkill(), "SecuritySkill")
    event_skill = kernel.import_skill(EventSkill(), "EventSkill")

    # Step 1 - OCR Step (correct call)
    ocr_context = await ocr_skill["ocr_extract_text"].invoke_async(image_path)
    text = ocr_context.result

    # Step 2 - Entity Extraction
    entity_context = await entity_skill["extract_entities"].invoke_async(text)
    entities = json.loads(entity_context.result)

    known_eds = []
    known_lawyers = []
    unknowns = []
    flags = []

    # Step 3 - Check each entity
    for person in entities:
        ed_context = await db_skill["lookup_ed"].invoke_async(person["name"])
        lawyer_context = await db_skill["lookup_lawyer"].invoke_async(person["name"])

        if json.loads(ed_context.result)["is_ed"]:
            known_eds.append(person["name"])
        elif json.loads(lawyer_context.result)["is_lawyer"]:
            known_lawyers.append(person["name"])
        else:
            unknowns.append(person["name"])

    # Step 4 - Sensitive Communications
    if len(known_eds) >= 2:
        flags.append("Sensitive communication between EDs detected")
    if known_lawyers:
        flags.append("Attorney-Client Privilege detected")

    # Step 5 - Security mentions
    security_context = await security_skill["detect_security_topics"].invoke_async(text)
    security_hits = json.loads(security_context.result)
    if security_hits:
        flags.append("Security/Safety concerns detected")

    # Step 6 - Events Detection
    event_context = await event_skill["detect_events"].invoke_async(text)
    events_info = json.loads(event_context.result)

    # Step 7 - Confidence Score
    score = 0.0
    if known_eds:
        score += 0.3
    if known_lawyers:
        score += 0.3
    if security_hits:
        score += 0.2
    if events_info["relevance_flag"]:
        score += 0.2
    score = min(1.0, round(score, 2))

    # Step 8 - Output
    result = {
        "text_excerpt": text[:300] + "...",
        "entities_extracted": entities,
        "summary": {
            "matched_eds": known_eds,
            "matched_lawyers": known_lawyers,
            "unmatched_names": unknowns,
            "pattern_flags": flags,
            "confidence_score": score,
            "flagged": bool(flags)
        },
        "events_detected": events_info
    }

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    image_path = input("Enter the path to the image: ").strip()
    asyncio.run(run_agent(image_path))

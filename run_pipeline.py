from engine import run
from events import EVENTS
from db import write_event

for cfg in EVENTS:
    print(f"Measuring {cfg['event_id']}...")
    try:
        record, top = run(
            cfg["EVENT"], cfg["BASKETS"], cfg["COMPANY_INFO"], cfg["NARRATIVE"]
        )
        write_event(record, top)
    except Exception as e:
        print(f"  FAILED {cfg['event_id']}: {e}")

print("Pipeline complete.")

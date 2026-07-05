return record, {
        "event_id": EVENT["event_id"],
        "name": EVENT["name"],
        "type_label": EVENT["type_label"],
        "information_date": EVENT["information_date"],
        "status": NARRATIVE["status"],
        "recency": NARRATIVE["recency"],
        "region": EVENT.get("region", ""),
    }

# agents/event_impact_agent.py

def map_event_to_impact(event):
    """
    Convert a single event into SMALL financial adjustments
    """

    event_type = (event.get("Event Type") or "").lower()
    risk_score = event.get("Event Risk Score", 50)

    growth_adj = 0
    discount_adj = 0

    # -----------------------------
    # GROWTH EVENTS
    # -----------------------------
    if "acquisition" in event_type:
        growth_adj += 0.003
        discount_adj += 0.001

    # -----------------------------
    # DISCOUNT / RISK EVENTS
    # -----------------------------
    if "debt" in event_type:
        discount_adj += 0.002

    elif "governance" in event_type:
        discount_adj += 0.001

    elif "legal" in event_type:
        discount_adj += 0.003

    return {
        "growth_adjustment": growth_adj,
        "discount_adjustment": discount_adj
    }

def aggregate_event_impacts(event_report):
    """
    Aggregate events with normalization + caps
    """

    total_growth = 0
    total_discount = 0

    event_count = len(event_report)

    for event in event_report:
        impact = map_event_to_impact(event)

        total_growth += impact["growth_adjustment"]
        total_discount += impact["discount_adjustment"]

    # ----------------------------
    # Normalize (average effect)
    # ----------------------------
    if event_count > 0:

        import math

        scale = min(math.sqrt(event_count), 10)

        total_growth /= scale
        total_discount /= scale

    # ----------------------------
    # Cap impacts (VERY IMPORTANT)
    # ----------------------------
    total_growth = min(total_growth, 0.03)
    total_discount = min(total_discount, 0.03)

    return {
        "Total Growth Adjustment": total_growth,
        "Total Discount Adjustment": total_discount,
        "Event Count": event_count
    }
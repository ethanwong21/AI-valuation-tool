# agents/event_impact_agent.py

def map_event_to_impact(event):
    """
    Convert a single event into SMALL financial adjustments
    """

    event_type = event.get("Event Type")
    risk_score = event.get("Event Risk Score", 50)

    growth_adj = 0
    discount_adj = 0

    # Much smaller base impacts
    if event_type == "Debt Issuance":
        discount_adj += 0.002

    elif event_type == "Acquisition":
        growth_adj += 0.003
        discount_adj += 0.001

    elif event_type == "Governance Change":
        discount_adj += 0.001

    elif event_type == "Legal Proceeding":
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
        total_growth /= event_count
        total_discount /= event_count

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
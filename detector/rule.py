MDD_THRESHOLD = 50000
SIGNAL_FREQ_THRESHOLD = 10

def detect_by_rule(mdd: int, signal_count: int) -> dict:
    if mdd > MDD_THRESHOLD:
        return {"status": "RED", "reason": f"MDD {mdd:,}원 초과"}
    if signal_count > SIGNAL_FREQ_THRESHOLD:
        return {"status": "YELLOW", "reason": f"신호 {signal_count}회 과다 발생"}
    return {"status": "GREEN", "reason": "정상"}
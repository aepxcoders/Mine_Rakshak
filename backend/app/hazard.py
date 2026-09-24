from typing import Any


def classify_hazard(data: dict[str, Any]) -> dict[str, Any]:
    """Prototype hazard classifier for the current test build.

    Raw MQ ADC values are deliberately NOT mapped to mine-safety gas limits.
    Gas alarms based on ppm are evaluated only when calibrated ppm values are
    supplied. Thresholds below are prototype/demo thresholds, not certified
    underground mine-safety limits.
    """

    reasons: list[str] = []
    danger = False
    warning = False

    # Calibrated methane only. DGMS references: 0.75% return-air,
    # 1.0% methane monitor alarm and 1.25% maximum / cut-off trigger.
    ch4 = data.get("ch4_ppm")
    if ch4 is not None:
        if ch4 >= 12500:
            danger = True
            reasons.append(f"Methane above 1.25% limit: {ch4:.0f} ppm")
        elif ch4 >= 7500:
            warning = True
            reasons.append(f"Methane elevated: {ch4:.0f} ppm")

    # Calibrated carbon monoxide only. Use the DGMS 50 ppm maximum
    # allowable concentration as danger and the NIOSH 35 ppm 8-h REL as
    # an early warning reference.
    co = data.get("co_ppm")
    if co is not None:
        if co >= 50:
            danger = True
            reasons.append(f"CO above 50 ppm reference: {co:.0f} ppm")
        elif co >= 35:
            warning = True
            reasons.append(f"CO exposure warning: {co:.0f} ppm")

    # The BMP280 reports dry-bulb temperature. DGMS underground heat limits
    # are specified using wet-bulb temperature, so dry-bulb temperature alone
    # is not used to declare regulatory heat danger in this test build.

    distance = data.get("distance_cm")
    if distance is not None:
        if distance <= 10:
            danger = True
            reasons.append(f"Obstacle critical: {distance:.1f} cm")
        elif distance <= 25:
            warning = True
            reasons.append(f"Obstacle nearby: {distance:.1f} cm")

    if data.get("flame") is True:
        danger = True
        reasons.append("Flame detected")

    if data.get("water") is True:
        danger = True
        reasons.append("Water detected")

    if data.get("vibration") is True:
        warning = True
        reasons.append("Vibration detected")

    # Prototype rover-stability thresholds. A steep orientation is a warning;
    # reserve danger for a likely rollover/extreme tilt. These are test values,
    # not certified mine-safety limits.
    tilt = data.get("tilt_deg")
    if tilt is not None:
        if tilt >= 70:
            danger = True
            reasons.append(f"Extreme rover tilt: {tilt:.1f}°")
        elif tilt >= 45:
            warning = True
            reasons.append(f"High rover tilt: {tilt:.1f}°")

    battery = data.get("battery_percent")
    if battery is not None:
        if battery <= 10:
            danger = True
            reasons.append(f"Battery critical: {battery:.0f}%")
        elif battery <= 20:
            warning = True
            reasons.append(f"Battery low: {battery:.0f}%")

    state = "danger" if danger else "warning" if warning else "safe"

    return {
        "state": state,
        "reasons": reasons,
        "gas_calibrated": bool(ch4 is not None or co is not None),
    }

from __future__ import annotations

from statistics import median
from typing import Any

from .mq_reference import estimate_all


# Regulatory/reference limits used by the explainable analytics engine.
# These values are deliberately kept separate from prototype operational rules.
SAFETY_REFERENCES = [
    {
        "id": "methane_dgms",
        "parameter": "Methane / inflammable gas",
        "field": "ch4_ppm",
        "unit": "ppm",
        "warning": "10,000 ppm (1.0%) alarm reference",
        "critical": "12,500 ppm (1.25%) maximum at any place / power cut trigger",
        "emergency": "50,000 ppm (5%) methane LEL reference",
        "source": "DGMS Coal Mines ventilation standard + DGMS methane drilling notification",
        "note": "Manufacturer-reference estimate may be shown by the prototype; certified compliance decisions require a validated gas instrument.",
    },
    {
        "id": "co_dgms_niosh",
        "parameter": "Carbon monoxide",
        "field": "co_ppm",
        "unit": "ppm",
        "warning": "35 ppm NIOSH 8-hour REL",
        "critical": "50 ppm DGMS maximum allowable concentration / OSHA 8-hour PEL",
        "emergency": "200 ppm NIOSH ceiling; 1,200 ppm IDLH",
        "source": "DGMS technical guidance + NIOSH Pocket Guide",
        "note": "Manufacturer-reference estimate may be shown by the prototype; certified exposure decisions require validated CO measurement. TWA limits also require time-weighted exposure measurement.",
    },
    {
        "id": "heat_dgms",
        "parameter": "Underground heat",
        "field": "wet_bulb_temp",
        "unit": "°C wet-bulb",
        "warning": ">30.5 °C: minimum 1 m/s ventilation required",
        "critical": ">33.5 °C: exceeds mine working-place limit",
        "emergency": "—",
        "source": "DGMS mine ventilation standard",
        "note": "BMP280 dry-bulb temperature alone is not a wet-bulb measurement, so this dashboard cannot claim compliance from temperature alone.",
    },
    {
        "id": "noise_reference",
        "parameter": "Occupational noise",
        "field": "sound_dba",
        "unit": "dBA",
        "warning": "85 dBA 8-hour action / recommended exposure level",
        "critical": "90 dBA 8-hour OSHA permissible exposure level",
        "emergency": "140 dB peak impulse reference",
        "source": "NIOSH / OSHA occupational noise guidance",
        "note": "Current sound sensor uses digital DO only, so DETECTED/CLEAR cannot be compared with dBA limits.",
    },
]


OPERATIONAL_REFERENCES = [
    {
        "parameter": "Obstacle distance",
        "warning": "≤25 cm",
        "critical": "≤10 cm",
        "basis": "MineRakshak rover collision-avoidance test rule (not a statutory mine limit)",
    },
    {
        "parameter": "Rover tilt",
        "warning": "≥45°",
        "critical": "≥70°",
        "basis": "MineRakshak stability test rule (not a statutory mine limit)",
    },
    {
        "parameter": "Wi-Fi RSSI",
        "warning": "≤−75 dBm",
        "critical": "≤−85 dBm",
        "basis": "Link-quality engineering rule for the Wi-Fi test build, not a personnel-safety limit",
    },
]


SEVERITY_WEIGHT = {
    "info": 0,
    "caution": 25,
    "warning": 55,
    "danger": 82,
    "emergency": 100,
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _alert(
    severity: str,
    title: str,
    message: str,
    action: str,
    *,
    basis: str,
    category: str = "safety",
    regulatory: bool = False,
) -> dict[str, Any]:
    return {
        "severity": severity,
        "title": title,
        "message": message,
        "action": action,
        "basis": basis,
        "category": category,
        "regulatory": regulatory,
    }


def _raw_gas_anomalies(latest: dict[str, Any], history: list[dict[str, Any]]):
    alerts: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    sensors = [
        ("mq4_raw", "MQ-4 methane-response"),
        ("mq7_raw", "MQ-7 CO-response"),
        ("mq135_raw", "MQ-135 air-quality-response"),
        ("mq3_raw", "MQ-3 VOC/gas-response"),
    ]

    for field, label in sensors:
        current = _number(latest.get(field))
        previous = [
            _number(item.get(field))
            for item in history[:-1]
            if _number(item.get(field)) is not None
        ]
        previous = [x for x in previous if x is not None]

        baseline = median(previous[-20:]) if len(previous) >= 5 else None
        change_pct = None
        status = "monitoring"

        if current is not None and current >= 4090:
            status = "saturated"
            alerts.append(
                _alert(
                    "warning",
                    f"{label} ADC saturation",
                    f"{label} is at {current:.0f}/4095, at the ESP32 ADC ceiling. The sensor response has reached the measurable ADC ceiling.",
                    "Check sensor supply, warm-up and module range; verify the area if the signal remains saturated.",
                    basis="ADC health / data-quality check",
                    category="sensor-health",
                )
            )
        elif current is not None and current >= 3950:
            status = "near-ceiling"
            alerts.append(
                _alert(
                    "caution",
                    f"{label} near ADC ceiling",
                    f"{label} is at {current:.0f}/4095. The sensor is close to the measurable ADC ceiling, so trend headroom is limited.",
                    "Check sensor range and continue monitoring the live trend.",
                    basis="ADC headroom / data-quality check",
                    category="sensor-health",
                )
            )
        elif current is not None and baseline not in (None, 0):
            change_pct = ((current - baseline) / baseline) * 100.0
            if change_pct >= 60:
                status = "rapid-rise"
                alerts.append(
                    _alert(
                        "warning",
                        f"Rapid rise in {label}",
                        f"Raw response is {change_pct:.0f}% above its recent baseline ({baseline:.0f} → {current:.0f}). This indicates an unusual change in the live gas-sensor response.",
                        "Verify the area, monitor the trend and improve ventilation if operationally appropriate.",
                        basis="Short-term baseline anomaly detection",
                        category="trend",
                    )
                )
            elif change_pct >= 30:
                status = "elevated-trend"
                alerts.append(
                    _alert(
                        "caution",
                        f"Elevated {label} trend",
                        f"Raw response is {change_pct:.0f}% above its recent baseline ({baseline:.0f} → {current:.0f}).",
                        "Continue monitoring the response trend for further increase.",
                        basis="Short-term baseline anomaly detection",
                        category="trend",
                    )
                )

        details.append(
            {
                "field": field,
                "label": label,
                "current": current,
                "baseline": round(baseline, 1) if baseline is not None else None,
                "change_percent": round(change_pct, 1) if change_pct is not None else None,
                "status": status,
                "calibrated": False,
            }
        )

    return alerts, details


def analyze_telemetry(latest: dict[str, Any], history: list[dict[str, Any]], age_seconds: float | None = None):
    alerts: list[dict[str, Any]] = []
    mq_estimates = estimate_all(latest, history)

    # --- Gas concentration decisions ---
    # Apply statutory/reference concentration thresholds only when a real ppm
    # concentration value is supplied. Raw MQ sensor-response values are handled
    # separately by the trend/range monitor and do not create a warning simply
    # because ppm input is absent.
    ch4 = _number(latest.get("ch4_ppm"))
    if ch4 is not None:
        if ch4 >= 50000:
            alerts.append(_alert("emergency", "Methane at/above LEL", f"Methane concentration is {ch4:.0f} ppm (≥5% by volume).", "Treat as an explosive-atmosphere emergency; remove ignition sources and follow mine emergency procedure.", basis="Methane 5% LEL reference", regulatory=True))
        elif ch4 >= 12500:
            alerts.append(_alert("danger", "Methane exceeds mine limit", f"Methane concentration is {ch4:.0f} ppm (≥1.25%).", "Cut/secure electrical energy as required by the applicable mine procedure and withdraw/ventilate as directed.", basis="DGMS maximum inflammable gas at any place / 1.25% power-cut trigger", regulatory=True))
        elif ch4 >= 10000:
            alerts.append(_alert("warning", "Methane alarm level reached", f"Methane concentration is {ch4:.0f} ppm (≥1.0%).", "Escalate ventilation and prepare for the 1.25% cut-off threshold.", basis="DGMS methane monitor alarm reference", regulatory=True))
        elif ch4 >= 7500:
            alerts.append(_alert("caution", "Methane elevated", f"Methane concentration is {ch4:.0f} ppm (≥0.75%).", "Investigate ventilation and trend.", basis="DGMS return-air inflammable gas reference", regulatory=True))

    co = _number(latest.get("co_ppm"))
    if co is not None:
        if co >= 1200:
            alerts.append(_alert("emergency", "CO immediately dangerous", f"CO concentration is {co:.0f} ppm (≥1,200 ppm IDLH).", "Treat as life-threatening atmosphere and follow rescue/respiratory-protection procedure.", basis="NIOSH IDLH 1,200 ppm", regulatory=True))
        elif co >= 200:
            alerts.append(_alert("danger", "CO ceiling exceeded", f"CO concentration is {co:.0f} ppm (≥200 ppm).", "Remove personnel from exposure and ventilate/investigate immediately.", basis="NIOSH 200 ppm ceiling", regulatory=True))
        elif co >= 50:
            alerts.append(_alert("danger", "CO above mine reference limit", f"CO concentration is {co:.0f} ppm (≥50 ppm).", "Escalate as unsafe exposure and improve ventilation/investigate the source.", basis="DGMS 50 ppm maximum allowable concentration", regulatory=True))
        elif co >= 35:
            alerts.append(_alert("warning", "CO exposure warning", f"CO concentration is {co:.0f} ppm (≥35 ppm).", "Review exposure duration and investigate the source.", basis="NIOSH 35 ppm 8-hour REL", regulatory=True))

    raw_alerts, gas_trends = _raw_gas_anomalies(latest, history)
    alerts.extend(raw_alerts)

    # Manufacturer-curve reference estimates. These are deliberately kept
    # separate from the calibrated ch4_ppm/co_ppm fields and therefore do not
    # create a regulatory alarm. They can still provide prototype decision
    # support when the estimate is inside the manufacturer's stated range.
    mq4_est = mq_estimates.get("mq4_raw", {})
    mq7_est = mq_estimates.get("mq7_raw", {})
    est_ch4 = _number(mq4_est.get("estimated_ppm"))
    est_co = _number(mq7_est.get("estimated_ppm"))

    if ch4 is None and est_ch4 is not None and mq4_est.get("in_reference_range"):
        if est_ch4 >= 12500:
            alerts.append(_alert("danger", "Methane reference estimate high", f"MQ-4 manufacturer-model estimate is about {est_ch4:.0f} ppm CH₄.", "Treat this as a prototype warning and verify with a calibrated/certified methane instrument.", basis="MQ-4 manufacturer Rs/R0 reference model + DGMS threshold context", category="gas-estimate"))
        elif est_ch4 >= 10000:
            alerts.append(_alert("warning", "Methane reference estimate at alarm region", f"MQ-4 manufacturer-model estimate is about {est_ch4:.0f} ppm CH₄.", "Increase caution/ventilation and verify concentration with a calibrated instrument.", basis="MQ-4 manufacturer Rs/R0 reference model + 1% methane context", category="gas-estimate"))
        elif est_ch4 >= 7500:
            alerts.append(_alert("caution", "Methane reference estimate elevated", f"MQ-4 manufacturer-model estimate is about {est_ch4:.0f} ppm CH₄.", "Monitor the trend and verify concentration if the estimate continues rising.", basis="MQ-4 manufacturer Rs/R0 reference model", category="gas-estimate"))

    if co is None and est_co is not None and mq7_est.get("in_reference_range"):
        if est_co >= 200:
            alerts.append(_alert("danger", "CO reference estimate very high", f"MQ-7 manufacturer-model estimate is about {est_co:.0f} ppm CO.", "Treat as a prototype warning; verify immediately with a calibrated CO instrument.", basis="MQ-7 manufacturer Rs/R0 reference model + CO threshold context", category="gas-estimate"))
        elif est_co >= 50:
            alerts.append(_alert("warning", "CO reference estimate elevated", f"MQ-7 manufacturer-model estimate is about {est_co:.0f} ppm CO.", "Investigate the source/ventilation and verify with a calibrated CO instrument.", basis="MQ-7 manufacturer Rs/R0 reference model + 50 ppm mine-reference context", category="gas-estimate"))
        elif est_co >= 35:
            alerts.append(_alert("caution", "CO reference estimate above exposure reference", f"MQ-7 manufacturer-model estimate is about {est_co:.0f} ppm CO.", "Monitor exposure and verify with a calibrated instrument.", basis="MQ-7 manufacturer Rs/R0 reference model + NIOSH 35 ppm context", category="gas-estimate"))

    # Attach the generic ppm/equivalent estimate to each trend card.
    for item in gas_trends:
        estimate = mq_estimates.get(item.get("field"), {})
        item["reference_estimate"] = estimate

    # --- Environment ---
    temp = _number(latest.get("temp"))
    humidity = _number(latest.get("humidity"))
    if temp is not None and humidity is None:
        alerts.append(
            _alert(
                "info",
                "Heat-limit comparison unavailable",
                f"BMP280 dry-bulb temperature is {temp:.1f} °C, but DGMS underground heat limits are specified as wet-bulb temperature.",
                "Add a humidity-capable sensor / wet-bulb or WBGT measurement before using the dashboard for heat-stress compliance.",
                basis="DGMS wet-bulb limit: ventilation action >30.5 °C; maximum 33.5 °C",
                category="data-quality",
                regulatory=True,
            )
        )

    # --- Immediate physical hazards ---
    if latest.get("flame") is True:
        alerts.append(_alert("emergency", "Flame detected", "The flame detector is active.", "Stop advance, verify the fire source and follow mine fire/emergency procedure.", basis="Direct hazard sensor", category="physical"))
    if latest.get("water") is True:
        alerts.append(_alert("danger", "Water detected", "The water sensor is active, indicating possible water ingress at the rover.", "Stop advance and verify flooding/inrush conditions before proceeding.", basis="Direct hazard sensor", category="physical"))
    if latest.get("vibration") is True:
        alerts.append(_alert("warning", "Vibration detected", "The SW-420 vibration input is active.", "Inspect for impact, unstable ground/rover contact or mechanical vibration.", basis="MineRakshak event rule", category="physical"))

    distance = _number(latest.get("distance_cm"))
    if distance is None:
        alerts.append(
            _alert(
                "info",
                "Obstacle distance unavailable",
                "No valid HC-SR04 distance is present in the latest telemetry packet.",
                "Treat obstacle clearance as unknown until a valid echo is restored; verify the ultrasonic sensor and its line of sight.",
                basis="Sensor availability check; missing distance is not interpreted as a clear path",
                category="data-quality",
            )
        )
    else:
        if distance <= 10:
            alerts.append(_alert("danger", "Obstacle critically close", f"Obstacle distance is {distance:.1f} cm.", "Stop/avoid forward movement.", basis="MineRakshak collision rule ≤10 cm", category="rover"))
        elif distance <= 25:
            alerts.append(_alert("warning", "Obstacle nearby", f"Obstacle distance is {distance:.1f} cm.", "Reduce speed and verify the path.", basis="MineRakshak collision rule ≤25 cm", category="rover"))

    tilt = _number(latest.get("tilt_deg"))
    if tilt is not None:
        if tilt >= 70:
            alerts.append(_alert("danger", "Extreme rover tilt", f"Rover tilt is {tilt:.1f}°.", "Stop movement and reassess terrain/rover stability.", basis="MineRakshak stability heuristic ≥70°", category="rover"))
        elif tilt >= 45:
            alerts.append(_alert("warning", "High rover tilt", f"Rover tilt is {tilt:.1f}°.", "Proceed cautiously and avoid additional slope/roll input.", basis="MineRakshak stability heuristic ≥45°", category="rover"))

    sound = _number(latest.get("sound"))
    if sound is not None and sound > 0:
        alerts.append(_alert("info", "Sound event detected", "The digital sound module is active.", "Use as an acoustic event cue only; the current module does not provide dBA exposure measurement.", basis="Digital DO event; no numeric sound level", category="event"))

    if latest.get("motion") is True:
        alerts.append(_alert("info", "Possible human motion detected", "PIR motion input is active near the rover.", "Use the camera/visual confirmation when available; PIR alone does not identify a person.", basis="PIR event", category="rescue"))

    rssi = _number(latest.get("wifi_rssi") if latest.get("wifi_rssi") is not None else latest.get("rssi"))
    if rssi is not None:
        if rssi <= -85:
            alerts.append(_alert("danger", "Telemetry link critically weak", f"Wi-Fi RSSI is {rssi:.0f} dBm.", "Move the gateway/access point closer or switch to the planned LoRa transport before relying on remote telemetry.", basis="MineRakshak test-link engineering rule ≤−85 dBm", category="connectivity"))
        elif rssi <= -75:
            alerts.append(_alert("warning", "Telemetry link weak", f"Wi-Fi RSSI is {rssi:.0f} dBm.", "Expect packet loss; improve link margin during the test.", basis="MineRakshak test-link engineering rule ≤−75 dBm", category="connectivity"))

    if age_seconds is not None and age_seconds > 10:
        alerts.append(_alert("danger", "Telemetry stale", f"Latest telemetry is {age_seconds:.0f} seconds old.", "Do not treat the dashboard as live until the telemetry link is restored.", basis="MineRakshak live-data freshness rule", category="connectivity"))

    # Put most urgent alerts first.
    order = {"emergency": 0, "danger": 1, "warning": 2, "caution": 3, "info": 4}
    alerts.sort(key=lambda item: order.get(item["severity"], 9))

    highest = alerts[0]["severity"] if alerts else "safe"
    safety_alerts = [a for a in alerts if a["severity"] in {"emergency", "danger", "warning"}]
    risk_score = max([SEVERITY_WEIGHT.get(a["severity"], 0) for a in alerts] or [5])
    if len(safety_alerts) > 1:
        risk_score = min(100, risk_score + min(12, (len(safety_alerts) - 1) * 4))

    # Coverage describes how much of the intended safety assessment is currently measurable.
    checks = {
        "live_telemetry": age_seconds is not None and age_seconds <= 10,
        "methane_concentration": ch4 is not None or mq4_est.get("estimated_ppm") is not None,
        "co_concentration": co is not None or mq7_est.get("estimated_ppm") is not None,
        "heat_compliance": humidity is not None and temp is not None,
        "physical_hazards": all(latest.get(k) is not None for k in ("flame", "water", "vibration")),
        "obstacle": distance is not None,
        "imu": tilt is not None,
        "connectivity": rssi is not None,
        "sound_event": latest.get("sound") is not None,
    }
    coverage = round(sum(bool(v) for v in checks.values()) / len(checks) * 100)

    if highest == "emergency":
        state = "emergency"
        summary = "EMERGENCY — immediate hazard response required"
    elif highest == "danger":
        state = "danger"
        summary = "CRITICAL — unsafe condition or severe system risk detected"
    elif highest == "warning":
        state = "warning"
        summary = "WARNING — conditions require operator attention"
    elif highest == "caution":
        state = "caution"
        summary = "CAUTION — sensor trend or system condition needs attention"
    else:
        state = "safe"
        summary = "NORMAL — no active rule-based hazard detected"

    driver_pool = [
        a for a in alerts
        if a["severity"] in {"emergency", "danger", "warning"}
    ]
    if len(driver_pool) < 2:
        driver_pool.extend(
            a for a in alerts
            if a["severity"] == "caution" and a not in driver_pool
        )
    risk_drivers = [
        {"severity": a["severity"], "title": a["title"]}
        for a in driver_pool[:3]
    ]
    detail_pool = [a for a in alerts if a["severity"] in {"emergency", "danger", "warning", "caution"}]
    risk_breakdown = [
        {
            "severity": a["severity"],
            "title": a["title"],
            "message": a["message"],
            "action": a["action"],
            "basis": a["basis"],
        }
        for a in detail_pool[:5]
    ]

    return {
        "engine": "MineRakshak Explainable Safety Analysis v1",
        "method": "Live sensor states + safety thresholds + short-term trend analysis",
        "risk_breakdown": risk_breakdown,
        "risk_drivers": risk_drivers,
        "machine_learning": False,
        "state": state,
        "risk_score": risk_score,
        "summary": summary,
        "analysis_coverage_percent": coverage,
        "alerts": alerts,
        "gas_trends": gas_trends,
        "mq_reference_estimates": mq_estimates,
        "checks": checks,
        "regulatory_references": SAFETY_REFERENCES,
        "operational_references": OPERATIONAL_REFERENCES,
        "limitations": [
            "MQ-4, MQ-7, MQ-135 and MQ-3 show manufacturer-curve reference estimates derived from Rs/R0 and the rover's early baseline. These are prototype estimates, not certified instrument readings.",
            "MQ-7 CO estimation assumes the manufacturer-specified high/low heater cycle; without verified heater cycling, treat the CO value as a reference estimate only.",
            "Temperature and humidity are monitored separately; underground heat compliance depends on the applicable wet-bulb/WBGT method.",
            "The current sound module is digital DETECTED/CLEAR, not a calibrated dBA meter.",
            "Obstacle and rover-tilt thresholds are MineRakshak engineering heuristics, not statutory mine-safety limits.",
            "This analytics layer is decision support for the prototype and does not replace certified gas instruments or mine emergency procedures.",
        ],
    }

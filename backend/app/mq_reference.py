from __future__ import annotations

"""Generic MQ reference-model conversion for the MineRakshak prototype.

This module intentionally keeps *reference estimates* separate from certified /
calibrated concentration measurements.  It uses the manufacturer's published
Rs/R0 method, reference sensitivity point and concentration-slope limit, while
using the rover's own early live readings as the clean-air R0 baseline.

Because breakout-board tolerances, heater drive, ageing, humidity, ADC scaling
and the actual clean-air baseline all matter, values produced here are labelled
reference estimates and are not written into the calibrated ch4_ppm/co_ppm
telemetry fields.
"""

from math import log, isfinite
from statistics import median
from typing import Any

ADC_MAX = 4095.0
ADC_VREF = 3.3
SENSOR_LOOP_VOLTAGE = 5.0

# Manufacturer-based curve envelopes.
# ref_ratio=0.2 follows the published sensitivity requirement R0(clean air) /
# Rs(reference gas) >= 5.  The exponent uses the published concentration slope
# alpha <= 0.6 across the stated concentration pair.  This is a conservative
# generic reference model, not a unit-specific factory calibration.
MODELS: dict[str, dict[str, Any]] = {
    "mq4_raw": {
        "sensor": "MQ-4",
        "gas": "CH₄",
        "gas_name": "Methane",
        "unit": "ppm",
        "range_min": 300.0,
        "range_max": 10000.0,
        "ref_ppm": 5000.0,
        "ref_ratio": 0.2,
        "slope_low_ppm": 1000.0,
        "slope_high_ppm": 5000.0,
        "alpha": 0.6,
        "source": "Winsen MQ-4",
    },
    "mq7_raw": {
        "sensor": "MQ-7",
        "gas": "CO",
        "gas_name": "Carbon monoxide",
        "unit": "ppm",
        "range_min": 10.0,
        "range_max": 500.0,
        "ref_ppm": 150.0,
        "ref_ratio": 0.2,
        "slope_low_ppm": 50.0,
        "slope_high_ppm": 300.0,
        "alpha": 0.6,
        "source": "Winsen MQ-7B reference curve",
        "heater_note": "CO reference estimate assumes the MQ-7 high/low heater cycle is implemented correctly.",
    },
    "mq135_raw": {
        "sensor": "MQ-135",
        "gas": "H₂-eq",
        "gas_name": "H₂ reference-equivalent air-quality response",
        "unit": "ppm-eq",
        "range_min": 10.0,
        "range_max": 1000.0,
        "ref_ppm": 400.0,
        "ref_ratio": 0.2,
        "slope_low_ppm": 100.0,
        "slope_high_ppm": 400.0,
        "alpha": 0.6,
        "source": "Winsen MQ-135 H₂ reference curve",
    },
    "mq3_raw": {
        "sensor": "MQ-3",
        "gas": "C₂H₅OH",
        "gas_name": "Ethanol",
        "unit": "ppm",
        "range_min": 25.0,
        "range_max": 500.0,
        "ref_ppm": 125.0,
        "ref_ratio": 0.2,
        "slope_low_ppm": 50.0,
        "slope_high_ppm": 300.0,
        "alpha": 0.6,
        "source": "Winsen MQ-3B reference curve",
    },
}


def _number(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)) and isfinite(float(v)):
        return float(v)
    return None


def _adc_to_rs_factor(adc: float) -> float | None:
    """Return Rs/RL from ADC. RL cancels when we later calculate Rs/R0."""
    if adc <= 0 or adc >= ADC_MAX:
        return None
    vout = (adc / ADC_MAX) * ADC_VREF
    if vout <= 0 or vout >= SENSOR_LOOP_VOLTAGE:
        return None
    return (SENSOR_LOOP_VOLTAGE / vout) - 1.0


def _curve_exponent(model: dict[str, Any]) -> float:
    return log(float(model["alpha"])) / log(float(model["slope_high_ppm"]) / float(model["slope_low_ppm"]))


def _estimate_ppm(rs_r0: float, model: dict[str, Any]) -> float | None:
    if rs_r0 <= 0:
        return None
    b = _curve_exponent(model)
    a = float(model["ref_ratio"]) / (float(model["ref_ppm"]) ** b)
    try:
        value = (rs_r0 / a) ** (1.0 / b)
    except (ValueError, OverflowError, ZeroDivisionError):
        return None
    return value if isfinite(value) and value >= 0 else None


def estimate_all(latest: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    for field, model in MODELS.items():
        current = _number(latest.get(field))
        history_values = [_number(row.get(field)) for row in history]
        history_values = [v for v in history_values if v is not None and 0 < v < ADC_MAX]

        # Use the oldest stable part of the available history as a prototype
        # clean-air reference.  This means the model follows the actual module's
        # baseline rather than assuming a universal breakout-board resistance.
        baseline_window = history_values[: min(10, len(history_values))]
        baseline_adc = median(baseline_window) if len(baseline_window) >= 5 else None

        current_factor = _adc_to_rs_factor(current) if current is not None else None
        baseline_factor = _adc_to_rs_factor(baseline_adc) if baseline_adc is not None else None
        rs_r0 = None
        ppm = None
        if current_factor is not None and baseline_factor not in (None, 0):
            rs_r0 = current_factor / baseline_factor
            ppm = _estimate_ppm(rs_r0, model)

        saturated = bool(current is not None and current >= 4090)
        near_ceiling = bool(current is not None and 3950 <= current < 4090)
        in_reference_range = bool(ppm is not None and model["range_min"] <= ppm <= model["range_max"])

        if ppm is None:
            display = "LEARNING BASELINE" if current is not None else "NO DATA"
            model_state = "baseline-learning" if current is not None else "no-data"
        elif saturated:
            display = "ADC SATURATED"
            model_state = "saturated"
        elif ppm < model["range_min"]:
            display = f"<{model['range_min']:.0f} {model['unit']}"
            model_state = "below-reference-range"
        elif ppm > model["range_max"]:
            display = f">{model['range_max']:.0f} {model['unit']}"
            model_state = "above-reference-range"
        else:
            display = f"{ppm:.0f} {model['unit']}"
            model_state = "reference-estimate"

        results[field] = {
            "field": field,
            "sensor": model["sensor"],
            "gas": model["gas"],
            "gas_name": model["gas_name"],
            "raw_adc": round(current, 1) if current is not None else None,
            "baseline_adc": round(baseline_adc, 1) if baseline_adc is not None else None,
            "rs_r0": round(rs_r0, 4) if rs_r0 is not None else None,
            "estimated_ppm": round(ppm, 2) if ppm is not None else None,
            "display": display,
            "unit": model["unit"],
            "reference_range": [model["range_min"], model["range_max"]],
            "in_reference_range": in_reference_range,
            "state": model_state,
            "near_adc_ceiling": near_ceiling,
            "adc_saturated": saturated,
            "source": model["source"],
            "model": "manufacturer Rs/R0 reference model",
            "heater_note": model.get("heater_note"),
        }

    return results

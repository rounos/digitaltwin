#!/usr/bin/env python3
"""
Synthetic dataset generator - "Digital Twin as Risk Evaluator" (Netcompany Hackathon, Challenge 1).

Everything here is FICTIONAL: the persona, her contacts, the addresses (.example domains), the cases.
No real personal data is used.

Design idea
-----------
* A hidden persona ("Eleni Markou") has consistent decision rules in 3 domains: medical triage,
  crisis response, time management.
* Scenarios are generated from structured data; the "ground truth" decision is computed by those rules.
* Past scenarios (history) leak into her digital footprint as chats, emails and decision-log notes.
* Held-out scenarios (test) are given WITHOUT answers; answers live in evaluation/ for scoring the twin.

Usage:  python generate_data.py [output_dir]
"""
import json
import os
import random
import sys
import datetime as dt
from email.message import EmailMessage
from email.utils import format_datetime

SEED = 42
rng = random.Random(SEED)
OUT = sys.argv[1] if len(sys.argv) > 1 else "synthetic_data"
UTC = dt.timezone(dt.timedelta(hours=2))  # Athens-ish, fixed offset for simplicity


def wjsonl(rel, rows):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def wtext(rel, text):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def wjson(rel, obj):
    wtext(rel, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


class SafeDict(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def fmt(t, ctx):
    return t.format_map(SafeDict(ctx))


# --------------------------------------------------------------------------------------
# 1. HIDDEN PERSONA (ground truth - NEVER feed this file to the twin; it is for evaluation)
# --------------------------------------------------------------------------------------
PERSONA = {
    "id": "eleni_markou_synthetic",
    "disclaimer": "Entirely fictional person created for a hackathon. Not based on a real individual.",
    "name": "Eleni Markou",
    "age": 34,
    "occupation": "Project manager / structural engineer at Aegean Structures (fictional firm)",
    "city": "Athens (fictional address)",
    "languages": ["el (family, friends)", "en (work)"],
    "style": {
        "email_en": "Short paragraphs, greeting 'Hi <name>,', sign-off 'Best,\\nEleni' (or 'Thanks!\\nEleni'), "
                    "dash bullet lists for options, flags problems early, no exclamation marks except 'Thanks!'",
        "chat_el": "Short direct sentences, practical, says what she decided and why in one line, "
                   "occasional 'οκ', '👍', hates being late, prefers text to phone calls",
    },
    "risk_attitudes": {
        "health": "cautious: never 'monitors' red-flag symptoms; 7-day cut-off for persistent symptoms; "
                  "second opinion before any elective procedure",
        "safety_crisis": "early mover: acts on incomplete information, prefers a false alarm over a late reaction",
        "schedule": "client deadlines are non-negotiable; renegotiates scope early rather than slipping late; "
                    "protects Tue/Thu mornings for deep work; 20% estimate buffer",
    },
    "decision_rules": {
        "M1": "Red-flag symptoms (radiating chest pain, breathless at rest, one-sided weakness, speech difficulty, "
              "sudden severe headache) -> emergency services immediately",
        "M2": "Temp >= 39.5, or >= 38.5 for >= 3 days, or SpO2 < 94 -> doctor within 24h",
        "M3": "Symptoms >= 7 days -> GP appointment this week + symptom log",
        "M4": "Elective procedure recommended -> independent second opinion first",
        "M5": "Short & mild -> self-care, recheck in 48h",
        "C-EQ": "critical: M>=5.5 & <=50km | high: (M>=5.0 & <=80km) or (M>=6.0 & <=150km) | medium: M>=4.0 & <=50km | else low",
        "C-FI": "critical: 112 alert or (<=3km & wind toward) | high: <=10km & wind toward | medium: <=10km or (<=25km & toward) | else low",
        "C-BO": "critical: >12h or (>4h & (>=38C or <=0C)) | high: >4h | medium: >1h | else low",
        "C-HE": "critical: >=43C | high: >=41C or (>=39C & >=3 days) | medium: >=36C | else low",
        "T-LOAD": "utilisation after new request: >100% high (renegotiate/decline) | >85% medium | else accept with buffer",
        "T-SLIP": "client-facing & >=3d & penalty -> critical | client-facing & >0 -> high | internal & >2d -> medium | else low",
        "T-FOCUS": "Tue/Thu 09:00-12:00 protected: decline unless client or urgent; then accept and move the block",
    },
}

# --------------------------------------------------------------------------------------
# 2. SCENARIOS (structured data per situation)
# --------------------------------------------------------------------------------------
S = []


def add(id_, domain, type_, data, test=False):
    S.append(dict(id=id_, domain=domain, type=type_, data=data, test=test))


PAT = {
    "self": ("me", "για μένα"),
    "mother": ("my mother", "για τη μαμά"),
    "father": ("my father", "για τον μπαμπά"),
    "partner": ("my partner Nikos", "για τον Νίκο"),
}

# ---- medical (triage-style risk assessment, NOT diagnosis) ----
add("med-01", "medical", "triage", dict(patient="self", age=34, symptoms=["chest_pain_radiating", "sweating"], duration_days=0, hr=104, spo2=97))
add("med-02", "medical", "triage", dict(patient="mother", age=61, symptoms=["shortness_of_breath_rest", "cough"], duration_days=1, spo2=91, temp_c=37.9), test=True)
add("med-03", "medical", "triage", dict(patient="partner", age=36, symptoms=["sudden_weakness_one_side", "speech_difficulty"], duration_days=0, bp="150/95"))
add("med-04", "medical", "triage", dict(patient="self", age=34, symptoms=["sore_throat", "fatigue"], duration_days=2, temp_c=37.6, spo2=98))
add("med-05", "medical", "triage", dict(patient="self", age=34, symptoms=["fever", "cough", "body_aches"], duration_days=4, temp_c=38.8, spo2=97, crp_mg_l=48), test=True)
add("med-06", "medical", "triage", dict(patient="father", age=66, symptoms=["mild_headache"], duration_days=1, temp_c=36.7, spo2=98, bp="135/85"))
add("med-07", "medical", "triage", dict(patient="self", age=34, symptoms=["persistent_cough"], duration_days=10, temp_c=36.9, spo2=98), test=True)
add("med-08", "medical", "triage", dict(patient="mother", age=61, symptoms=["knee_pain"], duration_days=14, temp_c=36.6))
add("med-09", "medical", "triage", dict(patient="self", age=34, symptoms=["skin_rash"], duration_days=3, temp_c=36.8, spo2=99))
add("med-10", "medical", "triage", dict(patient="partner", age=36, symptoms=["abdominal_pain", "vomiting"], duration_days=1, temp_c=39.6, hr=112, wbc_k_ul=15.2))
add("med-11", "medical", "triage", dict(patient="mother", age=61, symptoms=["knee_pain"], duration_days=60, procedure_recommended="total knee replacement"), test=True)
add("med-12", "medical", "triage", dict(patient="self", age=34, symptoms=["sneezing", "itchy_eyes"], duration_days=5, temp_c=36.7, spo2=99), test=True)
add("med-13", "medical", "triage", dict(patient="father", age=66, symptoms=["fever", "cough"], duration_days=2, temp_c=38.6, spo2=93), test=True)
add("med-14", "medical", "triage", dict(patient="self", age=34, symptoms=["lower_back_pain"], duration_days=8, temp_c=36.7))
add("med-15", "medical", "triage", dict(patient="father", age=66, symptoms=["back_pain"], duration_days=90, procedure_recommended="spinal fusion"))

# ---- crisis ----
add("eq-01", "crisis", "earthquake", dict(magnitude=5.8, distance_km=32, depth_km=10, building_year=1978, floor=4, time_of_day="03:12"))
add("eq-02", "crisis", "earthquake", dict(magnitude=4.6, distance_km=40, depth_km=12, building_year=1978, floor=4, time_of_day="14:40"))
add("eq-03", "crisis", "earthquake", dict(magnitude=5.2, distance_km=70, depth_km=8, building_year=1978, floor=4, time_of_day="22:05"), test=True)
add("eq-04", "crisis", "earthquake", dict(magnitude=3.4, distance_km=15, depth_km=9, building_year=1978, floor=4, time_of_day="11:20"))
add("eq-05", "crisis", "earthquake", dict(magnitude=6.1, distance_km=140, depth_km=20, building_year=1978, floor=4, time_of_day="06:55"))

add("fire-01", "crisis", "wildfire", dict(fire_distance_km=2.5, wind_toward_home=True, wind_speed_kmh=45, official_112_alert=True, car_fuel_pct=60))
add("fire-02", "crisis", "wildfire", dict(fire_distance_km=8, wind_toward_home=True, wind_speed_kmh=30, official_112_alert=False, car_fuel_pct=55), test=True)
add("fire-03", "crisis", "wildfire", dict(fire_distance_km=15, wind_toward_home=True, wind_speed_kmh=20, official_112_alert=False, car_fuel_pct=70))
add("fire-04", "crisis", "wildfire", dict(fire_distance_km=40, wind_toward_home=False, wind_speed_kmh=12, official_112_alert=False, car_fuel_pct=80))
add("fire-05", "crisis", "wildfire", dict(fire_distance_km=9, wind_toward_home=True, wind_speed_kmh=35, official_112_alert=False, car_fuel_pct=50))

add("bo-01", "crisis", "blackout", dict(scope="neighbourhood", expected_duration_h=0.5, temp_c=24, elderly_neighbour=True, cause="local transformer fault"))
add("bo-02", "crisis", "blackout", dict(scope="neighbourhood", expected_duration_h=3, temp_c=22, elderly_neighbour=True, cause="cable damage"))
add("bo-03", "crisis", "blackout", dict(scope="city district", expected_duration_h=6, temp_c=18, elderly_neighbour=True, cause="substation failure"), test=True)
add("bo-04", "crisis", "blackout", dict(scope="city district", expected_duration_h=8, temp_c=40, elderly_neighbour=True, cause="grid overload during heat"), test=True)
add("bo-05", "crisis", "blackout", dict(scope="regional", expected_duration_h=14, temp_c=20, elderly_neighbour=True, cause="transmission line failure"))
add("bo-06", "crisis", "blackout", dict(scope="city district", expected_duration_h=5.5, temp_c=20, elderly_neighbour=True, cause="substation fire"))

add("heat-01", "crisis", "heatwave", dict(forecast_max_c=44, duration_days=4, outdoor_site_visits_planned=True, elderly_relatives_alone=True, air_conditioning=True))
add("heat-02", "crisis", "heatwave", dict(forecast_max_c=39, duration_days=4, outdoor_site_visits_planned=True, elderly_relatives_alone=True, air_conditioning=True), test=True)
add("heat-03", "crisis", "heatwave", dict(forecast_max_c=37, duration_days=2, outdoor_site_visits_planned=False, elderly_relatives_alone=True, air_conditioning=True))
add("heat-04", "crisis", "heatwave", dict(forecast_max_c=41, duration_days=2, outdoor_site_visits_planned=True, elderly_relatives_alone=True, air_conditioning=True))

# ---- time management ----
add("tm-01", "time_management", "workload", dict(requester="peer", task="quay load calculations", new_request_hours=4, due_in_days=6, committed_hours=26, available_hours=40))
add("tm-02", "time_management", "workload", dict(requester="manager", task="tender documentation", new_request_hours=5, due_in_days=5, committed_hours=32, available_hours=40))
add("tm-03", "time_management", "workload", dict(requester="client", task="cost estimate revision", new_request_hours=8, due_in_days=4, committed_hours=36, available_hours=40))
add("tm-04", "time_management", "workload", dict(requester="client", task="BIM model update", new_request_hours=3, due_in_days=3, committed_hours=38, available_hours=40), test=True)
add("tm-05", "time_management", "workload", dict(requester="manager", task="site safety plan", new_request_hours=10, due_in_days=10, committed_hours=20, available_hours=40), test=True)

add("tm-06", "time_management", "slip", dict(task="Phase 2 structural drawings", slip_days=4, client_facing=True, penalty_clause=True))
add("tm-07", "time_management", "slip", dict(task="bridge inspection report", slip_days=1, client_facing=True, penalty_clause=False), test=True)
add("tm-08", "time_management", "slip", dict(task="internal design review pack", slip_days=4, client_facing=False, penalty_clause=False), test=True)
add("tm-09", "time_management", "slip", dict(task="calculation check-sheet", slip_days=1, client_facing=False, penalty_clause=False))
add("tm-10", "time_management", "slip", dict(task="progress report", slip_days=3, client_facing=True, penalty_clause=False))
add("tm-11", "time_management", "slip", dict(task="subcontractor schedule", slip_days=3, client_facing=False, penalty_clause=False))

add("tm-12", "time_management", "focus", dict(organizer="peer", weekday="Tue", start_hour=10, topic="quick sync on drawing numbering", urgent=False))
add("tm-13", "time_management", "focus", dict(organizer="client", weekday="Thu", start_hour=9, topic="change order discussion", urgent=False))
add("tm-14", "time_management", "focus", dict(organizer="peer", weekday="Wed", start_hour=10, topic="team retro", urgent=False))
add("tm-15", "time_management", "focus", dict(organizer="manager", weekday="Tue", start_hour=11, topic="inspection finding needs a decision", urgent=True), test=True)

# --------------------------------------------------------------------------------------
# 3. GROUND-TRUTH RULES -> decisions
# --------------------------------------------------------------------------------------
RED = {"chest_pain_radiating", "shortness_of_breath_rest", "sudden_weakness_one_side", "speech_difficulty", "severe_sudden_headache"}


def med_rule(d):
    sym = set(d["symptoms"])
    t = d.get("temp_c", 36.8)
    if sym & RED:
        return "critical", "M1"
    if t >= 39.5 or (t >= 38.5 and d["duration_days"] >= 3) or d.get("spo2", 98) < 94:
        return "high", "M2"
    if d.get("procedure_recommended"):
        return "medium", "M4"
    if d["duration_days"] >= 7:
        return "medium", "M3"
    return "low", "M5"


def eq_rule(d):
    m, x = d["magnitude"], d["distance_km"]
    if m >= 5.5 and x <= 50:
        return "critical", "C-EQ1"
    if (m >= 5.0 and x <= 80) or (m >= 6.0 and x <= 150):
        return "high", "C-EQ2"
    if m >= 4.0 and x <= 50:
        return "medium", "C-EQ3"
    return "low", "C-EQ4"


def fire_rule(d):
    x, tw, al = d["fire_distance_km"], d["wind_toward_home"], d["official_112_alert"]
    if al or (x <= 3 and tw):
        return "critical", "C-FI1"
    if x <= 10 and tw:
        return "high", "C-FI2"
    if x <= 10 or (x <= 25 and tw):
        return "medium", "C-FI3"
    return "low", "C-FI4"


def bo_rule(d):
    h, t = d["expected_duration_h"], d["temp_c"]
    if h > 12 or (h > 4 and (t >= 38 or t <= 0)):
        return "critical", "C-BO1"
    if h > 4:
        return "high", "C-BO2"
    if h > 1:
        return "medium", "C-BO3"
    return "low", "C-BO4"


def heat_rule(d):
    t, n = d["forecast_max_c"], d["duration_days"]
    if t >= 43:
        return "critical", "C-HE1"
    if t >= 41 or (t >= 39 and n >= 3):
        return "high", "C-HE2"
    if t >= 36:
        return "medium", "C-HE3"
    return "low", "C-HE4"


def util(d):
    return (d["committed_hours"] + d["new_request_hours"]) / d["available_hours"]


def load_rule(d):
    u = util(d)
    if u > 1.0:
        return "high", "T-LOAD1"
    if u > 0.85:
        return "medium", "T-LOAD2"
    return "low", "T-LOAD3"


def slip_rule(d):
    if d["client_facing"] and d["slip_days"] >= 3 and d["penalty_clause"]:
        return "critical", "T-SLIP1"
    if d["client_facing"] and d["slip_days"] > 0:
        return "high", "T-SLIP2"
    if (not d["client_facing"]) and d["slip_days"] > 2:
        return "medium", "T-SLIP3"
    return "low", "T-SLIP4"


def focus_rule(d):
    in_block = d["weekday"] in ("Tue", "Thu") and 9 <= d["start_hour"] < 12
    if not in_block:
        return "low", "T-FOCUS3"
    if d["organizer"] == "client" or d["urgent"]:
        return "medium", "T-FOCUS2"
    return "low", "T-FOCUS1"


RULES = dict(triage=med_rule, earthquake=eq_rule, wildfire=fire_rule, blackout=bo_rule,
             heatwave=heat_rule, workload=load_rule, slip=slip_rule, focus=focus_rule)

DECISION = {
    "M1": "Call emergency services now (166 EKAB / 112). Do not drive, do not wait to see if it passes.",
    "M2": "See a doctor within 24 hours (same-day if possible). Record temperature/oxygen every 4 hours to bring to the visit.",
    "M3": "Book a GP appointment this week, keep a short symptom log, ask for basic blood work.",
    "M4": "Do not agree to the procedure yet: get an independent second opinion first, after collecting all reports and imaging.",
    "M5": "Self-care (rest, fluids), monitor, set a reminder to re-assess in 48 hours; see a GP if worse or no better within a week.",
    "C-EQ1": "Drop-Cover-Hold during shaking, then leave via stairs to open space/assembly point (no elevators), check neighbours, use text not calls.",
    "C-EQ2": "Prepare for aftershocks: inspect for cracks, keep go-bag at the door, move outside at the first aftershock, stay off balconies.",
    "C-EQ3": "Stay alert: secure heavy furniture, re-check go-bag, follow official updates (Geodynamic Institute / EMSC). No evacuation.",
    "C-EQ4": "No action needed; log the event.",
    "C-FI1": "Evacuate now away from the wind direction with go-bag, documents and medication; call 112 once safe.",
    "C-FI2": "Prepare to leave immediately: car loaded and fuelled, windows closed, go-bag ready; leave at the first 112 message or if the fire gets within 5 km.",
    "C-FI3": "Monitor the fire map every 30 minutes, prepare go-bag, do not travel toward the area.",
    "C-FI4": "No action; check updates again in the evening.",
    "C-BO1": "Relocate to a safe, climate-controlled place (parents' flat), take medication and documents, check the elderly neighbour first.",
    "C-BO2": "Prepare for a long outage: fill water containers, charge all devices, move perishables, check on the elderly neighbour; go to parents' place if it passes 6 hours.",
    "C-BO3": "Charge power bank and torches, keep the fridge closed, follow the operator outage page.",
    "C-BO4": "Wait; check own breaker; keep phone in low-power mode.",
    "C-HE1": "Stay indoors 11:00-18:00, cancel site visits, call elderly relatives twice a day, hydrate, move to a cooling centre if AC fails.",
    "C-HE2": "Shift outdoor work to early morning, hydrate, check elderly relatives daily, avoid midday exposure.",
    "C-HE3": "Schedule the AC, drink more water, avoid heavy outdoor activity at midday.",
    "C-HE4": "No special action.",
    "T-LOAD1": "Decline or renegotiate today: offer a later date, reduced scope or a hand-off, rather than silently overcommit.",
    "T-LOAD2": "Accept only if something else moves; propose +2 days on the deadline.",
    "T-LOAD3": "Accept; schedule it with a 20% buffer.",
    "T-SLIP1": "Call the client today with a recovery plan (extra resource, weekend work on critical path, revised date) and inform the manager.",
    "T-SLIP2": "Notify the client today with a revised date and a reduced-scope option for the original date.",
    "T-SLIP3": "Escalate to the manager within 24 hours with two options and ask for a decision.",
    "T-SLIP4": "Absorb with the buffer; mention it in the weekly update.",
    "T-FOCUS1": "Decline politely and offer an afternoon slot (protect the deep-work block).",
    "T-FOCUS2": "Accept, and move the deep-work block to Wednesday morning.",
    "T-FOCUS3": "Accept; no conflict with protected time.",
}

REASON = {
    "M1": "Red-flag symptoms are not something to monitor. A false alarm costs a few hours; waiting can cost permanently.",
    "M2": "This fever level/duration or low oxygen is beyond the point where home care is reasonable, and the doctor needs data.",
    "M3": "Seven days is my cut-off: after that I stop guessing and get checked, with notes so the visit is efficient.",
    "M4": "No elective procedure on a single opinion; the decision is hard to undo.",
    "M5": "Short and mild with no red flags: rest and re-check beats rushing to a clinic.",
    "C-EQ1": "Early action beats perfect information. Shaking first, assessment after.",
    "C-EQ2": "Strong but not immediately dangerous: prepare so that the next step takes seconds.",
    "C-EQ3": "Noticeable but low risk: cheap precautions, no disruption.",
    "C-EQ4": "Too small to matter; I only keep a record.",
    "C-FI1": "Fire plus wind or an official alert leaves no margin; leaving late is the real risk.",
    "C-FI2": "Close and wind is against me: I get ready now so I can leave in minutes.",
    "C-FI3": "Not an immediate threat, but it can change with the wind, so I keep watching.",
    "C-FI4": "Far away and wind is not toward us.",
    "C-BO1": "Long or extreme-temperature outages become a health issue, especially for vulnerable neighbours.",
    "C-BO2": "Several hours is enough to run out of charge and water: prepare before it gets bad.",
    "C-BO3": "Short outage: minor preparation is enough.",
    "C-BO4": "Likely over soon.",
    "C-HE1": "At this temperature the risk is the heat itself; I remove exposure completely.",
    "C-HE2": "Heat is manageable if I move activity out of the hottest hours and check on vulnerable people.",
    "C-HE3": "Uncomfortable but manageable with small adjustments.",
    "C-HE4": "Normal summer day.",
    "T-LOAD1": "Above 100% load something breaks quietly. I would rather renegotiate openly on day one than miss on day ten.",
    "T-LOAD2": "I can take it only if something else gives, otherwise I am running without buffer.",
    "T-LOAD3": "There is capacity; the buffer protects the rest of the week.",
    "T-SLIP1": "A client-facing slip with a penalty must be heard from me first, with a plan, not discovered on the deadline.",
    "T-SLIP2": "Clients accept a revised date, they do not accept surprises.",
    "T-SLIP3": "Internal slip beyond two days needs a decision from someone with authority, with options ready.",
    "T-SLIP4": "Small internal slip is what the buffer is for.",
    "T-FOCUS1": "Deep-work mornings are how I deliver on time; a peer's sync fits in the afternoon.",
    "T-FOCUS2": "Client or urgent beats protected time, but I move the block rather than lose it.",
    "T-FOCUS3": "No conflict, so no reason to refuse.",
}

SEVERITY_ORDER = ["low", "medium", "high", "critical"]

# --------------------------------------------------------------------------------------
# 4. Scenario text rendering
# --------------------------------------------------------------------------------------
PEOPLE = {
    "client": ("Dimitris Sarris", "dimitris.sarris@nautilus-port.example"),
    "manager": ("Giorgos Papadakis", "giorgos.p@aegeanstructures.example"),
    "peer": ("Maria Kontou", "maria.k@aegeanstructures.example"),
}
ELENI = ("Eleni Markou", "eleni.markou@aegeanstructures.example")
yn = lambda b: "yes" if b else "no"


def describe(s):
    d, t = s["data"], s["type"]
    if t == "triage":
        who = PAT[d["patient"]][0]
        out = [f"Case concerns {who}, age {d['age']}.",
               "Symptoms: " + ", ".join(x.replace("_", " ") for x in d["symptoms"]) + ".",
               f"Duration: {d['duration_days']} day(s)."]
        v = []
        for k, lab in [("temp_c", "temperature {} C"), ("spo2", "SpO2 {}%"), ("hr", "heart rate {} bpm"),
                       ("bp", "blood pressure {}"), ("crp_mg_l", "CRP {} mg/L"), ("wbc_k_ul", "WBC {} K/uL")]:
            if k in d:
                v.append(lab.format(d[k]))
        if v:
            out.append("Measurements: " + ", ".join(v) + ".")
        if d.get("procedure_recommended"):
            out.append(f"A specialist has recommended: {d['procedure_recommended']}.")
        return " ".join(out)
    if t == "earthquake":
        return (f"A magnitude {d['magnitude']} earthquake was reported {d['distance_km']} km from home at depth {d['depth_km']} km, "
                f"at {d['time_of_day']}. Home is on floor {d['floor']} of a building constructed in {d['building_year']}.")
    if t == "wildfire":
        return (f"A wildfire was detected {d['fire_distance_km']} km from home. Wind {d['wind_speed_kmh']} km/h, blowing "
                f"{'towards' if d['wind_toward_home'] else 'away from'} home. Official 112 alert issued: {yn(d['official_112_alert'])}. "
                f"Car fuel level: {d['car_fuel_pct']}%.")
    if t == "blackout":
        return (f"Power outage affecting a {d['scope']}. Operator estimate: {d['expected_duration_h']} h. Outside temperature "
                f"{d['temp_c']} C. Elderly neighbour on the same floor: {yn(d['elderly_neighbour'])}. Cause: {d['cause']}.")
    if t == "heatwave":
        return (f"Forecast maximum {d['forecast_max_c']} C for {d['duration_days']} day(s). Outdoor site visits planned: "
                f"{yn(d['outdoor_site_visits_planned'])}. Elderly relatives living alone: {yn(d['elderly_relatives_alone'])}. "
                f"Air conditioning at home: {yn(d['air_conditioning'])}.")
    if t == "workload":
        return (f"New request from {d['requester']}: '{d['task']}', estimated {d['new_request_hours']} h, due in {d['due_in_days']} days. "
                f"Current commitments this week: {d['committed_hours']} h of {d['available_hours']} h available.")
    if t == "slip":
        return (f"Task '{d['task']}' is {d['slip_days']} day(s) behind schedule. Client-facing: {yn(d['client_facing'])}. "
                f"Contractual delay penalty: {yn(d['penalty_clause'])}.")
    if t == "focus":
        return (f"Meeting request from {d['organizer']} ({'urgent' if d['urgent'] else 'not urgent'}) on {d['weekday']} at "
                f"{d['start_hour']:02d}:00 about '{d['topic']}'.")
    raise ValueError(t)


QUESTION = "As Eleni, assess the risk level (low/medium/high/critical), decide what to do, and explain why."

# dates: history spread over 2025-02 .. 2026-10 ; test = last week
hist = [s for s in S if not s["test"]]
tests = [s for s in S if s["test"]]
start, end = dt.date(2025, 2, 3), dt.date(2026, 10, 20)
span = (end - start).days
days = sorted(rng.sample(range(span), len(hist)))
rng.shuffle(hist)  # decouple scenario order from date
for s, off in zip(hist, days):
    s["date"] = (start + dt.timedelta(days=off)).isoformat()
for i, s in enumerate(tests):
    s["date"] = (dt.date(2026, 11, 10) + dt.timedelta(days=i % 7)).isoformat()

for s in S:
    s["situation"] = describe(s)
    risk, rid = RULES[s["type"]](s["data"])
    s["truth"] = dict(risk_level=risk, rule_id=rid, decision=DECISION[rid], rationale=REASON[rid])

# --------------------------------------------------------------------------------------
# 5. Footprint from HISTORY decisions: chats (Greek), emails (English), decision-log notes
# --------------------------------------------------------------------------------------
CHAT_TPL = {
    "M1": ["Κάλεσα το 166 {fw}. Δεν περιμένω να δω αν θα περάσει, τέτοια συμπτώματα δεν τα παίζω.",
           "Πάμε επείγοντα, το ΕΚΑΒ είναι καθ' οδόν {fw}. Σε παίρνω μόλις ξέρω κάτι."],
    "M2": ["Έκλεισα ραντεβού {fw} για αύριο το πρωί. Δεν το αφήνω άλλη μέρα. Γράφω τιμές κάθε 4 ώρες για να τις δει ο γιατρός ({vit}).",
           "Δεν το αφήνω, πάμε σε γιατρό σήμερα ή αύριο πρωί {fw}. Τα νούμερα ({vit}) δεν μ' αρέσουν."],
    "M3": ["Πέρασε εβδομάδα και δεν έχει φύγει. Κλείνω ραντεβού με παθολόγο αυτή την εβδομάδα {fw} και κρατάω σημειώσεις για τα συμπτώματα.",
           "Οκ, 7 μέρες είναι το όριό μου. Δεν μαντεύω άλλο, πάω για έλεγχο {fw}."],
    "M4": ["Ο γιατρός πρότεινε {proc} {fw}, αλλά πριν πούμε ναι θέλω δεύτερη γνώμη από άλλον ειδικό. Μαζεύω πρώτα εξετάσεις και απεικονίσεις.",
           "Χειρουργείο δεν κλείνουμε με μία γνώμη. Δεύτερος γιατρός, ανεξάρτητος, και μετά αποφασίζουμε."],
    "M5": ["Τίποτα σοβαρό, ξεκούραση και υγρά. Έβαλα υπενθύμιση σε 2 μέρες να ξαναδώ πώς πάει, και αν χειροτερέψει πάμε σε γιατρό.",
           "Το παρακολουθώ. Σε 48 ώρες ξανακοιτάω την κατάσταση {fw}, και αν δεν βελτιωθεί κλείνω ραντεβού."],
    "C-EQ1": ["Ο σεισμός {mag} ρίχτηκα κάτω, κάλυψη, και μετά έφυγα από τις σκάλες προς την πλατεία. Ασανσέρ ποτέ. Εσύ είσαι καλά;"],
    "C-EQ2": ["Έλεγξα το σπίτι για ρωγμές και έβαλα το σακίδιο δίπλα στην πόρτα. Αν νιώσω μετασεισμό κατεβαίνω κάτω αμέσως."],
    "C-EQ3": ["Ένιωσα τον σεισμό ({mag}). Στερέωσα τα βαριά ράφια και τσέκαρα το EMSC. Τίποτα άλλο προς το παρόν."],
    "C-EQ4": ["Ήταν μικρός ({mag}). Τον σημείωσα και τίποτα άλλο."],
    "C-FI1": ["Έφυγα τώρα με το σακίδιο, ήρθε και το 112. Πήρα δρόμο αντίθετα από τον άνεμο. Θα πάρω τη γειτόνισσα στο δρόμο αν δεν με καθυστερήσει."],
    "C-FI2": ["Η φωτιά είναι {dist} χλμ και ο άνεμος φυσάει προς το μέρος μας. Φόρτωσα το αμάξι, η δεξαμενή είναι πάνω από μισή, παράθυρα κλειστά. Με το πρώτο 112 φεύγω."],
    "C-FI3": ["Παρακολουθώ τον χάρτη της φωτιάς κάθε μισή ώρα. Έχω έτοιμο το σακίδιο και δεν πάω προς τα εκεί."],
    "C-FI4": ["Είναι μακριά ({dist} χλμ). Θα ξανακοιτάξω το βράδυ."],
    "C-BO1": ["Με {h} ώρες χωρίς ρεύμα και {temp}° δεν κάθομαι. Πάω στη μαμά, παίρνω φάρμακα και χαρτιά και περνάω πρώτα από τη γειτόνισσα."],
    "C-BO2": ["Γέμισα νερά, φόρτισα τα πάντα και χτύπησα τη γειτόνισσα του 3ου. Αν περάσουν 6 ώρες πάω στη μαμά."],
    "C-BO3": ["Φόρτισα το power bank και δεν ανοίγω το ψυγείο. Βλέπω τη σελίδα του ΔΕΔΔΗΕ για ενημέρωση."],
    "C-BO4": ["Έφυγε το ρεύμα, έλεγξα τον διακόπτη μου, πρέπει να είναι γενικό. Περιμένω."],
    "C-HE1": ["{tmax}° για {d} μέρες. Ακύρωσα τις επισκέψεις στο εργοτάξιο, μέσα από τις 11 έως τις 18, και παίρνω τηλέφωνο τη γιαγιά δύο φορές τη μέρα."],
    "C-HE2": ["Έρχεται καύσωνας {tmax}°. Μετέφερα τις εξωτερικές δουλειές το πρωί, νερό παντού και τσεκάρω τους μεγάλους κάθε μέρα."],
    "C-HE3": ["{tmax}° μεθαύριο, θα βάλω το κλιματιστικό σε πρόγραμμα και θα πίνω περισσότερο νερό."],
    "C-HE4": ["Μια κανονική ζεστή μέρα, τίποτα το ιδιαίτερο."],
}
PROMPTS = ["Τι έγινε; Είσαι καλά;", "Πες μου τι κάνεις;", "Τι αποφάσισες;", "Όλα καλά; Τι θα κάνεις;"]
ACKS = ["οκ, πες μου αν θες κάτι", "Σωστά, καλά κάνεις", "Εντάξει, ενημέρωσέ με", "Τέλεια, προσοχή 👍"]
CONTACTS = ["Κατερίνα", "Νίκος", "Μαμά"]

EMAIL_WORK = {
    "M1": ("Offline today", "Hi {n},\n\nI need to be offline for the rest of the day for an urgent family/medical matter. Handover notes are in the project folder and {p} has the 15:00 client call.\n\nBest,\nEleni"),
    "M2": ("Doctor appointment tomorrow morning", "Hi {n},\n\nI'll be offline tomorrow until 11:00 for a doctor's appointment. Nothing urgent is pending; {p} has my notes.\n\nBest,\nEleni"),
    "C-BO1": ("Working from my parents' place today", "Hi {n},\n\nThere is a long power outage in my area, so I'm relocating and will work remotely from a different address today. I'm reachable by phone and email.\n\nBest,\nEleni"),
    "C-HE1": ("Site visits postponed due to heat", "Hi {n},\n\nWith the forecast above 43 C I'm postponing this week's site visits to early next week. Inspection data will be collected by drone where possible. I'll send a revised plan today.\n\nBest,\nEleni"),
    "C-FI1": ("Evacuated - working remotely", "Hi {n},\n\nI evacuated because of the fire near my area. I'm safe and will work remotely when I have a connection. Please reassign anything that cannot wait.\n\nBest,\nEleni"),
}


def ctx_for(s):
    d, t = s["data"], s["type"]
    c = {}
    if t == "triage":
        c["fw"] = PAT[d["patient"]][1]
        c["vit"] = ", ".join(x for x in [f"θερμοκρασία {d['temp_c']}" if "temp_c" in d else "", f"SpO2 {d['spo2']}" if "spo2" in d else ""] if x)
        c["proc"] = {"total knee replacement": "αντικατάσταση γόνατος", "spinal fusion": "σπονδυλοδεσία"}.get(d.get("procedure_recommended"), "επέμβαση")
    elif t == "earthquake":
        c["mag"] = d["magnitude"]
    elif t == "wildfire":
        c["dist"] = d["fire_distance_km"]
    elif t == "blackout":
        c["h"] = d["expected_duration_h"]
        c["temp"] = d["temp_c"]
    elif t == "heatwave":
        c["tmax"] = d["forecast_max_c"]
        c["d"] = d["duration_days"]
    return c


def tm_email(s, rid):
    d, t = s["data"], s["type"]
    if t == "workload":
        name, addr = PEOPLE[d["requester"]]
        first = name.split()[0]
        u = int(round(util(d) * 100))
        subj = f"Re: {d['task']}"
        body = {
            "T-LOAD1": f"Hi {first},\n\nThanks for thinking of me. With this I'd be at {u}% of my weekly capacity, so I can't take it on without something slipping.\n\nOptions:\n- Move the deadline by 3 days\n- Reduce the scope to the essentials\n- Hand part of it to someone else\n\nLet me know which works for you.\n\nBest,\nEleni",
            "T-LOAD2": f"Hi {first},\n\nI can take this on if the other deliverable moves by two days; otherwise I'm running without any buffer (I'd be at {u}%). Let me know if that works.\n\nBest,\nEleni",
            "T-LOAD3": f"Hi {first},\n\nSure, I can take this. I'll plan it for the middle of the week and add a 20% buffer.\n\nThanks!\nEleni",
        }[rid]
        return name, addr, subj, body
    if t == "slip":
        if d["client_facing"]:
            name, addr = PEOPLE["client"]
        else:
            name, addr = PEOPLE["manager"]
        first = name.split()[0]
        task, sl = d["task"], d["slip_days"]
        body = {
            "T-SLIP1": f"Hi {first},\n\nI'm flagging this early: {task} will be {sl} days late. I'd rather you hear it from me today than find out on the deadline.\n\nRecovery plan:\n- A second engineer joins from tomorrow\n- Weekend work on the critical path\n- Revised date confirmed by Friday\n\nCould we take 20 minutes today to go through it? I'm copying Giorgos.\n\nBest,\nEleni",
            "T-SLIP2": f"Hi {first},\n\nQuick heads-up: {task} will land {sl} day(s) after the agreed date.\n\nOptions:\n- Revised date with the full scope\n- Reduced-scope version on the original date\n\nTell me which you prefer and I'll confirm today.\n\nBest,\nEleni",
            "T-SLIP3": f"Hi {first},\n\n{task} is {sl} days behind. It's not client-visible yet.\n\nOption A: add one person for three days.\nOption B: move the downstream milestone by {sl} days.\n\nI'd like your decision by tomorrow.\n\nBest,\nEleni",
            "T-SLIP4": f"Hi {first},\n\nSmall slip on {task} ({sl} day). I'm absorbing it with the buffer, so there's no impact on the milestone. Mentioning it for the weekly update.\n\nBest,\nEleni",
        }[rid]
        return name, addr, f"{task} - status", body
    if t == "focus":
        name, addr = PEOPLE[d["organizer"]]
        first = name.split()[0]
        body = {
            "T-FOCUS1": f"Hi {first},\n\nI keep Tuesday and Thursday mornings for deep work. Could we do this at 14:00 instead?\n\nBest,\nEleni",
            "T-FOCUS2": f"Hi {first},\n\nYes, I'll join. I'm moving my deep-work block to Wednesday morning.\n\nBest,\nEleni",
            "T-FOCUS3": f"Hi {first},\n\nWorks for me. See you then.\n\nBest,\nEleni",
        }[rid]
        return name, addr, f"Re: {d['topic']}", body


chats, emails, notes = [], [], []
cid = eid = nid = 0


def iso(date_str, hh, mm=0):
    y, m, dd = map(int, date_str.split("-"))
    return dt.datetime(y, m, dd, hh, mm, tzinfo=UTC)


for s in sorted([x for x in S if not x["test"]], key=lambda x: x["date"]):
    rid = s["truth"]["rule_id"]
    # chat (Greek) for medical + crisis
    if s["domain"] in ("medical", "crisis"):
        cid += 1
        contact = rng.choice(CONTACTS)
        if s["domain"] == "medical" and s["data"]["patient"] == "partner":
            contact = "Κατερίνα"
        elif s["domain"] == "medical" and s["data"]["patient"] == "mother":
            contact = "Νίκος"
        text = fmt(rng.choice(CHAT_TPL[rid]), ctx_for(s))
        h = rng.randint(8, 21)
        chats.append({"id": f"chat-{cid:03d}", "channel": "messenger", "participants": ["Eleni", contact],
                      "date": s["date"], "related_scenario": s["id"],
                      "messages": [
                          {"from": contact, "ts": iso(s["date"], h, 2).isoformat(), "text": rng.choice(PROMPTS)},
                          {"from": "Eleni", "ts": iso(s["date"], h, 5).isoformat(), "text": text},
                          {"from": contact, "ts": iso(s["date"], h, 6).isoformat(), "text": rng.choice(ACKS)}]})
    # email
    if s["domain"] == "time_management":
        to_name, to_addr, subj, body = tm_email(s, rid)
        emails.append(dict(date=iso(s["date"], 9, 30), frm=ELENI, to=(to_name, to_addr), subject=subj, body=body, direction="outgoing", related=s["id"]))
    elif rid in EMAIL_WORK:
        subj, body = EMAIL_WORK[rid]
        body = body.format(n="Giorgos", p="Maria")
        emails.append(dict(date=iso(s["date"], 8, 15), frm=ELENI, to=PEOPLE["manager"], subject=subj, body=body, direction="outgoing", related=s["id"]))
    # decision-log note
    nid += 1
    notes.append({"id": f"note-{nid:03d}", "date": s["date"], "type": "decision_log",
                  "title": f"Decision log: {s['type']} ({s['date']})",
                  "text": f"# Decision log - {s['date']}\n\n**Situation:** {s['situation']}\n\n**Risk level I assigned:** {s['truth']['risk_level']}\n\n"
                          f"**What I did:** {s['truth']['decision']}\n\n**Why:** {s['truth']['rationale']}\n",
                  "related_scenario": s["id"]})

# ---- generic (non-scenario) footprint: style, preferences, everyday life ----
PROJ = ["Pier refurbishment", "Harbour bridge inspection", "Warehouse extension", "Quay wall retrofit"]
NAMES = ["Giorgos", "Maria", "Dimitris", "Sofia"]
THINGS = ["load calculation sheet", "survey data", "cable supports", "formwork rental", "geotechnical report"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
OUT_G = [
    ("Weekly update - {proj}", "Hi {n},\n\nThis week:\n- {a}\n- {b}\n\nNext week:\n- {c}\n\nNo blockers on my side.\n\nBest,\nEleni"),
    ("Re: Meeting {day}", "Hi {n},\n\n{time} works for me. I'll bring the updated schedule. Please send the agenda beforehand so I can prepare.\n\nBest,\nEleni"),
    ("Site visit - {proj}", "Hi {n},\n\nI'd like to do the site visit on {day} morning, before it gets hot. Safety briefing at 08:30, helmets and vests on arrival.\n\nCan you confirm access for two people?\n\nThanks!\nEleni"),
    ("Quote follow-up", "Hi {n},\n\nFollowing up on the quote for the {thing}. Could you confirm the delivery date and whether the price includes transport? I need both before Friday.\n\nBest,\nEleni"),
    ("Re: Draft comments", "Hi {n},\n\nThanks for the comments. I accepted most of them. Two points I'd keep as they are:\n- the load assumption (it follows the code, I added the reference)\n- the section order (the client asked for it)\n\nUpdated version attached.\n\nBest,\nEleni"),
]
IN_G = [
    ("Quick question on {proj}", "Hi Eleni,\n\nCould you tell me where the latest {thing} is saved? I can't find it in the project folder.\n\n{n}"),
    ("Invitation: {proj} review", "Hi Eleni,\n\nI'd like to schedule a review of {proj} on {day}. Does {time} work for you?\n\n{n}"),
    ("Reminder: timesheets", "Hi all,\n\nGentle reminder to submit your timesheets by Friday 17:00.\n\n{n}"),
]
APICKS = ["finished the bearing checks", "updated the BIM model", "reviewed contractor RFIs", "closed 6 of 9 site comments", "issued the revised drawings"]
for i in range(30):
    d0 = start + dt.timedelta(days=rng.randrange(span + 30))
    ctxe = dict(proj=rng.choice(PROJ), n=rng.choice(NAMES), thing=rng.choice(THINGS), day=rng.choice(DAYS),
                time=rng.choice(["10:30", "14:00", "15:30", "16:00"]), a=rng.choice(APICKS), b=rng.choice(APICKS), c=rng.choice(APICKS))
    if i % 5 < 3:
        subj, body = rng.choice(OUT_G)
        emails.append(dict(date=iso(d0.isoformat(), rng.randint(8, 18), rng.randint(0, 59)), frm=ELENI,
                           to=(ctxe["n"] + " " + rng.choice(["K.", "P.", "S."]), ctxe["n"].lower() + "@aegeanstructures.example"),
                           subject=fmt(subj, ctxe), body=fmt(body, ctxe), direction="outgoing", related=None))
    else:
        subj, body = rng.choice(IN_G)
        emails.append(dict(date=iso(d0.isoformat(), rng.randint(8, 18), rng.randint(0, 59)),
                           frm=(ctxe["n"] + " P.", ctxe["n"].lower() + "@aegeanstructures.example"), to=ELENI,
                           subject=fmt(subj, ctxe), body=fmt(body, ctxe), direction="incoming", related=None))

THREADS = [
    ("Κατερίνα", [("K", "Τι κάνεις; Βγαίνουμε Σάββατο;"), ("E", "Ναι, αλλά όχι αργά. Πρωί βουνό και μετά καφές;"), ("K", "Παρνήθα;"), ("E", "Τέλεια, 8:00 στο σημείο. Θα φέρω φρούτα και νερό για όλους.")]),
    ("Μαμά", [("K", "Θα έρθεις Κυριακή για φαγητό;"), ("E", "Ναι, μαμά, θα έρθω 14:00. Θες να φέρω κάτι;"), ("K", "Ένα γλυκό."), ("E", "οκ, θα πάρω από το φούρνο.")]),
    ("Νίκος", [("K", "Πάμε σινεμά απόψε;"), ("E", "Απόψε είμαι κουρασμένη, ας το αφήσουμε για αύριο. Πες μου ώρα."), ("K", "Οκ, 21:00;"), ("E", "Συμφωνώ 👍")]),
    ("Μαρία (δουλειά)", [("K", "Έχεις δει το νέο πρόγραμμα του έργου;"), ("E", "Ναι, το κοίταξα. Η φάση 2 είναι σφιχτή, θα βάλω 20% buffer στις εκτιμήσεις."), ("K", "Ωραία, στείλ' το και σε μένα."), ("E", "Θα το στείλω σε μισή ώρα.")]),
    ("Νίκος", [("K", "Τι να πάρω από το σούπερ μάρκετ;"), ("E", "Γάλα, φρούτα, καφέ. Γράψε μου και τι χρειάζεσαι εσύ.")]),
    ("Κατερίνα", [("K", "Διάβασες το βιβλίο που σου έδωσα;"), ("E", "Μισό. Μ' αρέσει, αλλά διαβάζω μόνο το βράδυ. Θα το τελειώσω μέχρι την Κυριακή.")]),
    ("Νίκος", [("K", "Σε πήρα και δεν σήκωσες."), ("E", "Ήμουν σε σύσκεψη. Προτιμώ να γράφεις μήνυμα, θα απαντήσω μόλις μπορέσω.")]),
    ("Μαμά", [("K", "Θυμήθηκες τα γενέθλια της θείας;"), ("E", "Ναι, έχω ήδη πάρει δώρο. Θα το δώσω την Κυριακή.")]),
    ("Κατερίνα", [("K", "Γυμναστήριο αύριο;"), ("E", "Ναι, 7:30 πριν τη δουλειά. Αν αργήσω μην περιμένεις.")]),
    ("Μαρία (δουλειά)", [("K", "Να μετακινήσουμε τη σύσκεψη της Πέμπτης;"), ("E", "Όχι το πρωί, κρατάω Τρίτες και Πέμπτες πρωί για να δουλεύω χωρίς διακοπές. Απόγευμα;")]),
    ("Νίκος", [("K", "Πάμε εκδρομή το Σαββατοκύριακο;"), ("E", "Ναι, αλλά θέλω πρώτα να δω την πρόγνωση. Αν έχει καύσωνα δεν κάνουμε βουνό.")]),
    ("Κατερίνα", [("K", "Πάμε για καφέ;"), ("E", "Ναι, φρέντο εσπρέσο χωρίς ζάχαρη. Στη γωνία στις 17:30;")]),
]
for contact, msgs in THREADS:
    cid += 1
    d0 = start + dt.timedelta(days=rng.randrange(span + 30))
    h = rng.randint(9, 21)
    chats.append({"id": f"chat-{cid:03d}", "channel": "messenger", "participants": ["Eleni", contact], "date": d0.isoformat(),
                  "related_scenario": None,
                  "messages": [{"from": ("Eleni" if w == "E" else contact), "ts": iso(d0.isoformat(), h, 2 * j).isoformat(), "text": tx} for j, (w, tx) in enumerate(msgs)]})

GENERIC_NOTES = [
    ("How I work", "personal", "# How I work\n\n- I plan the week on Monday morning.\n- Estimates get a 20% buffer.\n- Tuesday and Thursday mornings are for deep work: no meetings unless it is the client or it is urgent.\n- I prefer written updates over calls.\n- If a deadline will slip I say so as early as possible, with options, never on the deadline day.\n"),
    ("Go-bag checklist", "personal", "# Go-bag (by the front door)\n\n- Water 2 L, snacks\n- Copies of documents + cash\n- Power bank, phone charger, torch, small radio\n- Medication for 3 days\n- Whistle, mask, sturdy shoes\n- Check expiry dates every spring\n"),
    ("Emergency contacts (fictional)", "personal", "# Emergency contacts\n\n- Mum (Peristeri): +30 210 000 0001\n- Nikos: +30 690 000 0002\n- Katerina: +30 690 000 0003\n- Emergency: 112 / EKAB 166 / Fire 199\n"),
    ("Reading list", "personal", "# Reading list\n\n- Thinking in Systems\n- The Checklist Manifesto\n- A Greek novel for the summer\n"),
    ("Weekend plan - Parnitha", "personal", "# Weekend plan\n\nMeet 08:00 at the trailhead, bring water and fruit. Back for coffee by 13:00. Cancel if forecast is above 36 C.\n"),
    ("Meeting notes template", "work", "# Meeting notes\n\n**Decisions** / **Actions (owner, date)** / **Risks**\n\nAlways write the action list during the meeting, send within an hour.\n"),
    ("Site visit packing list", "work", "# Site visit\n\nHelmet, vest, boots, gloves, sunscreen, 1.5 L water, tablet with latest drawings, spare battery.\n"),
    ("Gift ideas", "personal", "# Gift ideas\n\n- Mum: ceramic planter\n- Nikos: trail running socks\n- Katerina: notebook\n"),
    ("Balcony ideas", "personal", "# Balcony\n\nHerbs (basil, oregano), a small shade net for summer, drip watering on a timer.\n"),
    ("Communication preferences", "personal", "# Communication\n\nText over calls. Short and specific. I answer within a few hours; if it is urgent, say 'urgent' in the first line.\n"),
]
for title, typ, text in GENERIC_NOTES:
    nid += 1
    d0 = start + dt.timedelta(days=rng.randrange(span))
    notes.append({"id": f"note-{nid:03d}", "date": d0.isoformat(), "type": typ, "title": title, "text": text, "related_scenario": None})

DOCS = [
    ("Project status report - Pier refurbishment (excerpt)", "# Status report - Pier refurbishment\n\n**Overall:** amber. Phase 2 drawings are the critical path.\n\n**Risks**\n1. Contractor access to the quay (mitigation: weekend slot booked)\n2. Material delivery +4 days (mitigation: alternative supplier quoted)\n\n**Decisions needed:** approval of the reduced-scope option for the inspection report.\n"),
    ("Personal emergency plan", "# Personal emergency plan (Eleni)\n\n1. Earthquake: drop-cover-hold, stairs, assembly point at the square. Go-bag by the door.\n2. Wildfire: monitor the fire map; leave early if wind is toward home; keep the car above half a tank in summer.\n3. Blackout: power bank, torches, fridge closed, check on the elderly neighbour; mum's place as fallback.\n4. Heatwave: avoid 11:00-18:00 outdoors, call grandparents.\n"),
    ("Lessons learned - Warehouse extension", "# Lessons learned\n\n- Escalating the delay late cost us trust; escalate early with options.\n- A 20% buffer in estimates paid for itself three times.\n- Protect focus time; most errors came from interrupted calculation days.\n"),
]
for i, (title, text) in enumerate(DOCS, 1):
    wtext(f"footprint/documents/doc-{i:02d}.md", text)

# --------------------------------------------------------------------------------------
# 6. Write everything
# --------------------------------------------------------------------------------------
emails.sort(key=lambda e: e["date"])
email_rows = []
for i, e in enumerate(emails, 1):
    m = EmailMessage()
    m["From"] = f"{e['frm'][0]} <{e['frm'][1]}>"
    m["To"] = f"{e['to'][0]} <{e['to'][1]}>"
    m["Subject"] = e["subject"]
    m["Date"] = format_datetime(e["date"])
    m["Message-ID"] = f"<email-{i:03d}@synthetic.example>"
    m.set_content(e["body"])
    wtext(f"footprint/emails/email-{i:03d}.eml", m.as_string())
    email_rows.append({"id": f"email-{i:03d}", "date": e["date"].isoformat(), "from": e["frm"][1], "to": e["to"][1],
                       "direction": e["direction"], "subject": e["subject"], "body": e["body"], "related_scenario": e["related"]})
wjsonl("footprint/emails.jsonl", email_rows)

chats.sort(key=lambda c: c["date"])
wjsonl("footprint/chats/chats.jsonl", chats)

for n in notes:
    wtext(f"footprint/notes/{n['id']}.md", f"---\ntitle: {n['title']}\ndate: {n['date']}\ntype: {n['type']}\n---\n\n{n['text']}")

hist_rows, test_rows, gt_rows = [], [], []
for s in sorted(S, key=lambda x: (x["test"], x["date"])):
    base = dict(scenario_id=s["id"], domain=s["domain"], type=s["type"], date=s["date"], situation=s["situation"], data=s["data"], question=QUESTION)
    if s["test"]:
        test_rows.append(base)
        gt_rows.append(dict(scenario_id=s["id"], **s["truth"]))
    else:
        hist_rows.append(dict(base, answer=s["truth"]))
wjsonl("scenarios/history_decisions.jsonl", hist_rows)
wjsonl("scenarios/test_scenarios.jsonl", test_rows)
wjsonl("evaluation/test_ground_truth.jsonl", gt_rows)
wjson("evaluation/persona_ground_truth_DO_NOT_FEED_TO_TWIN.json", PERSONA)

# --- summary ---
from collections import Counter
print("emails", len(emails), "chats", len(chats), "notes", len(notes), "docs", len(DOCS))
print("history", len(hist_rows), "test", len(test_rows))
hr = Counter(r["answer"]["rule_id"] for r in hist_rows)
tr = Counter(r["rule_id"] for r in gt_rows)
print("test rules NOT covered by history:", [k for k in tr if k not in hr])
print("test risk distribution:", dict(Counter(r["risk_level"] for r in gt_rows)))
print("history risk distribution:", dict(Counter(r["answer"]["risk_level"] for r in hist_rows)))

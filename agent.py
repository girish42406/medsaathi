"""MedSaathi agent: Gemini khud decide karta hai kaunsa tool chalana hai.

Tools: read_label, fda_lookup, check_interaction, check_expiry
Safety: dose nahi, "kaunsi dawai lo" nahi, sirf tool ke text se jawab.
"""
import calendar
import re
import time
from datetime import date
from typing import List, Optional

import requests
from google.genai import errors, types

FDA_URL = "https://api.fda.gov/drug/label.json"

FIELDS = [
    "boxed_warning",
    "contraindications",
    "do_not_use",
    "warnings",
    "warnings_and_cautions",
    "ask_doctor",
    "ask_doctor_or_pharmacist",
    "stop_use",
    "pregnancy",
    "pregnancy_or_breast_feeding",
    "pediatric_use",
    "geriatric_use",
    "use_in_specific_populations",
]

SYSTEM = (
    "You are MedSaathi, an information assistant for medicines. "
    "You MUST use the tools to get facts. Never answer a medical fact from your "
    "own memory. Use ONLY the text returned by the tools. "
    "Rules: (1) Never give a dose. (2) Never suggest which medicine to take or "
    "to stop. (3) If a tool finds nothing, say 'no information found in the FDA "
    "label, this does not mean it is safe, ask a doctor or pharmacist'. "
    "(4) For every medical statement, say which tool/source it came from "
    "(for example 'FDA label: warnings'). (5) Keep the answer short, in simple "
    "words, as bullet points. Do not add a disclaimer, the app shows it."
)


def _sents(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def _fda_label(name):
    """FDA label ke hisse (dict). Fail ho toh khali dict."""
    try:
        r = requests.get(
            FDA_URL,
            params={"search": 'openfda.generic_name:"%s"' % name, "limit": 5},
            timeout=15,
        )
        if r.status_code != 200:
            return {}
        out = {}
        for res in r.json().get("results", []):
            for f in FIELDS + ["drug_interactions"]:
                if f not in out and res.get(f):
                    out[f] = " ".join(res[f])
        return out
    except requests.RequestException:
        return {}


def run_agent(client, models, question, meds, lang_name, profile_text=""):
    """Returns (answer_text, steps_log). meds = list of dicts (photo se padhe)."""
    log = []

    # ---- Tools (nested, taaki meds aur log use kar sakein) ----

    def read_label(photo_number: int) -> dict:
        """Returns what was read from medicine photo number N (1 = first photo):
        brand, generic salt name, synonym names, use, expiry (MM/YYYY).
        Call this first to know which medicines the user uploaded."""
        i = photo_number - 1
        if i < 0 or i >= len(meds):
            res = {"error": "no such photo, there are %d photos" % len(meds)}
        else:
            res = meds[i]
        log.append("read_label(%s)" % photo_number)
        return res

    def check_expiry(expiry: str) -> dict:
        """Checks an expiry date given as MM/YYYY. Returns status:
        expired, expiring_soon (under 90 days), ok, or unclear."""
        log.append("check_expiry(%s)" % expiry)
        m = re.search(r"(\d{1,2})\s*/\s*(\d{4})", expiry or "")
        if not m or not 1 <= int(m.group(1)) <= 12:
            return {"status": "unclear"}
        month, year = int(m.group(1)), int(m.group(2))
        last = date(year, month, calendar.monthrange(year, month)[1])
        days = (last - date.today()).days
        if days < 0:
            return {"status": "expired", "days_ago": -days}
        if days <= 90:
            return {"status": "expiring_soon", "days_left": days}
        return {"status": "ok", "days_left": days}

    def fda_lookup(drug_name: str, topic: str) -> dict:
        """Looks up the US FDA label of a drug (generic salt name, English) and
        returns sentences about a topic, for example 'pregnancy', 'kidney',
        'liver', 'asthma', 'children', 'elderly', 'stomach ulcer', 'general'."""
        log.append("fda_lookup(%s, %s)" % (drug_name, topic))
        label = _fda_label(drug_name.lower())
        if not label:
            return {"found": False, "note": "no FDA label found"}
        t = topic.lower()
        if t == "general":
            kws = []
            fields = ["boxed_warning", "contraindications", "do_not_use"]
        else:
            kws = [w for w in re.split(r"[\s/,]+", t) if len(w) > 2]
            fields = FIELDS
        hits = []
        for f in fields:
            for s in _sents(label.get(f, "")):
                if (not kws or any(k[:6] in s.lower() for k in kws)) and s[:300] not in hits:
                    hits.append("[%s] %s" % (f, s[:300]))
        return {"found": True, "sentences": hits[:4]}

    def check_interaction(drug_a: str, drug_b: str) -> dict:
        """Checks if the FDA label of drug A mentions drug B (or the reverse) in
        its drug_interactions section. Use generic salt names in English."""
        log.append("check_interaction(%s, %s)" % (drug_a, drug_b))
        a, b = drug_a.lower(), drug_b.lower()
        la, lb = _fda_label(a), _fda_label(b)
        ta, tb = la.get("drug_interactions", ""), lb.get("drug_interactions", "")
        if not ta and not tb:
            return {"label_found": False, "note": "no interaction text in FDA labels"}
        hits = [s[:300] for s in _sents(ta) if b in s.lower()]
        hits += [s[:300] for s in _sents(tb) if a in s.lower()]
        if not hits:
            return {
                "label_found": True,
                "pair_mentioned": False,
                "note": "labels found but this pair is not mentioned; not a guarantee",
            }
        return {"label_found": True, "pair_mentioned": True, "sentences": hits[:4]}

    tools = [read_label, check_expiry, fda_lookup, check_interaction]

    prompt = (
        "The user uploaded %d medicine photo(s). Answer in %s.\n"
        "User profile: %s\nUser question: %s"
        % (len(meds), lang_name, profile_text or "not given", question)
    )
    cfg = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=12
        ),
    )

    for _ in range(3):
        for model in models:
            try:
                log.clear()
                r = client.models.generate_content(
                    model=model, contents=prompt, config=cfg
                )
                if r.text:
                    return r.text, list(log)
            except (errors.APIError, ValueError) as e:
                log.append("model %s fail: %s" % (model, str(e)[:120]))
        time.sleep(2)
    return None, list(log)

import calendar
import json
import re
import time
from datetime import date
from itertools import combinations

import requests
import streamlit as st
from google import genai
from google.genai import types, errors

st.set_page_config(page_title="MedSaathi", page_icon="💊")

MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.8-flash"]
client = genai.Client()

PROMPT = (
    "Is dawai ke label se ye nikaalo. Sirf JSON do, aur kuch nahi: "
    '{"brand": "", "generic": "", "names": [], "use_hindi": "", "expiry": ""}. '
    "generic = English me asli salt ka sabse common naam. "
    "names = us salt ke saare common English naam/synonyms ki list, US wale naam "
    'ke saath (jaise ["acetaminophen", "paracetamol"] ya '
    '["aspirin", "acetylsalicylic acid"]). '
    "use_hindi = kis kaam aati hai, Devanagari (हिंदी) script me, simple bhasha me. "
    "expiry = MM/YYYY format me. "
    "Jo saaf na dikhe usse null rakho, andaza mat lagao."
)

KEYWORDS = (
    "concomitant",
    "co-administ",
    "coadminist",
    "concurrent",
    "together",
    "combination",
    "taken with",
    "used with",
)


def ask(contents, as_json=True):
    cfg = None
    if as_json:
        cfg = types.GenerateContentConfig(response_mime_type="application/json")
    for model in MODELS:
        try:
            r = client.models.generate_content(
                model=model, contents=contents, config=cfg
            )
            return json.loads(r.text) if as_json else r.text
        except (errors.APIError, ValueError):
            time.sleep(2)
    return None


@st.cache_data(show_spinner=False)
def fda_one(name):
    """Ek naam ke liye FDA label ka drug_interactions text (ya None)."""
    try:
        r = requests.get(
            "https://api.fda.gov/drug/label.json",
            params={
                "search": f'openfda.generic_name:"{name}" AND _exists_:drug_interactions',
                "limit": 3,
            },
            timeout=15,
        )
        if r.status_code != 200:
            return None
        parts = []
        for res in r.json().get("results", []):
            parts += res.get("drug_interactions", [])
        return " ".join(parts) if parts else None
    except requests.RequestException:
        return None


def fda_for(names):
    for n in names:
        text = fda_one(n)
        if text:
            return text
    return None


def names_of(med):
    names = [str(n).lower() for n in (med.get("names") or []) if n]
    if med.get("generic"):
        names.append(str(med["generic"]).lower())
    return list(dict.fromkeys(names))


def mentions(text, others):
    if not text:
        return []
    sentences = re.split(r"(?<=[.;])\s+", text)
    hits = [s.strip() for s in sentences if any(o in s.lower() for o in others)]
    hits.sort(key=lambda s: not any(k in s.lower() for k in KEYWORDS))
    return hits[:3]


def show_expiry(exp):
    m = re.search(r"(\d{1,2})\s*/\s*(\d{4})", exp or "")
    if not m:
        st.info("Expiry saaf nahi dikhi, strip pe khud dekh lo.")
        return
    month, year = int(m.group(1)), int(m.group(2))
    if not 1 <= month <= 12:
        st.info("Expiry saaf nahi dikhi, strip pe khud dekh lo.")
        return
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    days = (last_day - date.today()).days
    if days < 0:
        st.error(f"❌ Expiry: {exp}. Ye dawai expire ho chuki hai, mat khao.")
    elif days <= 90:
        st.warning(f"⚠️ Expiry: {exp}. Jaldi expire hogi ({days} din baaki).")
    else:
        st.success(f"✅ Expiry: {exp}. Abhi theek hai.")


def med_card(photo, info):
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(photo)
        with c2:
            st.subheader(info.get("brand") or info.get("generic") or "Dawai")
            if info.get("generic"):
                st.caption(f"Salt: {info['generic']}")
            if info.get("use_hindi"):
                st.write(f"**Kaam:** {info['use_hindi']}")
            show_expiry(info.get("expiry"))


st.title("MedSaathi 💊")
st.caption("Dawai ki photo daalo, hum bataenge ye kya hai aur saath lene me savdhani.")

photos = st.file_uploader(
    "Dawai ki photo(s) daalo",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if photos:
    meds = []
    for p in photos:
        with st.spinner("Padh raha hoon..."):
            info = ask(
                [types.Part.from_bytes(data=p.getvalue(), mime_type=p.type), PROMPT]
            )
        if info:
            info = {
                k: (None if v in ("null", "", "None") else v) for k, v in info.items()
            }
            meds.append(info)
            med_card(p, info)
        else:
            st.error("Ye photo padh nahi paya, dobara try karo.")

    if len(meds) >= 2:
        st.header("Saath lene ki savdhani")
        for a, b in combinations(meds, 2):
            na, nb = names_of(a), names_of(b)
            if not na or not nb:
                continue
            ga, gb = a.get("generic") or na[0], b.get("generic") or nb[0]
            with st.container(border=True):
                st.subheader(f"{ga} + {gb}")
                ta, tb = fda_for(na), fda_for(nb)
                if not ta and not tb:
                    st.info("FDA label data nahi mila. Pharmacist se zaroor poochho.")
                    continue
                hits = mentions(ta, nb) + mentions(tb, na)
                if hits:
                    snippet = " ".join(hits)
                    hindi = ask(
                        "Neeche FDA label ka text hai. Sirf isi text ke basis par, "
                        "simple Hindi (Devanagari) me 2-3 line me batao ki "
                        f"{ga} aur {gb} saath lene me kya savdhani hai. "
                        "Agar ye text dono dawai ek saath lene ke baare me nahi hai "
                        "(jaise sirf allergy ya kisi bimari ke baare me), toh pehli "
                        "line me saaf likho: 'Ye dono ek saath lene ki baat nahi hai.' "
                        "Apni taraf se kuch mat jodo.\n\n" + snippet,
                        as_json=False,
                    )
                    st.warning(hindi or "Interaction mila hai, pharmacist se poochho.")
                    with st.expander("FDA label ka original text (source)"):
                        st.write(snippet)
                else:
                    st.success(
                        "FDA label me inka seedha interaction mention nahi mila. "
                        "Ye guarantee nahi hai, pharmacist se zaroor poochho."
                    )

    st.divider()
    st.caption(
        "⚠️ Ye sirf jaankari ke liye hai, doctor/pharmacist ki salah ka "
        "vikalp nahi. Dose aur dawai ka faisla hamesha doctor se karwao."
    )
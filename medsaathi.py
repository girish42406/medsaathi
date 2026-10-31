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
client = genai.Client(http_options=types.HttpOptions(timeout=30000))
LAST_ERR = {"msg": ""}

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

# FDA label ke wo hisse jahan warnings hoti hain
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
GENERAL_FIELDS = ["boxed_warning", "contraindications", "do_not_use"]

# condition -> (Hindi naam, label me dhundhne ke shabd)
COND = {
    "pregnancy": ("Pregnancy / doodh pilana", ["pregnan", "breast", "nursing", "lactat", "fetal", "fetus"]),
    "kidney": ("Kidney ki problem", ["renal", "kidney"]),
    "liver": ("Liver ki problem", ["hepatic", "liver"]),
    "asthma": ("Asthma", ["asthma", "bronchospasm"]),
    "heart_bp": ("BP / dil ki bimari", ["hypertension", "blood pressure", "cardiovascular", "heart failure", "myocardial"]),
    "stomach": ("Pet ka ulcer / acidity", ["ulcer", "gastrointestinal", "stomach", "bleeding"]),
    "child": ("Bachche (12 se kam)", ["pediatric", "children", "child", "reye"]),
    "elderly": ("Buzurg (65+)", ["geriatric", "elderly", "older patients", "older adults"]),
}
COND_CHOICES = {
    "Pregnancy / doodh pilana": "pregnancy",
    "Kidney ki problem": "kidney",
    "Liver ki problem": "liver",
    "Asthma": "asthma",
    "BP / dil ki bimari": "heart_bp",
    "Pet ka ulcer / acidity": "stomach",
}


def ask(contents, as_json=True):
    cfg = None
    if as_json:
        cfg = types.GenerateContentConfig(response_mime_type="application/json")
    for _ in range(3):
        for model in MODELS:
            try:
                r = client.models.generate_content(
                    model=model, contents=contents, config=cfg
                )
                return json.loads(r.text) if as_json else r.text
            except (errors.APIError, ValueError) as e:
                LAST_ERR["msg"] = f"{model}: {str(e)[:200]}"
        time.sleep(2)
    return None


@st.cache_data(show_spinner=False)
def read_photo(data, mime):
    info = ask([types.Part.from_bytes(data=data, mime_type=mime), PROMPT])
    if info is None:
        raise RuntimeError("photo read failed")  # fail hua result cache nahi hota
    return info


@st.cache_data(show_spinner=False)
def label_one(name):
    """Ek naam ke liye FDA label ke warning wale hisse (dict)."""
    try:
        r = requests.get(
            "https://api.fda.gov/drug/label.json",
            params={"search": f'openfda.generic_name:"{name}"', "limit": 5},
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


def label_for(names):
    for n in names:
        d = label_one(n)
        if d:
            return d
    return {}


def names_of(med):
    names = [str(n).lower() for n in (med.get("names") or []) if n]
    if med.get("generic"):
        names.append(str(med["generic"]).lower())
    return list(dict.fromkeys(names))


def split_sents(text):
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", text) if s.strip()]


def mentions(text, others):
    if not text:
        return []
    hits = [s for s in split_sents(text) if any(o in s.lower() for o in others)]
    hits.sort(key=lambda s: not any(k in s.lower() for k in KEYWORDS))
    return hits[:3]


def find_sents(label, kws, n=2):
    hits = []
    for f in FIELDS:
        for s in split_sents(label.get(f, "")):
            if any(k in s.lower() for k in kws) and s[:300] not in hits:
                hits.append(s[:300])
    return hits[:n]


def general_sents(label, n=3):
    out = []
    for f in GENERAL_FIELDS:
        out += [s[:300] for s in split_sents(label.get(f, ""))]
    return out[:n]


@st.cache_data(show_spinner=False)
def summarize(generic, payload_json):
    text = ask(
        f"Neeche {generic} ke FDA label ke hisse hain (JSON). Sirf isi text ke "
        "basis par sirf Devanagari (हिंदी) script me, Roman ya English me nahi, "
        "chhote bullets banao (headings bhi Devanagari me): pehle "
        "'कौन न ले / सावधानी' (general), phir har condition ke liye alag bullet. "
        "Jis condition ka text khali ho uske liye likho 'label me alag se warning "
        "nahi mili (iska matlab ye nahi ki ye surakshit hai, doctor se poochho)'. "
        "Shuru me 'diye gaye text ke aadhar par' jaisi bhoomika mat likho. "
        "Apni taraf se kuch mat jodo aur dose kabhi mat batao.\n\n" + payload_json,
        as_json=False,
    )
    if not text:
        raise RuntimeError("summary failed")
    return text


def show_expiry(exp):
    m = re.search(r"(\d{1,2})\s*/\s*(\d{4})", exp or "")
    if not m or not 1 <= int(m.group(1)) <= 12:
        st.info("Expiry saaf nahi dikhi, strip pe khud dekh lo.")
        return
    month, year = int(m.group(1)), int(m.group(2))
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


# ---------- Sidebar: profile ----------
st.sidebar.header("Aapki profile (optional)")
st.sidebar.caption("Ye kahin save nahi hoti, sirf isi session me use hoti hai.")
age = st.sidebar.radio("Umar", ["Adult", "Bachcha (12 se kam)", "Buzurg (65+)"])
chosen = st.sidebar.multiselect("Koi condition?", list(COND_CHOICES))
allergy_txt = st.sidebar.text_input("Allergy (comma se alag karo, jaise aspirin)")

selected = [COND_CHOICES[c] for c in chosen]
if age.startswith("Bachcha"):
    selected.append("child")
if age.startswith("Buzurg"):
    selected.append("elderly")
allergies = [a.strip().lower() for a in allergy_txt.split(",") if a.strip()]

# ---------- Main ----------
st.title("MedSaathi 💊")
st.caption("Dawai ki photo daalo, hum bataenge ye kya hai aur kya savdhani rakhni hai.")

photos = st.file_uploader(
    "Dawai ki photo(s) daalo",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if photos:
    meds = []
    for p in photos:
        try:
            with st.spinner("Padh raha hoon..."):
                info = read_photo(p.getvalue(), p.type)
        except RuntimeError:
            st.error("Ye photo padh nahi paya, dobara try karo.")
            st.caption(LAST_ERR["msg"])
            continue
        info = {k: (None if v in ("null", "", "None") else v) for k, v in info.items()}
        meds.append(info)
        med_card(p, info)

    # ----- Kaun na le / profile ke hisaab se savdhani -----
    if meds:
        st.header("Kaun na le / aapke liye savdhani")
        for med in meds:
            names = names_of(med)
            if not names:
                continue
            g = med.get("generic") or names[0]
            with st.container(border=True):
                st.subheader(g)
                bad = [a for a in allergies if any(a in n or n in a for n in names)]
                if bad:
                    st.error(
                        f"❌ Aapne {', '.join(bad)} se allergy bataayi hai. "
                        "Ye dawai usi salt ki hai, mat lo, doctor se poochho."
                    )
                label = label_for(names)
                if not label:
                    st.info("FDA label data nahi mila. Pharmacist se zaroor poochho.")
                    continue
                gen = general_sents(label)
                hits = {k: find_sents(label, COND[k][1]) for k in selected}
                payload = {
                    "general": gen,
                    "profile": {COND[k][0]: v for k, v in hits.items()},
                }
                payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                try:
                    with st.spinner("Label padh raha hoon..."):
                        text = summarize(g, payload_json)
                except RuntimeError:
                    text = None
                has_profile_hit = any(hits.values())
                if text:
                    (st.warning if has_profile_hit else st.info)(text)
                else:
                    st.info("Summary nahi ban payi, neeche original text dekho.")
                with st.expander("FDA label ka original text (source)"):
                    if gen:
                        st.markdown("**General warnings:**")
                        for s in gen:
                            st.write("- " + s)
                    for k, v in hits.items():
                        if v:
                            st.markdown(f"**{COND[k][0]}:**")
                            for s in v:
                                st.write("- " + s)

    # ----- Saath lene ki savdhani -----
    if len(meds) >= 2:
        st.header("Saath lene ki savdhani")
        for a, b in combinations(meds, 2):
            na, nb = names_of(a), names_of(b)
            if not na or not nb:
                continue
            ga, gb = a.get("generic") or na[0], b.get("generic") or nb[0]
            with st.container(border=True):
                st.subheader(f"{ga} + {gb}")
                ta = label_for(na).get("drug_interactions")
                tb = label_for(nb).get("drug_interactions")
                if not ta and not tb:
                    st.info("FDA label data nahi mila. Pharmacist se zaroor poochho.")
                    continue
                hits = mentions(ta, nb) + mentions(tb, na)
                if hits:
                    snippet = " ".join(hits)
                    hindi = ask(
                        "Neeche FDA label ka text hai. Sirf isi text ke basis par, "
                        "2-3 line me batao ki "
                        f"{ga} aur {gb} saath lene me kya savdhani hai. "
                        "Agar ye text dono dawai ek saath lene ke baare me nahi hai "
                        "(jaise sirf allergy ya kisi bimari ke baare me), toh pehli "
                        "line me saaf likho: 'Ye dono ek saath lene ki baat nahi hai.' "
                        "Agar text me dono dawai ek saath lene (concomitant / "
                        "co-administration) ki baat ho, toh wahi sabse pehle likho. "
                        "Sirf Devanagari (हिंदी) script me likho. "
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
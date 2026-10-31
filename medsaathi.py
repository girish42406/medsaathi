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

# display naam -> (code, English naam, script)
LANGS = {
    "हिंदी": ("hi", "Hindi", "Devanagari"),
    "English": ("en", "English", "Latin"),
    "मराठी": ("mr", "Marathi", "Devanagari"),
    "অসমীয়া (Assamese)": ("as", "Assamese", "Assamese/Bengali"),
    "বাংলা (Bengali)": ("bn", "Bengali", "Bengali"),
    "बर' (Bodo)": ("brx", "Bodo", "Devanagari"),
    "डोगरी (Dogri)": ("doi", "Dogri", "Devanagari"),
    "ગુજરાતી (Gujarati)": ("gu", "Gujarati", "Gujarati"),
    "ಕನ್ನಡ (Kannada)": ("kn", "Kannada", "Kannada"),
    "کٲشُر (Kashmiri)": ("ks", "Kashmiri", "Perso-Arabic"),
    "कोंकणी (Konkani)": ("kok", "Konkani", "Devanagari"),
    "मैथिली (Maithili)": ("mai", "Maithili", "Devanagari"),
    "മലയാളം (Malayalam)": ("ml", "Malayalam", "Malayalam"),
    "ꯃꯤꯇꯩꯂꯣꯟ (Manipuri)": ("mni", "Manipuri (Meitei)", "Meitei Mayek"),
    "नेपाली (Nepali)": ("ne", "Nepali", "Devanagari"),
    "ଓଡ଼ିଆ (Odia)": ("or", "Odia", "Odia"),
    "ਪੰਜਾਬੀ (Punjabi)": ("pa", "Punjabi", "Gurmukhi"),
    "संस्कृतम् (Sanskrit)": ("sa", "Sanskrit", "Devanagari"),
    "ᱥᱟᱱᱛᱟᱲᱤ (Santali)": ("sat", "Santali", "Ol Chiki"),
    "سنڌي (Sindhi)": ("sd", "Sindhi", "Perso-Arabic"),
    "தமிழ் (Tamil)": ("ta", "Tamil", "Tamil"),
    "తెలుగు (Telugu)": ("te", "Telugu", "Telugu"),
    "اردو (Urdu)": ("ur", "Urdu", "Perso-Arabic"),
}

# ---------- UI text ----------
TT = {
    "hi": {
        "profile": "आपकी प्रोफ़ाइल (वैकल्पिक)",
        "profile_note": "ये कहीं सेव नहीं होती, सिर्फ़ इसी सेशन में इस्तेमाल होती है।",
        "age": "उम्र",
        "age_adult": "वयस्क",
        "age_child": "बच्चा (12 से कम)",
        "age_elderly": "बुज़ुर्ग (65+)",
        "cond": "कोई बीमारी?",
        "allergy": "एलर्जी (कॉमा से अलग करें, जैसे aspirin)",
        "caption": "दवा की फोटो डालें, हम बताएंगे ये क्या है और क्या सावधानी रखनी है।",
        "upload": "दवा की फोटो डालें",
        "reading": "पढ़ रहा हूँ...",
        "kaam": "काम",
        "salt": "मूल तत्व",
        "exp_ok": "✅ एक्सपायरी: {e}. अभी ठीक है।",
        "exp_soon": "⚠️ एक्सपायरी: {e}. जल्दी खत्म होगी ({d} दिन बाकी)।",
        "exp_bad": "❌ एक्सपायरी: {e}. ये दवा एक्सपायर हो चुकी है, न खाएं।",
        "exp_unclear": "एक्सपायरी साफ़ नहीं दिखी, स्ट्रिप पर खुद देख लें।",
        "warn_head": "कौन न ले / आपके लिए सावधानी",
        "together_head": "साथ लेने की सावधानी",
        "allergy_msg": "❌ आपने {a} से एलर्जी बताई है। ये दवा उसी तत्व की है, न लें, डॉक्टर से पूछें।",
        "no_label": "FDA लेबल डेटा नहीं मिला। फार्मासिस्ट से ज़रूर पूछें।",
        "src": "FDA लेबल का मूल टेक्स्ट (सोर्स)",
        "general": "सामान्य चेतावनी",
        "summary_fail": "सारांश नहीं बन पाया, नीचे मूल टेक्स्ट देखें।",
        "no_direct": "FDA लेबल में इनका सीधा इंटरैक्शन नहीं मिला। ये गारंटी नहीं है, फार्मासिस्ट से ज़रूर पूछें।",
        "inter_fail": "इंटरैक्शन मिला है, फार्मासिस्ट से पूछें।",
        "disclaimer": "⚠️ ये सिर्फ़ जानकारी के लिए है, डॉक्टर/फार्मासिस्ट की सलाह का विकल्प नहीं। डोज़ और दवा का फ़ैसला हमेशा डॉक्टर से करवाएं।",
        "photo_fail": "ये फोटो पढ़ नहीं पाया, दोबारा कोशिश करें।",
    },
    "en": {
        "profile": "Your profile (optional)",
        "profile_note": "This is not saved anywhere, only used in this session.",
        "age": "Age",
        "age_adult": "Adult",
        "age_child": "Child (under 12)",
        "age_elderly": "Elderly (65+)",
        "cond": "Any health condition?",
        "allergy": "Allergy (comma separated, e.g. aspirin)",
        "caption": "Upload a photo of your medicine and we'll explain what it is and what to watch out for.",
        "upload": "Upload medicine photo(s)",
        "reading": "Reading...",
        "kaam": "Used for",
        "salt": "Active ingredient",
        "exp_ok": "✅ Expiry: {e}. Still fine.",
        "exp_soon": "⚠️ Expiry: {e}. Expires soon ({d} days left).",
        "exp_bad": "❌ Expiry: {e}. This medicine has expired, do not take it.",
        "exp_unclear": "Expiry not clearly visible, please check the strip yourself.",
        "warn_head": "Who should not take it / precautions for you",
        "together_head": "Precautions when taken together",
        "allergy_msg": "❌ You said you are allergic to {a}. This medicine contains it, do not take it, ask a doctor.",
        "no_label": "No FDA label data found. Please ask a pharmacist.",
        "src": "Original FDA label text (source)",
        "general": "General warnings",
        "summary_fail": "Could not make a summary, see the original text below.",
        "no_direct": "No direct interaction found in the FDA labels. This is not a guarantee, please ask a pharmacist.",
        "inter_fail": "An interaction was found, please ask a pharmacist.",
        "disclaimer": "⚠️ For information only, not a substitute for a doctor/pharmacist. Always get dose and medicine decisions from a doctor.",
        "photo_fail": "Could not read this photo, please try again.",
    },
    "mr": {
        "profile": "तुमची प्रोफाइल (ऐच्छिक)",
        "profile_note": "ही कुठेही साठवली जात नाही, फक्त या सत्रात वापरली जाते.",
        "age": "वय",
        "age_adult": "प्रौढ",
        "age_child": "लहान मूल (१२ पेक्षा कमी)",
        "age_elderly": "ज्येष्ठ (६५+)",
        "cond": "काही आजार?",
        "allergy": "अ‍ॅलर्जी (स्वल्पविरामाने वेगळी करा, उदा. aspirin)",
        "caption": "औषधाचा फोटो टाका, हे काय आहे आणि काय काळजी घ्यावी ते आम्ही सांगू.",
        "upload": "औषधाचे फोटो टाका",
        "reading": "वाचत आहे...",
        "kaam": "उपयोग",
        "salt": "मूळ घटक",
        "exp_ok": "✅ मुदत: {e}. अजून ठीक आहे.",
        "exp_soon": "⚠️ मुदत: {e}. लवकरच संपेल ({d} दिवस बाकी).",
        "exp_bad": "❌ मुदत: {e}. हे औषध एक्स्पायर झाले आहे, घेऊ नका.",
        "exp_unclear": "मुदत नीट दिसली नाही, स्ट्रिपवर स्वतः पाहा.",
        "warn_head": "कोणी घेऊ नये / तुमच्यासाठी काळजी",
        "together_head": "एकत्र घेताना काळजी",
        "allergy_msg": "❌ तुम्ही {a} ची अ‍ॅलर्जी सांगितली आहे. हे औषध त्याच घटकाचे आहे, घेऊ नका, डॉक्टरांना विचारा.",
        "no_label": "FDA लेबल डेटा मिळाला नाही. फार्मासिस्टला नक्की विचारा.",
        "src": "FDA लेबलचा मूळ मजकूर (स्रोत)",
        "general": "सर्वसाधारण इशारे",
        "summary_fail": "सारांश तयार झाला नाही, खाली मूळ मजकूर पाहा.",
        "no_direct": "FDA लेबलमध्ये यांचा थेट परस्परसंवाद आढळला नाही. याची हमी नाही, फार्मासिस्टला नक्की विचारा.",
        "inter_fail": "परस्परसंवाद आढळला आहे, फार्मासिस्टला विचारा.",
        "disclaimer": "⚠️ ही फक्त माहिती आहे, डॉक्टर/फार्मासिस्टच्या सल्ल्याला पर्याय नाही. डोस आणि औषधाचा निर्णय नेहमी डॉक्टरांकडून घ्या.",
        "photo_fail": "हा फोटो वाचता आला नाही, पुन्हा प्रयत्न करा.",
    },
}

# sidebar ke condition labels
CLT = {
    "hi": {
        "pregnancy": "गर्भावस्था / दूध पिलाना",
        "kidney": "किडनी की समस्या",
        "liver": "लिवर की समस्या",
        "asthma": "अस्थमा",
        "heart_bp": "BP / दिल की बीमारी",
        "stomach": "पेट का अल्सर / एसिडिटी",
    },
    "en": {
        "pregnancy": "Pregnancy / breastfeeding",
        "kidney": "Kidney problem",
        "liver": "Liver problem",
        "asthma": "Asthma",
        "heart_bp": "BP / heart disease",
        "stomach": "Stomach ulcer / acidity",
    },
    "mr": {
        "pregnancy": "गर्भावस्था / स्तनपान",
        "kidney": "किडनीचा त्रास",
        "liver": "यकृताचा (लिव्हर) त्रास",
        "asthma": "दमा",
        "heart_bp": "बीपी / हृदयरोग",
        "stomach": "पोटातील अल्सर / अ‍ॅसिडिटी",
    },
}

NOWARN = {
    "hi": "लेबल में अलग से चेतावनी नहीं मिली (इसका मतलब ये नहीं कि ये सुरक्षित है, डॉक्टर से पूछें)",
    "en": "No separate warning found in the label (this does not mean it is safe, ask a doctor)",
    "mr": "लेबलमध्ये वेगळा इशारा आढळला नाही (याचा अर्थ हे सुरक्षित आहे असे नाही, डॉक्टरांना विचारा)",
}
NOTTOGETHER = {
    "hi": "ये दोनों एक साथ लेने की बात नहीं है।",
    "en": "This is not about taking the two together.",
    "mr": "ही दोन्ही औषधे एकत्र घेण्याबद्दल नाही.",
}

PROMPT = (
    "Extract the following from this medicine label. Reply with JSON only: "
    '{"brand": "", "generic": "", "names": [], '
    '"use": {"hi": "", "en": "", "mr": ""}, "expiry": ""}. '
    "generic = the most common English name of the active salt. "
    "names = list of all common English names/synonyms of the salt, including the "
    'US name (e.g. ["acetaminophen", "paracetamol"] or '
    '["aspirin", "acetylsalicylic acid"]). '
    "use = what the medicine is used for, in simple words: hi in Devanagari Hindi, "
    "en in English, mr in Devanagari Marathi. "
    "expiry = in MM/YYYY format. "
    "Use null for anything not clearly visible, do not guess."
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

# condition -> (English naam, label me dhundhne ke shabd)
COND = {
    "pregnancy": ("Pregnancy / breastfeeding", ["pregnan", "breast", "nursing", "lactat", "fetal", "fetus"]),
    "kidney": ("Kidney problem", ["renal", "kidney"]),
    "liver": ("Liver problem", ["hepatic", "liver"]),
    "asthma": ("Asthma", ["asthma", "bronchospasm"]),
    "heart_bp": ("BP / heart disease", ["hypertension", "blood pressure", "cardiovascular", "heart failure", "myocardial"]),
    "stomach": ("Stomach ulcer / acidity", ["ulcer", "gastrointestinal", "stomach", "bleeding"]),
    "child": ("Children (under 12)", ["pediatric", "children", "child", "reye"]),
    "elderly": ("Elderly (65+)", ["geriatric", "elderly", "older patients", "older adults"]),
}
SIDEBAR_CONDS = ["pregnancy", "kidney", "liver", "asthma", "heart_bp", "stomach"]


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
    if not isinstance(info, dict):
        raise RuntimeError("photo read failed")
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
def summarize(generic, payload_json, lang_name, script, nowarn, general_head):
    text = ask(
        f"Below are parts of the FDA label for {generic} (JSON). Based ONLY on this "
        "text, make short bullet points. Start with a heading "
        f"'{general_head}' for the general warnings, then one separate heading + "
        "bullets for each condition in 'profile'. "
        f"If a condition has no text, write: '{nowarn}'. "
        "Do not add an introduction, do not add anything of your own, and never "
        f"mention dose. Write ONLY in {lang_name} ({script} script); "
        "drug names may stay in English.\n\n" + payload_json,
        as_json=False,
    )
    if not text:
        raise RuntimeError("summary failed")
    return text


@st.cache_data(show_spinner=False)
def explain_pair(ga, gb, snippet, lang_name, script, nottogether):
    return ask(
        "Below is text from an FDA label. Based ONLY on this text, explain in 2-3 "
        f"short lines what precaution applies when taking {ga} and {gb} together. "
        "If the text mentions taking both together (concomitant / co-administration), "
        "write that first. If the text is not about taking them together (e.g. only "
        f"about allergy or a disease), start with: '{nottogether}'. "
        f"Do not add anything of your own. Write ONLY in {lang_name} "
        f"({script} script); drug names may stay in English.\n\n" + snippet,
        as_json=False,
    )


@st.cache_data(show_spinner=False)
def translate_ui(lang_name, script):
    """English UI text ko kisi bhi bhasha me translate karta hai (ek baar, phir cache)."""
    base = json.dumps(
        {
            "T": TT["en"],
            "CL": CLT["en"],
            "NOWARN": NOWARN["en"],
            "NOTTOGETHER": NOTTOGETHER["en"],
        },
        ensure_ascii=False,
    )
    out = ask(
        f"Translate the VALUES of this JSON into {lang_name} ({script} script). "
        "Keep all keys unchanged. Keep placeholders like {e}, {d}, {a} and emoji "
        "exactly as they are. Keep drug names and abbreviations like FDA and BP as "
        "they are. Use simple everyday words that a common person understands. "
        "Reply with JSON only.\n\n" + base
    )
    if not isinstance(out, dict) or not all(
        k in out for k in ("T", "CL", "NOWARN", "NOTTOGETHER")
    ):
        raise RuntimeError("ui translation failed")
    return out


@st.cache_data(show_spinner=False)
def tr_text(text, lang_name, script):
    out = ask(
        f"Translate this into {lang_name} ({script} script), simple words, "
        "keep drug names as they are. Reply with only the translation:\n" + text,
        as_json=False,
    )
    if not out:
        raise RuntimeError("translation failed")
    return out.strip()


# ---------- Sidebar ----------
lang_label = st.sidebar.selectbox("भाषा / Language", list(LANGS))
code, LANG_NAME, SCRIPT = LANGS[lang_label]

if code in TT:
    T, CL, NW, NT = TT[code], CLT[code], NOWARN[code], NOTTOGETHER[code]
else:
    try:
        with st.sidebar:
            with st.spinner("..."):
                pack = translate_ui(LANG_NAME, SCRIPT)
        T = {**TT["en"], **pack["T"]}
        CL = {**CLT["en"], **pack["CL"]}
        NW, NT = pack["NOWARN"], pack["NOTTOGETHER"]
        st.sidebar.caption(
            "⚠️ Machine-translated. Please verify with a doctor/pharmacist. "
            "FDA source text stays in English."
        )
    except RuntimeError:
        st.sidebar.warning("Translation failed, showing English. Try again.")
        T, CL, NW, NT = TT["en"], CLT["en"], NOWARN["en"], NOTTOGETHER["en"]
        code, LANG_NAME, SCRIPT = "en", "English", "Latin"

if code in ("ur", "ks", "sd"):
    st.markdown(
        "<style>div[data-testid='stMarkdownContainer']{direction:rtl;text-align:right;}</style>",
        unsafe_allow_html=True,
    )

st.sidebar.header(T["profile"])
st.sidebar.caption(T["profile_note"])
age = st.sidebar.radio(
    T["age"],
    ["adult", "child", "elderly"],
    format_func=lambda k: T["age_" + k],
)
selected = st.sidebar.multiselect(
    T["cond"], SIDEBAR_CONDS, format_func=lambda k: CL[k]
)
allergy_txt = st.sidebar.text_input(T["allergy"])

selected = list(selected)
if age == "child":
    selected.append("child")
if age == "elderly":
    selected.append("elderly")
allergies = [a.strip().lower() for a in allergy_txt.split(",") if a.strip()]


def cond_label(k):
    if k == "child":
        return T["age_child"]
    if k == "elderly":
        return T["age_elderly"]
    return CL[k]


def safe_fmt(key, **kw):
    try:
        return T[key].format(**kw)
    except (KeyError, IndexError, ValueError):
        return TT["en"][key].format(**kw)


def show_expiry(exp):
    m = re.search(r"(\d{1,2})\s*/\s*(\d{4})", exp or "")
    if not m or not 1 <= int(m.group(1)) <= 12:
        st.info(T["exp_unclear"])
        return
    month, year = int(m.group(1)), int(m.group(2))
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    days = (last_day - date.today()).days
    if days < 0:
        st.error(safe_fmt("exp_bad", e=exp))
    elif days <= 90:
        st.warning(safe_fmt("exp_soon", e=exp, d=days))
    else:
        st.success(safe_fmt("exp_ok", e=exp))


def med_card(photo, info):
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(photo)
        with c2:
            st.subheader(info.get("brand") or info.get("generic") or "?")
            if info.get("generic"):
                st.caption(f"{T['salt']}: {info['generic']}")
            use = info.get("use")
            if isinstance(use, dict):
                use = use.get(code) or use.get("en")
                if use and code not in TT:
                    try:
                        use = tr_text(use, LANG_NAME, SCRIPT)
                    except RuntimeError:
                        pass
            if use:
                st.write(f"**{T['kaam']}:** {use}")
            show_expiry(info.get("expiry"))


# ---------- Main ----------
st.title("MedSaathi 💊")
st.caption(T["caption"])

photos = st.file_uploader(
    T["upload"],
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if photos:
    meds = []
    for p in photos:
        try:
            with st.spinner(T["reading"]):
                info = read_photo(p.getvalue(), p.type)
        except RuntimeError:
            st.error(T["photo_fail"])
            st.caption(LAST_ERR["msg"])
            continue
        info = {k: (None if v in ("null", "", "None") else v) for k, v in info.items()}
        meds.append(info)
        med_card(p, info)

    # ----- Kaun na le / profile ke hisaab se savdhani -----
    if meds:
        st.header(T["warn_head"])
        for med in meds:
            names = names_of(med)
            if not names:
                continue
            g = med.get("generic") or names[0]
            with st.container(border=True):
                st.subheader(g)
                bad = [a for a in allergies if any(a in n or n in a for n in names)]
                if bad:
                    st.error(safe_fmt("allergy_msg", a=", ".join(bad)))
                label = label_for(names)
                if not label:
                    st.info(T["no_label"])
                    continue
                gen = general_sents(label)
                hits = {k: find_sents(label, COND[k][1]) for k in selected}
                payload = {
                    "general": gen,
                    "profile": {cond_label(k): v for k, v in hits.items()},
                }
                payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
                try:
                    with st.spinner(T["reading"]):
                        text = summarize(g, payload_json, LANG_NAME, SCRIPT, NW, T["warn_head"])
                except RuntimeError:
                    text = None
                has_profile_hit = any(hits.values())
                if text:
                    (st.warning if has_profile_hit else st.info)(text)
                else:
                    st.info(T["summary_fail"])
                with st.expander(T["src"]):
                    if gen:
                        st.markdown(f"**{T['general']}:**")
                        for s in gen:
                            st.write("- " + s)
                    for k, v in hits.items():
                        if v:
                            st.markdown(f"**{cond_label(k)}:**")
                            for s in v:
                                st.write("- " + s)

    # ----- Saath lene ki savdhani -----
    if len(meds) >= 2:
        st.header(T["together_head"])
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
                    st.info(T["no_label"])
                    continue
                hits = mentions(ta, nb) + mentions(tb, na)
                if hits:
                    snippet = " ".join(hits)
                    text = explain_pair(ga, gb, snippet, LANG_NAME, SCRIPT, NT)
                    st.warning(text or T["inter_fail"])
                    with st.expander(T["src"]):
                        st.write(snippet)
                else:
                    st.success(T["no_direct"])

    st.divider()
    st.caption(T["disclaimer"])

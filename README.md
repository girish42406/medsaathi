# 💊 MedSaathi

**Apni dawai ko samjho, apni bhasha mein.**
Upload photos of medicine strips or boxes. MedSaathi reads the label, checks the expiry, shows precautions based on your profile, and checks interactions when you upload two or more medicines. Output is available in 22 Indian languages plus English.

Built for the **Code for a Billion: Bharat Agentic-AI Hackathon 2026** (theme: agentic AI for India's public health). Aim: help ordinary people, especially elderly and rural users, understand their medicines.

**Live app:** https://medsaathi-7amrfu58ehsx9ryrmuj29u.streamlit.app

> ⚠️ **Information only. Not a substitute for a doctor or pharmacist.** MedSaathi never gives a dose and never suggests which medicine to take.

---

## What it does

- **Photo to label.** Upload one or more photos. Gemini vision extracts brand, generic salt, synonyms, use, and expiry.
- **Edit what was read.** If the label was read wrongly, fix brand, salt or expiry in editable boxes. Everything downstream updates.
- **Expiry card.** Green (OK), amber (under 90 days), red (expired).
- **Who should not take it.** Warnings come from the **openFDA drug label API** (boxed warning, contraindications, do-not-use, pregnancy, pediatric, geriatric, and more), filtered by your sidebar profile (age group, pregnancy, kidney, liver, asthma, BP/heart, stomach ulcer, allergy). Gemini only rephrases and translates. The original FDA text is always shown as the source.
- **Allergy alert.** Red alert if your typed allergy matches the salt or its synonyms.
- **Interaction check.** For every pair of uploaded medicines, MedSaathi looks for each drug (and a small list of drug-class terms, such as NSAIDs) in the other's FDA `drug_interactions` text.
- **Ask MedSaathi (agent).** Ask a question in plain words. A Gemini agent decides which tools to call and answers with sources. The "Agent ne kya kiya" box shows every tool call.
- **22 languages.** Hindi, English and Marathi have hand-written UI text. The others are machine-translated by Gemini and cached. Low-resource ones are marked beta. Urdu, Kashmiri and Sindhi use right-to-left layout.

## How the agent works

```
User question + uploaded photos
        │
        ▼
   Gemini (function calling)  ── decides which tool to call ──┐
        │                                                      │
        ▼                                                      ▼
 read_label(photo_no)      check_expiry(MM/YYYY)      fda_lookup(drug, topic)
                                                       check_interaction(a, b)
        │                                                      │
        └──────────── tool results (FDA text only) ◄───────────┘
        │
        ▼
 Short answer with sources + disclaimer
```

Tools: `read_label`, `check_expiry`, `fda_lookup`, `check_interaction` (see `agent.py`).
Medical facts come only from tool results. The model is instructed never to answer a medical fact from memory.

## Safety rules

1. The app **never gives a dose** and **never suggests which medicine to take**.
2. Medical statements come from **FDA label text**, with the source shown. The LLM only rephrases or translates.
3. The disclaimer is always visible.
4. "No warning found" is never worded as "safe". It says: not found, ask a doctor.
5. Your profile is **not stored anywhere**. It lives only in your session.

## Known limitations

- Data is **US FDA labels**, not Indian labels or brands. Matching is by salt name.
- The interaction check finds direct name mentions plus a small hand-made list of drug classes. It can miss real interactions. "No direct interaction found" is **not** a guarantee.
- Photo reading can fail on blurry images. Free Gemini models can be busy or slow.
- Machine-translated languages are **not verified by native speakers**.

## Run it yourself

```bash
git clone https://github.com/girish42406/medsaathi
cd medsaathi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
streamlit run medsaathi.py
```

On Streamlit Community Cloud, put `GEMINI_API_KEY` in **Secrets**. Never put a key in code.

## Files

| File | What it does |
| --- | --- |
| `medsaathi.py` | Streamlit app: UI, photo reading, FDA warnings, interaction check |
| `agent.py` | Gemini function-calling agent and its 4 tools |
| `drug_classes.py` | Small drug to class-term list used only for searching FDA text |
| `requirements.txt` | Python packages |

## License

MIT. See [LICENSE](LICENSE).

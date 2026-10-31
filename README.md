# MedSaathi 💊

Dawai ki photo se jaankari, aapki profile ke hisaab se savdhani, aur do dawaiyan saath lene ka check, simple Hindi me.

**Live demo:** _(deploy ke baad link yahan lagana)_
**Demo video:** _(link yahan lagana)_

## Problem

Bharat me bahut se log, khaaskar buzurg aur chhote shehron/gaon ke log, dawai ki strip dekh ke samajh nahi paate ki wo kya hai, expire to nahi hui, ya kisi doosri dawai ke saath lena safe hai ya nahi. Galat combination ya expired dawai se nuksan ho sakta hai.

## Solution

MedSaathi me user dawai ki photo upload karta hai. App:

1. **Photo padhta hai** (Gemini vision) aur dawai ka naam, salt, kaam aur expiry nikalta hai
2. **Expiry check** karta hai (hara / peela / laal)
3. **Profile ke hisaab se savdhani** deta hai (umar, pregnancy, kidney, liver, asthma, BP, pet ka ulcer, allergy)
4. **Do ya zyada dawaiyan saath lene ka interaction** batata hai
5. Sab kuch **simple Hindi (Devanagari)** me samjhata hai

## Safety ka tareeka (important)

- **Medical faisla AI ke andaze se nahi hota.** Warnings aur interactions **FDA ke official drug label (openFDA)** ke text se aate hain. AI sirf us text ko simple Hindi me samjhata hai.
- Har warning ke saath **original FDA text (source)** dikhta hai, taaki user/doctor khud verify kar sake.
- App **dose kabhi nahi batata** aur **dawai suggest nahi karta**.
- "Label me warning nahi mili" ka matlab "safe hai" nahi hota, ye app saaf likhta hai.
- Profile kahin save nahi hoti, sirf us session me use hoti hai.

## Tech stack

- Python, Streamlit
- Google Gemini API (photo padhna aur Hindi me samjhana)
- openFDA Drug Label API (warnings aur interactions ka data)

## Limitations (imaandari se)

- Data **US FDA labels** ka hai, Bharat ke brand names ya Indian labels ka nahi. Salt ka naam match karke dhundhta hai.
- Interaction check abhi sirf **seedha naam mention** pakadta hai, poori dawai class (jaise "NSAIDs") nahi.
- Photo padhne me galti ho sakti hai (dhundhli photo, chhota text).
- Free-tier AI model kabhi busy ho sakta hai.
- Ye **jaankari ke liye hai, doctor/pharmacist ki salah ka vikalp nahi.**

## Aage ke plan

- Marathi aur doosri bhashayein
- Indian drug database jodna
- Dawai ki class (jaise NSAIDs) ke hisaab se interaction
- Dose reminder aur family alert

## Local me chalana

    git clone https://github.com/girish42406/medsaathi.git
    cd medsaathi
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    export GEMINI_API_KEY=apni_key
    streamlit run medsaathi.py

Gemini API key **aistudio.google.com** se free me mil jaati hai.

## Author

Girish Sharma
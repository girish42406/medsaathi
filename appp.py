import time
import streamlit as st
from google import genai
from google.genai import types, errors

MODELS = ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-3.8-flash"]
client = genai.Client()
PROMPT = (
    "Is dawai ka naam, kis kaam aati hai, aur expiry date "
    "simple Hindi me batao. Agar kuch saaf na dikhe toh "
    "bolo, andaza mat lagao."
)

st.title("MedSaathi 💊")
photo = st.file_uploader("Dawai ki photo daalo", type=["jpg", "jpeg", "png"])

if photo:
    st.image(photo)
    result = None
    errs = []
    with st.spinner("Padh raha hoon..."):
        for model in MODELS:
            try:
                result = client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(
                            data=photo.getvalue(), mime_type=photo.type
                        ),
                        PROMPT,
                    ],
                )
                break
            except errors.APIError as e:
                errs.append(f"{model}: {str(e)[:150]}")
                time.sleep(2)
    if result:
        st.write(result.text)
    else:
        st.error("Abhi sab models busy hain, 1 minute baad dobara try karo.")
        st.write(errs)
"""Chhoti hand-made list: dawai -> class ke naam jo FDA text mein aate hain.
Ye sirf search ke liye hai (kaunse shabd dhundhne hain). Medical claim FDA text se hi aata hai.
"""

CLASS_TERMS = {
    "ibuprofen": ["nsaid", "nonsteroidal"],
    "aspirin": ["nsaid", "nonsteroidal", "salicylate"],
    "naproxen": ["nsaid", "nonsteroidal"],
    "diclofenac": ["nsaid", "nonsteroidal"],
    "ketorolac": ["nsaid", "nonsteroidal"],
    "etoricoxib": ["nsaid", "nonsteroidal", "cox-2"],
    "celecoxib": ["nsaid", "nonsteroidal", "cox-2"],
    "warfarin": ["anticoagulant", "coumarin"],
    "clopidogrel": ["antiplatelet", "platelet"],
    "lisinopril": ["ace inhibitor", "ace-inhibitor"],
    "enalapril": ["ace inhibitor", "ace-inhibitor"],
    "ramipril": ["ace inhibitor", "ace-inhibitor"],
    "losartan": ["angiotensin receptor", "arb"],
    "telmisartan": ["angiotensin receptor", "arb"],
    "furosemide": ["diuretic"],
    "hydrochlorothiazide": ["diuretic", "thiazide"],
    "atenolol": ["beta-blocker", "beta blocker"],
    "metoprolol": ["beta-blocker", "beta blocker"],
    "amlodipine": ["calcium channel"],
}


def class_terms(names):
    """names (list of lowercase naam) -> unki class ke search shabd."""
    out = []
    for n in names:
        out += CLASS_TERMS.get(n.lower(), [])
    return list(dict.fromkeys(out))

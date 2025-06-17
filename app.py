import streamlit as st
import json
import random
import re
import google.generativeai as genai

# ========== CONFIG ==========
API_KEY = "AIzaSyCEhQGSelnU2D7Iib-WTVrFlOwe6vxzV1E"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("models/gemini-2.0-flash")
chat = model.start_chat()

# ========== TXT to JSON ==========
def convert_txt_to_json(txt_string):
    vocab_list = []
    for line in txt_string.strip().split("\n"):
        match = re.match(r"(.+?)\s+\((.+?)\)\s*:\s*(.+)", line.strip())
        if match:
            word = match.group(1).strip()
            word_type = match.group(2).strip()
            meaning = match.group(3).strip()
            vocab_list.append({
                "word": word,
                "type": word_type,
                "meaning": meaning
            })
    return vocab_list

# ========== GEMINI HELPERS ==========
def check_meaning_with_gemini(question, user_answer, correct_answer, word_type, direction):
    if direction == "en-vi":
        explanation_lang = "Tiếng Việt"
        meaning_from = "Tiếng Anh"
        meaning_to = "Tiếng Việt"
    else:
        explanation_lang = "English"
        meaning_from = "Tiếng Việt"
        meaning_to = "English"

    prompt = f"""
You are evaluating a vocabulary translation quiz.

The user is translating **from {meaning_from} to {meaning_to}**.
Word type: {word_type if word_type else 'unknown'}
Question word: '{question}'
User answered: '{user_answer}'
Correct answer should be: '{correct_answer}'

Respond with YES or NO to confirm correctness.
Then always give a short explanation in {explanation_lang}.
"""
    try:
        response = chat.send_message(prompt)
        text = response.text.strip()
        is_correct = text.lower().startswith("yes")
        return is_correct, text
    except Exception as e:
        return False, f"⚠️ Gemini error: {str(e)}"

def generate_example_sentence(word, word_type, meaning):
    prompt = f"Give a short English sentence using the word '{word}' ({word_type if word_type else 'n/a'}) meaning '{meaning}'."
    try:
        response = chat.send_message(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Gemini error during sentence generation: {str(e)}"

# ========== STREAMLIT UI ==========
st.set_page_config(page_title="🧠 Smart Vocab Quiz", layout="centered")
st.title("🧠 Smart Vocabulary Quiz")

uploaded_file = st.file_uploader("📤 Upload your vocab .txt file", type=["txt"])

if uploaded_file and "vocab" not in st.session_state:
    content = uploaded_file.read().decode("utf-8")
    vocab = convert_txt_to_json(content)
    if not vocab:
        st.error("⚠️ Invalid format. Please use: word (type): meaning")
        st.stop()

    st.session_state.vocab = vocab
    random.shuffle(st.session_state.vocab)
    st.session_state.index = 0
    st.session_state.feedback = ""
    st.session_state.sentence = ""
    st.session_state.direction = random.choice(["en-vi", "vi-en"])
    st.session_state.user_input = ""

# ========== Start Quiz ==========
if "vocab" in st.session_state:
    if st.session_state.index >= len(st.session_state.vocab):
        st.success("🎉 You've completed the quiz!")
        if st.button("🔁 Restart"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    q = st.session_state.vocab[st.session_state.index]
    direction = st.session_state.direction

    if direction == "en-vi":
        prompt_question = q["word"]
        correct_answer = q["meaning"]
        st.subheader(f"What is the Vietnamese meaning of: **{q['word']}** ({q['type']})")
    else:
        prompt_question = q["meaning"]
        correct_answer = q["word"]
        st.subheader(f"What is the English meaning of: **{q['meaning']}** ({q['type']})")

    user_input = st.text_input("Your answer:", value=st.session_state.user_input, key=f"input_{st.session_state.index}")

    if st.button("✔️ Submit Answer"):
        is_correct, explanation = check_meaning_with_gemini(prompt_question, user_input, correct_answer, q["type"], direction)
        st.session_state.feedback = f"{'✅ Correct!' if is_correct else f'❌ Incorrect. Correct answer is: {correct_answer}'}\n\n📘 Gemini explains:\n{explanation}"
        st.session_state.user_input = user_input

    if st.session_state.feedback:
        st.markdown(st.session_state.feedback)

        if st.button("✏️ Generate Example Sentence"):
            st.session_state.sentence = generate_example_sentence(q["word"], q["type"], q["meaning"])

        if st.session_state.sentence:
            st.info(st.session_state.sentence)

        if st.button("➡️ Next"):
            st.session_state.index += 1
            st.session_state.feedback = ""
            st.session_state.sentence = ""
            st.session_state.user_input = ""
            st.session_state.direction = random.choice(["en-vi", "vi-en"])
            st.rerun()
else:
    st.info("📄 Please upload a `.txt` file to begin.")

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
def check_meaning_with_gemini(question, user_answer, correct_answer, word_type):
    prompt = f"""
You're checking if a user's vocabulary answer is semantically correct.
Word type: {word_type if word_type else 'unknown'}
Question: What is the meaning of '{question}'?
User answered: '{user_answer}'
Expected: '{correct_answer}'
Respond only YES or NO if it's semantically equivalent. Explain briefly if wrong.
Trả lời bằng tiếng Việt.
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

# ========== STREAMLIT ==========
st.set_page_config(page_title="🧠 Vocab Quiz", layout="centered")
st.title("🧠 Smart Vocabulary Quiz")

uploaded_file = st.file_uploader("📤 Upload .txt or .json file", type=["txt", "json"])

if uploaded_file and "vocab" not in st.session_state:
    content = uploaded_file.read().decode("utf-8")

    if uploaded_file.name.endswith(".txt"):
        vocab = convert_txt_to_json(content)
    else:
        vocab = json.loads(content)

    if not vocab:
        st.error("❌ Invalid file format.")
        st.stop()

    random.shuffle(vocab)
    st.session_state.vocab = vocab
    st.session_state.index = 0
    st.session_state.feedback = ""
    st.session_state.sentence = ""
    st.session_state.direction = random.choice(["en-vi", "vi-en"])

# ========== MAIN QUIZ ==========
if "vocab" in st.session_state:
    if st.session_state.index >= len(st.session_state.vocab):
        st.success("🎉 You've completed the quiz!")
        if st.button("🔁 Restart"):
            del st.session_state.vocab
        st.stop()

    item = st.session_state.vocab[st.session_state.index]
    word, meaning, word_type = item["word"], item["meaning"], item["type"]

    # Chọn chiều hỏi
    direction = st.session_state.direction
    if direction == "en-vi":
        question_text = f"🧠 What is the Vietnamese meaning of: **{word}**"
        prompt_question = word
        correct_answer = meaning
    else:
        question_text = f"🧠 What is the English meaning of: **{meaning}**"
        prompt_question = meaning
        correct_answer = word

    if word_type:
        question_text += f" ({word_type})"

    st.subheader(question_text)

    user_input = st.text_input("Your answer:", key=f"user_input_{st.session_state.index}")

    if st.button("✔️ Submit Answer"):
        is_correct, feedback = check_meaning_with_gemini(
            prompt_question, user_input, correct_answer, word_type
        )
        st.session_state.feedback = (
            "✅ Correct!" if is_correct else f"❌ Incorrect.\n\nCorrect: **{correct_answer}**"
        )
        st.session_state.feedback += f"\n\n📘 Gemini explains:\n{feedback}"

    if st.session_state.feedback:
        st.markdown(st.session_state.feedback)

        if st.button("✏️ Generate Example Sentence"):
            st.session_state.sentence = generate_example_sentence(word, word_type, meaning)

        if st.session_state.sentence:
            st.info(st.session_state.sentence)

        if st.button("➡️ Next"):
            st.session_state.index += 1
            st.session_state.feedback = ""
            st.session_state.sentence = ""
            st.session_state.direction = random.choice(["en-vi", "vi-en"])
            st.rerun()
else:
    st.info("📄 Please upload a `.txt` or `.json` file to begin.")

import streamlit as st
import json
import random
import re
import google.generativeai as genai

# ========== CONFIG & SECURITY WARNING ==========
st.set_page_config(page_title="🧠 Smart Vocab Quiz", layout="centered", initial_sidebar_state="auto")
st.title("🧠 Smart Vocabulary Quiz")

# CẢNH BÁO BẢO MẬT: Không bao giờ hardcode API key vào mã nguồn.
# Sử dụng Streamlit Secrets để bảo mật.
# 1. Tạo file .streamlit/secrets.toml
# 2. Thêm vào file đó:
#    GEMINI_API_KEY = "AIzaSy...your_real_key"
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Cập nhật tên model thành phiên bản mới và ổn định
    model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
except (KeyError, FileNotFoundError):
    st.error("🚨 Lỗi: Vui lòng cấu hình GEMINI_API_KEY trong Streamlit Secrets.")
    st.info("Tạo một thư mục `.streamlit` trong project của bạn, trong đó tạo file `secrets.toml` và thêm `GEMINI_API_KEY = 'your_key_here'` vào đó.")
    st.stop()

# ========== HELPER FUNCTIONS ==========

def convert_txt_to_json(txt_string):
    """Chuyển đổi một chuỗi text có định dạng sang cấu trúc JSON."""
    vocab_list = []
    # Regex được cải thiện để linh hoạt hơn với khoảng trắng
    # "word" (type) : "meaning"
    pattern = re.compile(r'["\']?(.+?)["\']?\s+\((.+?)\)\s*:\s*["\']?(.+?)["\']?$')
    for line in txt_string.strip().split("\n"):
        match = pattern.match(line.strip())
        if match:
            vocab_list.append({
                "word": match.group(1).strip(),
                "type": match.group(2).strip(),
                "meaning": match.group(3).strip()
            })
    return vocab_list

def start_quiz(vocab_data):
    """Khởi tạo hoặc reset trạng thái session để bắt đầu quiz."""
    if not vocab_data:
        st.error("⚠️ Không thể bắt đầu quiz. Không tìm thấy dữ liệu từ vựng.")
        return
    
    random.shuffle(vocab_data)
    st.session_state.vocab = vocab_data
    st.session_state.index = 0
    st.session_state.feedback = ""
    st.session_state.sentence = ""
    st.session_state.direction = random.choice(["en-vi", "vi-en"])
    st.session_state.user_input = ""
    st.rerun()

# ========== GEMINI API FUNCTIONS ==========

def generate_vocab_with_gemini(topic, characteristics):
    """Tạo danh sách từ vựng bằng Gemini theo định dạng yêu cầu."""
    
    # Prompt được thiết kế cực kỳ nghiêm ngặt để đảm bảo định dạng đầu ra
    prompt = f"""
    You are an API that generates vocabulary lists.
    Your task is to create a list of 15-20 vocabulary words based on the user's request.
    You MUST follow this format for EACH line EXACTLY:
    "English Word" (type) : "Vietnamese Meaning"

    Valid types are: n, v, adj, adv, prep, phr, phr. v.

    DO NOT include any headers, footers, explanations, or any text other than the vocabulary list itself.

    ---
    User's Request:
    Topic: {topic}
    Characteristics: {characteristics}
    ---
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"⚠️ Lỗi khi gọi Gemini API: {str(e)}")
        return None

def check_meaning_with_gemini(question, user_answer, correct_answer, word_type, direction):
    """Kiểm tra câu trả lời của người dùng và đưa ra giải thích."""
    explanation_lang = "Tiếng Việt" if direction == "en-vi" else "English"
    meaning_from = "Tiếng Anh" if direction == "en-vi" else "Tiếng Việt"
    meaning_to = "Tiếng Việt" if direction == "en-vi" else "English"

    prompt = f"""
    Evaluate a vocabulary quiz answer.
    The user is translating from {meaning_from} to {meaning_to}.
    - Question word: '{question}'
    - Correct answer: '{correct_answer}'
    - User's answer: '{user_answer}'

    First, on a single line, respond with only "YES" if the user's answer is correct or a reasonable synonym, and "NO" otherwise.
    Then, on a new line, provide a brief, helpful explanation in {explanation_lang}.
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        parts = text.split('\n', 1)
        is_correct = parts[0].strip().upper() == "YES"
        explanation = parts[1].strip() if len(parts) > 1 else "No explanation provided."
        return is_correct, explanation
    except Exception as e:
        return False, f"⚠️ Lỗi khi kiểm tra với Gemini: {str(e)}"

def generate_example_sentence(word, word_type, meaning):
    """Tạo câu ví dụ cho một từ vựng."""
    prompt = f"Write one short, clear English sentence using the word '{word}' ({word_type}) which means '{meaning}' in Vietnamese."
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Lỗi khi tạo câu: {str(e)}"

# ========== STREAMLIT UI & LOGIC ==========

# Nếu quiz đang diễn ra, không hiển thị màn hình bắt đầu
if "vocab" not in st.session_state:
    tab1, tab2 = st.tabs(["✨ Generate with AI", "📤 Upload a File"])

    with tab1:
        st.subheader("Generate a new vocabulary list")
        with st.form("generate_form"):
            topic = st.text_input("Topic", placeholder="e.g., Technology, Environment, Business")
            characteristics = st.text_input("Characteristics", placeholder="e.g., IELTS Band 7.0, Formal, Common Phrasal Verbs")
            submitted = st.form_submit_button("🚀 Generate & Start Quiz")

            if submitted:
                if not topic or not characteristics:
                    st.warning("Please fill in both Topic and Characteristics.")
                else:
                    with st.spinner("🧠 Gemini is thinking... Please wait."):
                        generated_txt = generate_vocab_with_gemini(topic, characteristics)
                    
                    if generated_txt:
                        vocab_data = convert_txt_to_json(generated_txt)
                        if vocab_data:
                            st.success(f"Generated {len(vocab_data)} words! Starting quiz...")
                            start_quiz(vocab_data)
                        else:
                            st.error("Could not parse the generated text. Please try again.")

    with tab2:
        st.subheader("Upload your own vocabulary file")
        uploaded_file = st.file_uploader("Upload a .txt file (format: word (type): meaning)", type=["txt"])
        if uploaded_file:
            content = uploaded_file.read().decode("utf-8")
            vocab_data = convert_txt_to_json(content)
            if vocab_data:
                st.success(f"Loaded {len(vocab_data)} words from your file!")
                if st.button("▶️ Start Quiz with this file"):
                    start_quiz(vocab_data)
            else:
                st.error("⚠️ Invalid format in the uploaded file. Please use: word (type): meaning")
else:
    # ========== QUIZ INTERFACE ==========
    if st.session_state.index >= len(st.session_state.vocab):
        st.success("🎉 You've completed the quiz! Well done!")
        if st.button("🔁 Restart Quiz"):
            # Chỉ reset lại index và các trạng thái liên quan để bắt đầu lại
            start_quiz(st.session_state.vocab)
        if st.button("🏠 Back to Home"):
            # Xóa toàn bộ session state để quay về màn hình chính
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    # Progress bar
    progress = (st.session_state.index + 1) / len(st.session_state.vocab)
    st.progress(progress, text=f"Question {st.session_state.index + 1} of {len(st.session_state.vocab)}")
    
    q = st.session_state.vocab[st.session_state.index]
    direction = st.session_state.direction

    if direction == "en-vi":
        prompt_question = q["word"]
        correct_answer = q["meaning"]
        st.subheader(f"Translate to Vietnamese: **{q['word']}** ({q['type']})")
    else:
        prompt_question = q["meaning"]
        correct_answer = q["word"]
        st.subheader(f"Translate to English: **{q['meaning']}** ({q['type']})")

    with st.form(key=f"answer_form_{st.session_state.index}"):
        user_input = st.text_input("Your answer:", key=f"input_{st.session_state.index}")
        submit_button = st.form_submit_button("✔️ Check Answer")

    if submit_button:
        if not user_input:
            st.warning("Please enter an answer.")
        else:
            with st.spinner("Checking..."):
                is_correct, explanation = check_meaning_with_gemini(prompt_question, user_input, correct_answer, q["type"], direction)
            
            if is_correct:
                st.session_state.feedback = f"✅ Correct! \n\n{explanation}"
            else:
                st.session_state.feedback = f"❌ Incorrect. The correct answer is: **{correct_answer}**\n\n{explanation}"
            
            # Tự động tạo câu ví dụ nếu trả lời đúng
            st.session_state.sentence = generate_example_sentence(q["word"], q["type"], q["meaning"])

    if st.session_state.feedback:
        st.markdown(st.session_state.feedback)
        if st.session_state.sentence:
            st.info(f"**Example:** {st.session_state.sentence}")

        if st.button("➡️ Next Question"):
            st.session_state.index += 1
            st.session_state.feedback = ""
            st.session_state.sentence = ""
            st.session_state.direction = random.choice(["en-vi", "vi-en"])
            st.rerun()
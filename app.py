import streamlit as st
import json
import random
import re
import google.generativeai as genai
from streamlit.components.v1 import html
import logging
from datetime import datetime

# ========== LOGGING CONFIG ==========
def setup_logger():
    """Cấu hình logging cho ứng dụng"""
    log_filename = f"logs/app_{datetime.now().strftime('%Y%m')}.log"
    
    # Tạo thư mục logs nếu chưa tồn tại
    import os
    os.makedirs('logs', exist_ok=True)
    
    # Cấu hình logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Khởi tạo logger
logger = setup_logger()

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

def auto_focus_input():
    """Hàm tạo JavaScript để tự động focus vào input field và xử lý phím Enter"""
    js_code = """
        <script>
            function focusInput() {
                // Tìm tất cả các input field
                var inputs = window.parent.document.getElementsByTagName('input');
                // Focus vào input field cuối cùng (input answer của quiz)
                if (inputs.length > 0) {
                    inputs[inputs.length - 1].focus();
                }
            }

            function focusNextButton() {
                // Tìm nút Next Question
                var buttons = window.parent.document.getElementsByTagName('button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].innerText.includes('Next Question')) {
                        buttons[i].focus();
                        // Thêm event listener cho phím Enter
                        window.parent.document.addEventListener('keydown', function(e) {
                            if (e.key === 'Enter' && document.activeElement === buttons[i]) {
                                buttons[i].click();
                                // Sau khi click, đợi một chút để trang reload và focus lại vào input
                                setTimeout(focusInput, 100);
                            }
                        });
                        break;
                    }
                }
            }

            // Kiểm tra xem có feedback không (đã submit câu trả lời chưa)
            var feedbackElements = window.parent.document.getElementsByClassName('stMarkdown');
            var hasFeedback = false;
            for (var i = 0; i < feedbackElements.length; i++) {
                if (feedbackElements[i].innerText.includes('✅') || feedbackElements[i].innerText.includes('❌')) {
                    hasFeedback = true;
                    break;
                }
            }

            // Nếu có feedback thì focus vào nút Next, không thì focus vào input
            setTimeout(function() {
                if (hasFeedback) {
                    focusNextButton();
                } else {
                    focusInput();
                }
            }, 100);
        </script>
    """
    return html(js_code)

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

def convert_json_to_txt(vocab_list):
    """Chuyển đổi danh sách từ vựng từ JSON sang định dạng text."""
    txt_lines = []
    for item in vocab_list:
        txt_lines.append(f'"{item["word"]}" ({item["type"]}) : "{item["meaning"]}"')
    return "\n".join(txt_lines)

def start_quiz(vocab_data):
    """Khởi tạo hoặc reset trạng thái session để bắt đầu quiz."""
    if not vocab_data:
        logger.warning("Attempted to start quiz with no vocabulary data")
        st.error("⚠️ Không thể bắt đầu quiz. Không tìm thấy dữ liệu từ vựng.")
        return
    
    logger.info(f"Starting new quiz with {len(vocab_data)} words")
    random.shuffle(vocab_data)
    st.session_state.vocab = vocab_data
    st.session_state.index = 0
    st.session_state.feedback = ""
    st.session_state.sentence = ""
    st.session_state.direction = random.choice(["en-vi", "vi-en"])
    st.session_state.user_input = ""
    st.session_state.correct_answers = 0
    st.rerun()

# ========== GEMINI API FUNCTIONS ==========

def generate_vocab_with_gemini(topic, characteristics):
    """Tạo danh sách từ vựng bằng Gemini theo định dạng yêu cầu."""
    logger.info(f"Generating vocabulary list - Topic: {topic}, Characteristics: {characteristics}")
    
    # Prompt được thiết kế cực kỳ nghiêm ngặt để đảm bảo định dạng đầu ra
    prompt = f"""
    You are an API that generates vocabulary lists.
    Your task is to create a list of vocabulary words based on the user's request, default is 15-20 words.
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
    logger.info(f"Checking answer - Question: {question}, User Answer: {user_answer}, Direction: {direction}")
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
                    logger.warning("Form submitted with empty fields")
                    st.warning("Please fill in both Topic and Characteristics.")
                else:
                    logger.info(f"New quiz generation requested - Topic: {topic}, Characteristics: {characteristics}")
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
        final_score = st.session_state.correct_answers
        total_questions = len(st.session_state.vocab)
        score_percentage = (final_score / total_questions) * 100
        logger.info(f"Quiz completed - Final Score: {final_score}/{total_questions} ({score_percentage:.1f}%)")
        
        st.success("🎉 You've completed the quiz! Well done!")
        st.balloons()  # Thêm hiệu ứng bóng bay khi hoàn thành
        
        # Hiển thị điểm số cuối cùng
        st.markdown(f"""
        ### 📊 Your Final Score:
        - **Correct Answers:** {final_score}/{total_questions}
        - **Score:** {score_percentage:.1f}%
        """)
        
        # Đánh giá kết quả
        if score_percentage >= 90:
            st.success("🌟 Excellent! Outstanding performance!")
        elif score_percentage >= 70:
            st.success("👏 Good job! Keep up the good work!")
        elif score_percentage >= 50:
            st.info("💪 Not bad! Keep practicing to improve!")
        else:
            st.warning("📚 More practice needed. Don't give up!")
        
        # Add download button
        vocab_text = convert_json_to_txt(st.session_state.vocab)
        st.download_button(
            label="📥 Download Vocabulary List",
            data=vocab_text,
            file_name="vocabulary_list.txt",
            mime="text/plain"
        )
        
        if st.button("🔁 Restart Quiz"):
            # Chỉ reset lại index và các trạng thái liên quan để bắt đầu lại
            start_quiz(st.session_state.vocab)
        if st.button("🏠 Back to Home"):
            # Xóa toàn bộ session state để quay về màn hình chính
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.stop()

    # Add Back button
    if st.button("🏠 Back to Home", key="back_button"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Progress bar and score display during quiz
    col1, col2 = st.columns([2, 1])
    with col1:
        progress = (st.session_state.index + 1) / len(st.session_state.vocab)
        st.progress(progress, text=f"Question {st.session_state.index + 1} of {len(st.session_state.vocab)}")
    with col2:
        current_score = st.session_state.correct_answers
        total_so_far = st.session_state.index
        if total_so_far > 0:
            current_percentage = (current_score / total_so_far) * 100
            st.markdown(f"**Score:** {current_score}/{total_so_far} ({current_percentage:.1f}%)")
        else:
            st.markdown("**Score:** 0/0 (0%)")
    
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
            logger.warning(f"Empty answer submitted for question {st.session_state.index + 1}")
            st.warning("Please enter an answer.")
        else:
            with st.spinner("Checking..."):
                is_correct, explanation = check_meaning_with_gemini(prompt_question, user_input, correct_answer, q["type"], direction)
            
            if is_correct:
                logger.info(f"Correct answer - Question {st.session_state.index + 1}: {prompt_question}")
                st.session_state.feedback = f"✅ Correct! \n\n{explanation}"
                st.session_state.correct_answers += 1 # Tăng biến đếm số câu đúng
            else:
                logger.info(f"Incorrect answer - Question {st.session_state.index + 1}: {prompt_question}, User Answer: {user_input}, Correct Answer: {correct_answer}")
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
    
    # Auto focus vào input field
    auto_focus_input()
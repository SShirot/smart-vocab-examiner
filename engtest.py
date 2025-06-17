import random
import google.generativeai as genai
import os

# === CONFIG ===
GEMINI_API_KEY = "AIzaSyCEhQGSelnU2D7Iib-WTVrFlOwe6vxzV1E"  # Thay bằng key thật
VOCAB_FILE = "vocab.txt"
# ===============

# Khởi tạo Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="models/gemini-2.0-flash")
chat = model.start_chat(history=[])

def load_vocab(file_path):
    if not os.path.exists(file_path):
        print(f"❌ File '{file_path}' không tồn tại.")
        return []
    vocab_pairs = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if "|" in line:
                eng, vi = line.strip().split("|", 1)
                vocab_pairs.append((eng.strip(), vi.strip()))
    return vocab_pairs

def ask_question(eng_word, vi_word, direction):
    if direction == "en-vi":
        print(f"\n🧠 What is the Vietnamese meaning of: **{eng_word}** ?")
        return vi_word
    else:
        print(f"\n🧠 What is the English meaning of: **{vi_word}** ?")
        return eng_word

def explain_answer(word, correct_answer, direction):
    if direction == "en-vi":
        prompt = f"What is the Vietnamese meaning of '{word}'? Explain briefly for a learner."
    else:
        prompt = f"What is the English meaning of '{word}'? Explain briefly for a learner."
    response = chat.send_message(prompt)
    return response.text.strip()

def quiz_mode(vocab_list):
    score = 0
    total = 0
    while True:
        eng, vi = random.choice(vocab_list)
        direction = random.choice(["en-vi", "vi-en"])
        correct_answer = ask_question(eng, vi, direction)

        user_input = input("Your answer (or 'q' to quit): ").strip()
        if user_input.lower() == "q":
            break

        total += 1
        if user_input.lower() == correct_answer.lower():
            print("✅ Correct!")
            score += 1
        else:
            print(f"❌ Incorrect. The correct answer is: {correct_answer}")

        explanation = explain_answer(eng if direction == "en-vi" else vi, correct_answer, direction)
        print(f"\n📘 Gemini explains:\n{explanation}")
        input("\n🔁 Press Enter to continue...")

    print(f"\n🎉 Quiz finished. Score: {score}/{total}")

if __name__ == "__main__":
    print("📚 Welcome to the Vocabulary Quiz (Gemini)")
    print("📂 Reading vocabulary from:", VOCAB_FILE)
    print("✏️ Type 'q' to quit.\n")

    vocab_data = load_vocab(VOCAB_FILE)
    if vocab_data:
        quiz_mode(vocab_data)
    else:
        print("⚠️ No valid vocabulary found.")

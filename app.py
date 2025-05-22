from flask import Flask, render_template, request, redirect, url_for, session
import time
import os

# Your existing imports...
import spacy
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Load model and constants
nlp = spacy.load("en_core_web_sm")
MISTRAL_API_KEY = "aKFEMuDwJOvtphHDDOrh2qbfRP7jEA1L"
skill_keywords = [...]  # (Keep your existing skill list)
exclude_list = [...]     # (Keep your existing exclude list)

# ⬇ PASTE your existing methods here:
# - extract_skills

# Skill keywords for extraction
skill_keywords = [
    "Python", "Java", "JavaScript", "C++", "SQL", "MongoDB", "PostgreSQL", "Machine Learning",
    "Deep Learning", "Neural Networks", "Data Science", "AI", "Django", "Flask", "React", "React Native", "Node.js",
    "TensorFlow", "PyTorch", "API", "AWS", "Cloud Computing", "DevOps", "Competitive Programming","Data Structures",
    "Algorithms", "Web Development", "Software Development", "Computer Vision", "Natural Language Processing",
    "Data Analysis", "Business Intelligence", "Power BI", "Tableau", "Big Data", "Hadoop", "Spark", "ETL", "CI/CD",
    "Kubernetes", "Docker", "Git", "Linux", "Unix", "Shell Scripting", "Automation", "Agile", "Scrum", "Kanban", 
    "Problem Solving","HTML", "CSS", "Bootstrap", "SASS", "LESS", "jQuery", "Angular", "Vue.js", "TypeScript",
    "Svelte", "Web Design", "UI/UX","REST", "GraphQL", "Microservices", "Serverless", "Blockchain", "Cryptocurrency",
    "Solidity", "Ethereum", "DeFi", "NFT","Cybersecurity", "Ethical Hacking", "Penetration Testing", "OWASP",
    "Firewall", "VPN", "Security Audits", "Compliance", "ISO 27001","Risk Management", "Fraud Detection",
    "Identity & Access Management", "SIEM", "Splunk", "Networking", "TCP/IP", "DNS", "HTTP", "SSL","Wireless Networks",
    "Network Security", "Cisco", "Juniper", "CompTIA", "CCNA", "CCNP", "CCIE", "CEH", "CISSP", "CISM","CISA",
]

# Exclude list
exclude_list = ["AuxPlutes Tech", "EBTS Organization"]

# Extract skills from LinkedIn About section
def extract_skills(about_text):
    extracted_skills = []
    lower_text = about_text.lower()

    for skill in skill_keywords:
        if skill.lower() in lower_text:
            extracted_skills.append(skill)

    doc = nlp(about_text)
    for token in doc.ents:
        if token.label_ in ["ORG", "PRODUCT"]:
            extracted_skills.append(token.text)

    extracted_skills = [skill for skill in extracted_skills if skill not in exclude_list]
    return list(set(extracted_skills))

# Login to LinkedIn with manual input
def login_linkedin(driver):
    email = input("Enter your LinkedIn email: ")
    password = input("Enter your LinkedIn password: ")

    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password + Keys.RETURN)
    time.sleep(10)  # Wait for CAPTCHA/manual check

# Scrape profile and return extracted skills
def scrape_linkedin_profile(linkedin_url):
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    login_linkedin(driver)
    driver.get(linkedin_url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    name_section = soup.find("h1")
    name = name_section.text.strip() if name_section else "No Name Found"

    about_section = soup.find("div", {"class": "display-flex ph5 pv3"})
    about_text = about_section.text.strip() if about_section else "No About section found"

    extracted_skills = extract_skills(about_text)

    print(f"\n🔹 Name: {name}")
    print(f"\n🔹 About Section:\n{about_text}")
    print(f"\n✅ Extracted Skills: {extracted_skills}")

    return extracted_skills

# ============== QUIZ GENERATOR ==============

mistakes_per_skill = {}

def generate_quiz_questions(skills, num_questions=10):
    questions = []
    print("\n⏳ Generating quiz questions...")

    MODEL_NAME = "mistral-large-latest"  
    questions_per_skill = max(1, num_questions // len(skills))

    for skill in skills:
        for _ in range(questions_per_skill):
            if len(questions) >= num_questions:
                break

            prompt_text = (
                f"Generate a hard multiple-choice question on {skill}. make sure not to include any image or code in question or options"
                "Provide a question, 4 answer choices (A, B, C, D), "
                "the correct answer, and a brief explanation.\n\n"
                "Format:\n"
                "Question: <question>\n"
                "A) <option 1>\n"
                "B) <option 2>\n"
                "C) <option 3>\n"
                "D) <option 4>\n"
                "Correct Answer: <correct option>\n"
                "Explanation: <why it's correct>"
            )

            retry_count = 0
            while retry_count < 3:
                try:
                    response = requests.post(
                        "https://api.mistral.ai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
                        json={
                            "model": MODEL_NAME,
                            "messages": [{"role": "user", "content": prompt_text}],
                            "max_tokens": 300
                        },
                        timeout=15
                    )

                    if response.status_code == 200:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"].strip()

                        question = None
                        options = []
                        correct_answer = None
                        explanation = None

                        lines = content.split("\n")
                        for line in lines:
                            line = line.strip()
                            if line.startswith("Question:"):
                                question = line.replace("Question:", "").strip()
                            elif line.startswith(("A)", "B)", "C)", "D)")):
                                options.append(line[3:].strip())
                            elif line.startswith("Correct Answer:"):
                                correct_answer = line.replace("Correct Answer:", "").strip()
                            elif line.startswith("Explanation:"):
                                explanation = line.replace("Explanation:", "").strip()

                        if question and len(options) == 4 and correct_answer and explanation:
                            questions.append({
                                "question": question,
                                "options": options,
                                "correct_answer": correct_answer.split(")")[0].strip(),
                                "explanation": explanation,
                                "skill": skill
                            })
                        break
                    elif response.status_code == 429:
                        time.sleep(5 + retry_count * 5)
                        retry_count += 1
                    else:
                        break

                except requests.exceptions.RequestException:
                    break

            time.sleep(2)

    return questions

def run_quiz(questions):
    global mistakes_per_skill
    score = 0

    print("\n📌 Welcome to the AI-Generated Quiz!\n")

    for i, q in enumerate(questions, 1):
        print(f"\n🔹 Question {i}: {q['question']}")
        print(f"A) {q['options'][0]}")
        print(f"B) {q['options'][1]}")
        print(f"C) {q['options'][2]}")
        print(f"D) {q['options'][3]}")

        user_answer = input("\n👉 Enter your answer (A, B, C, or D): ").strip().upper()

        if user_answer == q["correct_answer"]:
            print("🎉 Correct! ✅")
            score += 1
        else:
            print(f"❌ Incorrect! Correct answer: {q['correct_answer']}")
            mistakes_per_skill[q["skill"]] = mistakes_per_skill.get(q["skill"], 0) + 1

        print(f"💡 Explanation: {q['explanation']}\n")

    print("\n🎯 Quiz Complete!")
    print(f"🏆 Your Score: {score} / {len(questions)}")

    if mistakes_per_skill:
        print("\n📊 Skills You Struggled With:")
        for skill, count in mistakes_per_skill.items():
            print(f"🔸 {skill}: {count} mistakes")

        print("\n📚 Recommended Study Areas:")
        for skill in mistakes_per_skill.keys():
            print(f"✅ Revise more on {skill}")

    else:
        print("\n🎉 No weak areas detected!")

# ============== STUDY MATERIAL GENERATOR ==============

def generate_study_material(weak_skills):
    study_material = {}

    print("\n⏳ Generating study materials for weak topics...\n")

    MODEL_NAME = "mistral-large-latest"  

    for skill in weak_skills:
        prompt_text = (
            f"Provide a detailed study guide for {skill}. "
            "Include key concepts, best practices, and learning resources in 500 words."
        )

        retry_count = 0
        while retry_count < 3:
            try:
                response = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
                    json={
                        "model": MODEL_NAME,
                        "messages": [{"role": "user", "content": prompt_text}],
                        "max_tokens": 500
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    study_material[skill] = content
                    break  

                elif response.status_code == 429:
                    time.sleep(5 + retry_count * 5)
                    retry_count += 1  

                else:
                    break  

            except requests.exceptions.RequestException:
                break  

        time.sleep(2)  

    return study_material

# - login_linkedin
# - scrape_linkedin_profile
# - generate_quiz_questions
# - run_quiz
# - generate_study_material

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session['linkedin_url'] = request.form["linkedin_url"]
        session['email'] = request.form["email"]
        session['password'] = request.form["password"]
        return redirect(url_for("quiz"))
    return render_template("index.html")

@app.route("/quiz")
def quiz():
    linkedin_url = session.get("linkedin_url")
    if not linkedin_url:
        return redirect(url_for("index"))

    # Modify login method to use session email/password instead of input()
    def login_linkedin_session(driver):
        driver.get("https://www.linkedin.com/login")
        time.sleep(3)
        driver.find_element(By.ID, "username").send_keys(session['email'])
        driver.find_element(By.ID, "password").send_keys(session['password'] + Keys.RETURN)
        time.sleep(10)

    # Patch login method to use above version
    global login_linkedin
    login_linkedin = login_linkedin_session

    skills = scrape_linkedin_profile(linkedin_url)
    session["skills"] = skills
    session["questions"] = generate_quiz_questions(skills, 10)
    session["score"] = 0
    session["mistakes"] = {}

    return redirect(url_for("quiz_question", qid=0))

@app.route("/quiz/<int:qid>", methods=["GET", "POST"])
def quiz_question(qid):
    questions = session["questions"]
    if request.method == "POST":
        answer = request.form.get("answer")
        correct = questions[qid]["correct_answer"]
        if answer == correct:
            session["score"] += 1
        else:
            skill = questions[qid]["skill"]
            mistakes = session["mistakes"]
            mistakes[skill] = mistakes.get(skill, 0) + 1
            session["mistakes"] = mistakes
        return redirect(url_for("quiz_question", qid=qid + 1))

    if qid >= len(questions):
        return redirect(url_for("results"))

    return render_template("quiz.html", qid=qid, total=len(questions), q=questions[qid])

@app.route("/results")
def results():
    return render_template("results.html",
                           score=session["score"],
                           total=len(session["questions"]),
                           mistakes=session["mistakes"])

@app.route("/study")
def study():
    weak_skills = list(session["mistakes"].keys())
    study_content = generate_study_material(weak_skills)
    return render_template("study.html", study=study_content)

   
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))  # Render sets PORT env var
    app.run(host='0.0.0.0', port=port)

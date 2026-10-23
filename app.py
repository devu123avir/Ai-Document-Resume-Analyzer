import os
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import fitz
import streamlit as st
from dotenv import load_dotenv
from google import genai
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

st.set_page_config(
    page_title="AI Document & Resume Analyzer",
    page_icon="📄",
    layout="wide",
)

st.title("📄 AI Document & Resume Analyzer")
st.write(
    "Upload a PDF, explore its content, compare a resume with a job "
    "description, and download an analysis report."
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


# --------------------------------------------------
# 2. PDF TEXT EXTRACTION
# --------------------------------------------------

def extract_pdf_text(pdf_bytes):
    """Extract selectable text from a PDF."""
    pages = []

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_document:
        for page_number, page in enumerate(pdf_document, start=1):
            page_text = page.get_text("text").strip()
            if page_text:
                pages.append(f"Page {page_number}:\n{page_text}")

    return "\n\n".join(pages)


def get_gemini_client():
    """Create a Gemini client using the key stored in the local .env file."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY was not found. Add GEMINI_API_KEY=your_key to the .env file."
        )
    return genai.Client(api_key=GEMINI_API_KEY)



    
def readable_api_error(error):
    """Return a useful error message without hiding the original details."""
    message = str(error)
    lowered = message.lower()

    if any(term in lowered for term in (
        "api_key_invalid", 
        "api key not valid",
        "invalid api key",
        "unauthenticated",
        "401",
    )):
        category = "Gemini authentication error"

    elif any(term in lowered for term in (
        "resource_exhausted",
        "quota",
        "rate limit",
        "429",
        "limit exceeded",
    )):
        category = "Gemini quota/rate-limit error"

    elif any(term in lowered for term in (
        "not found",
        "404",
        "unsupported model",
    )):
        category = f"Gemini model error (configured model: {GEMINI_MODEL})"

    elif "permission denied" in lowered or "403" in lowered:
        category = "Gemini permission error"

    else:
        category = f"Gemini request failed ({type(error).__name__})"

    return f"{category}: {message}"



# --------------------------------------------------
# 3. SKILL EXTRACTION
# --------------------------------------------------

SKILLS_LIST = [
    "Python", "Java", "C++", "JavaScript", "SQL", "MySQL", "HTML", "CSS",
    "React", "Node.js", "Django", "Flask", "FastAPI", "Streamlit",
    "Machine Learning", "Deep Learning", "Generative AI",
    "Artificial Intelligence", "Data Analysis", "Pandas", "NumPy",
    "TensorFlow", "PyTorch", "LangChain", "OpenAI API", "REST API",
    "Git", "GitHub", "Docker", "AWS", "Azure", "Google Cloud",
    "Communication", "Problem Solving", "Data Structures", "Algorithms",
    "OOP", "Object-Oriented Programming", "Jupyter", "Linux", "Excel",
    "Power BI", "Tableau", "NLP", "Computer Vision", "RAG", "LLM", "LLMs",
]


def extract_skills(text):
    """Find predefined skill keywords in text."""
    text_lower = text.lower()
    found = []

    # Check longer terms first so related phrases are handled consistently.
    for skill in sorted(SKILLS_LIST, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
        if re.search(pattern, text_lower):
            found.append(skill)

    # Preserve the configured list order while removing duplicate concepts.
    return [skill for skill in SKILLS_LIST if skill in found]


def compare_resume_with_job(resume_text, job_description):
    """Compare recognized resume skills with skills mentioned in a job description."""
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_description)

    resume_set = {skill.lower() for skill in resume_skills}
    matched = [skill for skill in job_skills if skill.lower() in resume_set]
    missing = [skill for skill in job_skills if skill.lower() not in resume_set]

    score = round(len(matched) / len(job_skills) * 100) if job_skills else None

    return {
        "resume_skills": resume_skills,
        "job_skills": job_skills,
        "matched_skills": matched,
        "missing_skills": missing,
        "match_score": score,
    }


# --------------------------------------------------
# 4. AI SUMMARY
# --------------------------------------------------

def generate_summary(document_text):
    """Generate a summary of the uploaded document using Gemini."""
    client = get_gemini_client()
    prompt = (
        "You are a document analysis assistant. Summarize the supplied document clearly. "
        "Identify its purpose, key points, important facts, and conclusions. "
        "Do not invent information. Use headings and concise bullet points where helpful.\n\n"
        f"DOCUMENT CONTENT:\n{document_text[:50000]}"
    )
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    answer = getattr(response, "text", None)
    if not answer or not answer.strip():
        raise RuntimeError("Gemini returned an empty summary. Please try again.")
    return answer.strip()


# --------------------------------------------------
# 5. CHAT WITH PDF
# --------------------------------------------------

def answer_pdf_question(document_text, question, chat_history):
    """Answer a question using the uploaded PDF and recent conversation."""
    client = get_gemini_client()

    history_text = []
    for message in chat_history[-6:]:
        role_label = "User" if message["role"] == "user" else "Assistant"
        history_text.append(f"{role_label}: {message['content']}")

    history_block = "\n".join(history_text) if history_text else "(No previous messages.)"
    prompt = (
        "You are a helpful PDF assistant. Use the supplied document as the primary source. "
        "Do not invent facts. If the answer is not in the document, say that clearly. "
        "Answer clearly and directly.\n\n"
        f"PDF CONTENT:\n{document_text[:30000]}\n\n"
        f"PREVIOUS CONVERSATION:\n{history_block}\n\n"
        f"CURRENT QUESTION:\n{question}"
    )
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    answer = getattr(response, "text", None)
    if not answer or not answer.strip():
        raise RuntimeError("Gemini returned an empty answer. Please try again.")
    return answer.strip()


# --------------------------------------------------
# 6. PDF ANALYSIS REPORT
# --------------------------------------------------

def create_analysis_report(result, resume_filename):
    """Build a downloadable PDF report for the resume comparison."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    story = [
        Paragraph("Resume Analysis Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"<b>Resume file:</b> {escape(resume_filename)}", styles["Normal"]),
        Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            styles["Normal"],
        ),
        Spacer(1, 16),
    ]

    score = result["match_score"]
    score_text = (
        "Not available: no recognized skills in the job description."
        if score is None
        else f"{score}% (keyword-based match estimate)"
    )
    story.append(Paragraph(f"<b>Resume Match Score:</b> {score_text}", styles["Heading2"]))
    story.append(Spacer(1, 12))

    sections = [
        ("Skills Found in Resume", result["resume_skills"]),
        ("Skills Found in Job Description", result["job_skills"]),
        ("Matching Skills", result["matched_skills"]),
        ("Missing Skills", result["missing_skills"]),
    ]

    for heading, items in sections:
        story.append(Paragraph(heading, styles["Heading2"]))
        if items:
            table = Table([[escape(item)] for item in items], colWidths=[6.8 * inch])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("None identified.", styles["Normal"]))
        story.append(Spacer(1, 12))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Note: This report uses predefined keyword matching. It does not measure "
        "hiring probability or replace a complete professional assessment.",
        styles["Italic"],
    ))
    document.build(story)
    return buffer.getvalue()


# --------------------------------------------------
# 7. MAIN PDF UPLOAD AND TEXT EXTRACTION
# --------------------------------------------------

uploaded_file = st.file_uploader(
    "Upload your PDF",
    type=["pdf"],
    key="main_pdf_uploader",
)

extracted_text = ""
if uploaded_file is not None:
    # Reset document-specific output when the uploaded PDF changes.
    current_pdf_signature = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("summary_file_signature") != current_pdf_signature:
        st.session_state.pop("last_summary", None)
        st.session_state["summary_file_signature"] = current_pdf_signature
    try:
        extracted_text = extract_pdf_text(uploaded_file.getvalue())
        if extracted_text.strip():
            st.success("PDF uploaded and text extracted successfully.")
            with st.expander("📄 View extracted PDF text"):
                st.text_area(
                    "Extracted text",
                    value=extracted_text,
                    height=250,
                    key="extracted_pdf_text_preview",
                )
            st.download_button(
                "📥 Download Extracted Text",
                data=extracted_text,
                file_name="extracted_text.txt",
                mime="text/plain",
                key="download_extracted_text",
            )
        else:
            st.warning(
                "No selectable text was found in this PDF. It may be scanned; "
                "OCR support would be needed to read scanned pages."
            )
    except Exception as error:
        st.error(f"Could not read this PDF: {error}")


# --------------------------------------------------
# 8. AI SUMMARY
# --------------------------------------------------

if uploaded_file is not None and extracted_text.strip():
    st.divider()
    st.subheader("🧠 AI Summary & Important Points")

    if st.button("Generate AI Summary", key="generate_summary_button"):
        try:
            with st.spinner("Analyzing the document..."):
                st.session_state["last_summary"] = generate_summary(extracted_text)
            st.success("Summary generated.")
        except Exception as error:
            st.error(readable_api_error(error))

    if st.session_state.get("last_summary"):
        st.markdown(st.session_state["last_summary"])
        st.download_button(
            "📥 Download AI Summary",
            data=st.session_state["last_summary"],
            file_name="ai_summary.txt",
            mime="text/plain",
            key="download_ai_summary",
        )


# --------------------------------------------------
# 9. CHAT WITH PDF
# --------------------------------------------------

if uploaded_file is not None and extracted_text.strip():
    st.divider()
    st.subheader("💬 Chat with your PDF")
    st.caption("Ask questions about this PDF. AI responses use the Gemini API.")

    # Use filename and file size to reset history when the selected file changes.
    file_signature = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("chat_file_signature") != file_signature:
        st.session_state["pdf_chat_history"] = []
        st.session_state["chat_file_signature"] = file_signature

    if "pdf_chat_history" not in st.session_state:
        st.session_state["pdf_chat_history"] = []

    for message in st.session_state["pdf_chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # A form gives the chat a clear submit action and avoids accidental submits.
    with st.form("pdf_chat_form", clear_on_submit=True):
        user_question = st.text_input(
            "Your question",
            placeholder="e.g. What skills are mentioned in this resume?",
            key="pdf_chat_question",
        )
        submitted = st.form_submit_button("Send question")

    if submitted:
        if not user_question.strip():
            st.warning("Please type a question first.")
        else:
            question = user_question.strip()
            previous_history = list(st.session_state["pdf_chat_history"])

            st.session_state["pdf_chat_history"].append({
                "role": "user",
                "content": question,
            })

            try:
                with st.spinner("Analyzing your question..."):
                    answer = answer_pdf_question(
                        extracted_text,
                        question,
                        previous_history,
                    )
                st.session_state["pdf_chat_history"].append({
                    "role": "assistant",
                    "content": answer or "The model returned an empty answer. Please try again.",
                })
            except Exception as error:
                st.session_state["pdf_chat_history"].append({
                    "role": "assistant",
                    "content": f"⚠️ {readable_api_error(error)}",
                })

            st.rerun()

    if st.session_state.get("pdf_chat_history"):
        if st.button("Clear chat history", key="clear_pdf_chat_history"):
            st.session_state["pdf_chat_history"] = []
            st.rerun()


# --------------------------------------------------
# 10. RESUME VS JOB DESCRIPTION ANALYZER
# --------------------------------------------------

st.divider()
st.header("🎯 Resume vs Job Description Analyzer")
st.write(
    "Compare a resume with a job description using basic keyword matching. "
    "This feature does not require AI credits."
)

resume_file = st.file_uploader(
    "Upload your resume PDF",
    type=["pdf"],
    key="resume_comparison_uploader",
)

job_description = st.text_area(
    "Paste the Job Description here",
    height=220,
    placeholder=(
        "Example: We are looking for a Python Developer with Python, SQL, "
        "Git, REST API, and problem-solving skills..."
    ),
    key="job_description_input",
)

if st.button("Analyze Resume", key="analyze_resume_button"):
    if resume_file is None:
        st.warning("Please upload your resume PDF.")
    elif not job_description.strip():
        st.warning("Please paste a job description.")
    else:
        try:
            resume_text = extract_pdf_text(resume_file.getvalue())
            if not resume_text.strip():
                st.error(
                    "No selectable text found in the resume PDF. "
                    "Scanned PDFs need OCR support."
                )
            else:
                result = compare_resume_with_job(resume_text, job_description)
                st.session_state["last_resume_result"] = result
                st.session_state["last_resume_filename"] = resume_file.name
        except Exception as error:
            st.error(f"Resume analysis failed: {error}")

result = st.session_state.get("last_resume_result")

if result is not None:
    st.subheader("📊 Resume Analysis Results")

    if result["match_score"] is None:
        st.info(
            "No recognized skills were found in the Job Description. "
            "Try adding specific technical skills from the supported list."
        )
    else:
        st.metric("Keyword Match Score", f"{result['match_score']}%")
        st.progress(result["match_score"] / 100)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✅ Matching Skills")
        if result["matched_skills"]:
            for skill in result["matched_skills"]:
                st.write(f"- {skill}")
        else:
            st.write("No matching skills found.")

    with col2:
        st.markdown("### ❌ Missing Skills")
        if result["missing_skills"]:
            for skill in result["missing_skills"]:
                st.write(f"- {skill}")
        else:
            st.write("No missing skills from the recognized list.")

    with st.expander("Skills detected in resume"):
        st.write(result["resume_skills"] or "No recognized skills found.")

    with st.expander("Skills detected in job description"):
        st.write(result["job_skills"] or "No recognized skills found.")

    st.divider()
    st.subheader("📥 Downloadable Analysis Report")

    try:
        report_bytes = create_analysis_report(
            result,
            st.session_state.get("last_resume_filename", "resume.pdf"),
        )
        st.download_button(
            "📥 Download Resume Analysis Report (PDF)",
            data=report_bytes,
            file_name="resume_analysis_report.pdf",
            mime="application/pdf",
            key="download_resume_report",
        )
    except Exception as error:
        st.error(f"Could not create the PDF report: {error}")

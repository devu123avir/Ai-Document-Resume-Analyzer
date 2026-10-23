# AI Document & Resume Analyzer

An AI-powered web application built with Python and Streamlit that helps users analyze PDF documents, interact with document content, and compare resumes with job descriptions.

## Features

* **PDF Text Extraction:** Extract text from uploaded PDF documents.
* **AI-Powered Summarization:** Generate concise summaries of document content using Google Gemini.
* **Chat with PDF:** Ask questions about an uploaded document and receive AI-generated answers.
* **Resume vs. Job Description Analysis:** Compare a resume with a job description to identify matching and potentially missing skills or keywords.
* **Downloadable PDF Report:** Download an analysis report for future reference.

## Screenshots

### 1. Application Interface

![Application Interface](screenshots/Screenshot%202026-10-23%20161608%20-%20Copy.png)

### 2. AI-Powered Document Summary

![AI Summary](screenshots/Screenshot%202026-10-23%20161643.png)

### 3. Chat with PDF

![Chat with PDF](screenshots/Screenshot%202026-10-23%20161655.png)

### 4. Resume vs. Job Description Analysis

![Resume Analysis](screenshots/Screenshot%202026-10-23%20161709.png)

### 5. Downloadable PDF Report

![PDF Report](screenshots/Screenshot%202026-10-23%20161742.png)




## Technology Stack

* Python
* Streamlit
* Google Gemini API
* PyMuPDF
* ReportLab
* python-dotenv

## Project Structure

```text
AI-Document-Resume-Analyzer/
├── app.py
├── requirements.txt
├── test_gemini.py
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/devu123avir/Ai-Document-Resume-Analyzer.git
cd Ai-Document-Resume-Analyzer
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Your Gemini API Key

Create a `.env` file in the project root directory and add your own Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

Replace `your_gemini_api_key_here` with your own valid API key. Never publish your actual API key or commit your `.env` file to GitHub.

### 5. Run the Application

```bash
python -m streamlit run app.py
```

Streamlit will provide a local URL where you can open the application in your browser.

## Security

* Keep API keys in your local `.env` file.
* Never commit secrets, credentials, or private configuration files to version control.
* API availability and usage limits depend on your Google AI account and configured model.

## Future Improvements

* Improve resume scoring and skill-gap analysis.
* Add support for more document formats.
* Improve the visual design and user experience.
* Add more detailed downloadable analysis reports.

## Author

**Divyanshu Chaurasia**

GitHub: [devu123avir](https://github.com/devu123avir)

---

*Built as a hands-on project to develop practical skills in Python, AI integration, and application development.*

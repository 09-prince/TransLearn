# 🎓 TransLearn – AI-Powered YouTube Learning Assistant

TransLearn is a FastAPI-based backend that transforms educational YouTube videos into interactive learning content. It generates:

- ✅ Multiple-choice questions (MCQs)
- ✅ Structured notes in PDF
- ✅ Audio summaries via text-to-speech

## 🚀 Features

- 🔍 Extracts and trims YouTube transcripts
- 🧠 Smart text chunking for optimal processing
- 🧾 MCQ generation using Groq + Llama model
- 📄 Auto-formatted notes as PDF
- 🔊 Audio summaries using Google Cloud Text-to-Speech
- ⚡ FastAPI-based API with full CORS support

---

## 📦 Installation

```bash
git clone https://github.com/your-username/translearn.git
cd translearn
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
  



⚙️ Environment Setup
Create a .env file in the root directory:
GROQ_API_KEY="your_groq_api_key"

Place your Google Cloud Text-to-Speech credentials JSON (e.g.
hip-fusion-454512-p9-51166d5109ee.json) in the root folder.

🧪 Run the Backend Server
$ uvicorn main:app --reload




📬 API Endpoints
➤ GET /
Returns a welcome message.

➤ POST /mcq
Generate MCQs from a YouTube video.

Request Body:
{
  "link": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
  "num": 5,
  "diff": "medium"
}

Response:
[
  {
    "question": "...",
    "options": ["A", "B", "C", "D"],
    "answer": "A"
  },
  ...
]

➤ POST /notes
Generate structured notes from video and return as PDF.

Request Body:
{
  "link": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
}
Response: Returns a notes.pdf file for download.

➤ POST /summary-audio
Generate a summarized spoken version of the video as audio.
{
  "link": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
}
Response: Returns an MP3 audio file.




🛠 Project Structure
.
├── main.py                 # FastAPI app with routes
├── back_end.py             # Core logic (MCQ, notes, voice summary)
├── requirements.txt
├── pyproject.toml
├── .env                    # GROQ API Key
├── .gitignore
├── hip-fusion-*.json       # Google TTS credentials


🔧 Dependencies
Key libraries used:

FastAPI, Uvicorn – API backend

LangChain, langchain-groq – LLM orchestration

FPDF – PDF notes generation

youtube-transcript-api – Transcript extraction

google-cloud-texttospeech – Audio summary

python-dotenv, requests – Utility libraries

All dependencies are listed in requirements.txt.




from back_end import main

pipeline = main()

# Generate MCQs
questions = pipeline.Mcq(link="https://youtube.com/...", num=5, diff="easy")

# Generate Notes
pdf_bytes = pipeline.Notes(link="https://youtube.com/...")

# Generate Voice Summary
audio_bytes = pipeline.Voice(link="https://youtube.com/...")




📄 License
MIT License.
You are free to use, modify, and distribute this project with attribution.


✨ Author
Kanishk Khandelwal
🔗 GitHub • 🌐 LinkedIn
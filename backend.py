import os
import io
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
import requests
from dotenv import load_dotenv
from typing import List
from fpdf import FPDF
from typing import List
from google.cloud import texttospeech




load_dotenv()

api_key  = os.getenv("GROQ_API_KEY")


class YouTubeTranscriptFetcher:
    def __init__(self, video_input: str, language: str = "en"):
        self.video_input = video_input
        self.language = language
        self.video_id = self.extract_video_id()

    def extract_video_id(self) -> str:
        video_input = self.video_input
        if "youtube.com" in video_input:
            parsed_url = urlparse(video_input)
            query = parse_qs(parsed_url.query)
            video_id = query.get("v", [None])[0]
        elif "youtu.be" in video_input:
            parsed_url = urlparse(video_input)
            video_id = parsed_url.path.lstrip("/")
        else:
            video_id = video_input

        if not video_id or len(video_id) != 11:
            raise ValueError(f"Invalid YouTube video ID: {video_id}")
        return video_id

    def _trim_edges(self, text: str, n: int = 100) -> str:
        words = text.split()
        if len(words) <= 2 * n:
            return "Transcript too short to trim."
        return " ".join(words[n:-n])

    def get_transcript(self, trim_words: int = 100) -> str:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(self.video_id, languages=[self.language])
            full_text = " ".join(chunk["text"] for chunk in transcript_list)
            return self._trim_edges(full_text, trim_words)
        except TranscriptsDisabled:
            return "Transcripts are disabled for this video."
        except NoTranscriptFound:
            return "No transcript found for this video."
        except Exception as e:
            return f"An error occurred: {str(e)}"


def estimate_tokens(text: str) -> int:
    # Rough estimate: 1 token ≈ 4 characters (English)
    return int(len(text) / 4)

def trim_text_by_char_length(text: str, max_tokens: int = 5900) -> str:
    est_tokens = estimate_tokens(text)
    if est_tokens <= max_tokens:
        return text
    allowed_chars = max_tokens * 4
    return text[:allowed_chars]



class SmartTextChunker:
    def __init__(self, text: str):
        self.text = text
        self.length = len(text)

    def decide_num_chunks(self) -> int:
        if self.length < 1000:
            return 5
        elif self.length < 2000:
            return 6
        elif self.length < 4000:
            return 7
        elif self.length < 8000:
            return 8
        else:
            return 9

    def chunk(self) -> list[list[str]]:
        num_chunks = self.decide_num_chunks()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )

        docs = splitter.create_documents([self.text])
        total = len(docs)
        chunk_size = total // num_chunks + (total % num_chunks > 0)

        chunks = []
        for i in range(0, total, chunk_size):
            group = [doc.page_content for doc in docs[i:i + chunk_size]]
            chunks.append([" ".join(group)])

        while len(chunks) < num_chunks:
            chunks.append([""])

        return chunks



class MCQGenerator:
    def __init__(self, model_name="llama-3.1-8b-instant"):
        self.model = ChatGroq(model=model_name, api_key=api_key)
        self.parser = JsonOutputParser()

        self.prompt_template = PromptTemplate(
            template="""
You are a helpful assistant.

Generate {num} multiple-choice questions from the given text.
Difficulty Level => {diff}
Answer the following in strict JSON only — no explanations, no markdown.

Each question must include:
- "question": a clear question
- "options": a list of 4 options
- "answer": the correct option (text only, not the letter)

Respond ONLY in valid JSON list format like:

[
  {{
    "question": "What is the capital of France?",
    "options": ["Paris", "London", "Berlin", "Rome"],
    "answer": "Paris"
  }},
  ...
]

Text:
\"\"\"{text}\"\"\"
""",
            input_variables=["text", "num", "diff"]
        )

    def generate_mcqs(self, text_chunks: list[str], total_questions: int, diff: str) -> list[dict]:
        questions_per_chunk = total_questions // len(text_chunks)
        all_questions = []

        chain = self.prompt_template | self.model | self.parser

        for chunk in text_chunks:
            mcqs = chain.invoke({
                "text": chunk,
                "num": questions_per_chunk,
                "diff": diff
            })
            all_questions.extend(mcqs)

        # Handle extra questions if needed
        extra = total_questions - len(all_questions)
        if extra > 0:
            extra_mcqs = chain.invoke({
                "text": text_chunks[0],
                "num": extra,
                "diff": diff 
            })
            all_questions.extend(extra_mcqs)

        return all_questions


class SummaryPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("Helvetica", "", 12)  # Use Unicode-safe font

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, title, ln=True, align="C")
        self.ln(5)

    def section_heading(self, heading):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, heading, ln=True)
        self.ln(2)

    def body_text(self, text):
        self.set_font("Helvetica", "", 12)
        self.multi_cell(0, 8, text)
        self.ln()

    def bullet_list(self, items):
        self.set_font("Helvetica", "", 12)
        for item in items:
            self.cell(5)
            self.cell(0, 8, f"- {item}", ln=True)
        self.ln()

    def numbered_list(self, items):
        self.set_font("Helvetica", "", 12)
        for idx, item in enumerate(items, 1):
            self.cell(5)
            self.cell(0, 8, f"{idx}. {item}", ln=True)
        self.ln()


class NotesGenerator:
    def __init__(self, chunks: List[List[str]], model_name: str = "llama3-70b-8192"):
        self.chunks = chunks
        self.llm = ChatGroq(model=model_name, api_key=api_key)
        self.parser = StrOutputParser()

    def summarize_chunk(self, text: str) -> str:
        prompt = PromptTemplate(
            template="""
Summarize the following content into 3–4 informative sentences capturing the core points.

Text:
\"\"\"{context}\"\"\"
""",
            input_variables=["context"]
        )
        chain = prompt | self.llm | self.parser
        return chain.invoke({"context": text}).strip()

    def generate_final_notes(self, summary_text: str) -> str:
        prompt = PromptTemplate(
            template="""
Generate a well-formatted article in plain text format using the following structure. Do not use markdown or special characters:
— no explanations, no markdown and no symbol like "₹".
1. Title: [Your Title Here]
2. Section headings ending with a colon (e.g., Introduction:)
3. Include 1–2 short paragraphs (2–4 sentences each) per section
4. Add a bullet list using '- ' (e.g., - Benefit A)
5. Add a numbered list using '1.', '2.', etc.
6. End with a Conclusion: section
7. End the file with: - End of Document -

{context}
""",
            input_variables=["context"]
        )
        chain = prompt | self.llm | self.parser
        return chain.invoke({"context": summary_text}).strip()

    def generate_notes(self) -> str:
        # Step 1: Flatten and summarize each chunk
        mini_summaries = []
        for sublist in self.chunks:
            chunk_text = " ".join(sublist).strip()
            if chunk_text:
                summary = self.summarize_chunk(chunk_text)
                mini_summaries.append(summary)

        # Step 2: Merge and summarize again
        merged_summary = "\n".join(mini_summaries)
        safe_text = trim_text_by_char_length(merged_summary, 5900)
        final_notes = self.generate_final_notes(safe_text)
        return final_notes

    def save_to_pdf(self, summary: str) -> bytes:
        content = summary.splitlines()
        pdf = SummaryPDF()
        pdf.add_page()

        mode = None
        bullet_items = []
        numbered_items = []

        for line in content:
            line = line.strip()
            if line.startswith("Title:"):
                pdf.chapter_title(line.replace("Title:", "").strip())
            elif line.endswith(":"):
                pdf.section_heading(line)
            elif line.startswith("- "):
                if mode != "bullet":
                    if numbered_items:
                        pdf.numbered_list(numbered_items)
                        numbered_items = []
                    mode = "bullet"
                bullet_items.append(line[2:])
            elif line[:2].isdigit() and line[2] == '.':
                if mode != "numbered":
                    if bullet_items:
                        pdf.bullet_list(bullet_items)
                        bullet_items = []
                    mode = "numbered"
                numbered_items.append(line[3:].strip())
            elif not line:
                if mode == "bullet":
                    pdf.bullet_list(bullet_items)
                    bullet_items = []
                elif mode == "numbered":
                    pdf.numbered_list(numbered_items)
                    numbered_items = []
                mode = None
            else:
                if mode == "bullet":
                    pdf.bullet_list(bullet_items)
                    bullet_items = []
                elif mode == "numbered":
                    pdf.numbered_list(numbered_items)
                    numbered_items = []
                mode = None
                pdf.body_text(line)

        if bullet_items:
            pdf.bullet_list(bullet_items)
        if numbered_items:
            pdf.numbered_list(numbered_items)

        buffer = io.BytesIO()
        pdf.output(name=buffer, dest='F')  
        buffer.seek(0)
        return buffer.read()

class VoiceSummaryGenerator:
    def __init__(self, model_name: str = "llama-3.1-8b-instant", credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "gcloud-key.json")):
        # LLM model for summarization
        self.model = ChatGroq(model=model_name, api_key=api_key)
        self.parser = StrOutputParser()

        # Google Cloud TTS client
        self.client = texttospeech.TextToSpeechClient.from_service_account_json(credentials_path)
        self.language_code = "en-US"
        self.voice_name = "en-US-Wavenet-D"
        self.ssml_gender = texttospeech.SsmlVoiceGender.MALE
        self.audio_encoding = texttospeech.AudioEncoding.MP3

        # Prompt to summarize chunks

        self.chunk_prompt = PromptTemplate(
                    template="""Summarize the following content chunk into 2–3 sentences suitable for audio:\n\n\"\"\"{text}\"\"\"""",
                    input_variables=["text"]
                )

        self.final_prompt = PromptTemplate(
                    template="""
        You are an educational assistant.

        Summarize the following content into a spoken script that:
        - Is suitable for listening as audio
        - Covers all important points
        - Uses simple and clear language
        - Start from the explination only do not talk about the error and other think use are only used to get only the topic provided
        - Lasts no longer than 3 minutes when spoken aloud (~350–400 words)

        Write it as if someone is narrating naturally.

        Text:
        \"\"\"{text}\"\"\"
        """,
                    input_variables=["text"]
                )



    def generate_script(self, chunks: List[List[str]]) -> str:
        """
        Step 1: Summarize each chunk briefly.
        Step 2: Merge those and create a 3-minute script.
        """
        flat_chunks = [item for sublist in chunks for item in sublist]
        summaries = []

        for chunk in flat_chunks:
            try:
                chain = self.chunk_prompt | self.model | self.parser
                mini_summary = chain.invoke({"text": chunk.strip()})
                summaries.append(mini_summary.strip())
            except Exception as e:
                print(f"❌ Failed to summarize chunk: {e}")

        merged_summary = "\n".join(summaries)
        safe_text = merged_summary[:5900]  # Basic char trimming, replace with tokenizer if needed

        try:
            final_chain = self.final_prompt | self.model | self.parser
            final_script = final_chain.invoke({"text": safe_text})
            return final_script.strip()
        except Exception as e:
            print(f"❌ Failed to generate final script: {e}")
            return ""

    def synthesize_voice(self, text: str, output_path: str = "output_audio.mp3") -> bool:
        """
        Converts text into speech using Google TTS API and saves it as an MP3.
        """
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name,
                ssml_gender=self.ssml_gender
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.audio_encoding
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            with open(output_path, "wb") as out:
                out.write(response.audio_content)

            print(f"✅ Audio saved to: {output_path}")
            return True

        except Exception as e:
            print(f"❌ Google TTS failed: {e}")
            return False
        
    def synthesize_voice_to_bytes(self, text: str) -> bytes:
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=self.language_code,
            name=self.voice_name,
            ssml_gender=self.ssml_gender
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=self.audio_encoding
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        return response.audio_content  # return audio as bytes



class main:
    def __init__(self):
        pass

    def Chunk(self, link: str):
        transcript = YouTubeTranscriptFetcher(link)
        clean_transcript = transcript.get_transcript()
        chunk_maker = SmartTextChunker(clean_transcript)
        chunk = chunk_maker.chunk()
        return chunk

    def Mcq(self, link: str, num: int, diff: str):
        chunk = self.Chunk(link)
        mcq = MCQGenerator()
        questions = mcq.generate_mcqs(chunk, num, diff)
        return questions[:num]
    
    def Notes(self, link: str, model_name: str = None) -> bytes:
        chunk = self.Chunk(link)
        generator = NotesGenerator(chunk)
        summary = generator.generate_notes()
        pdf_bytes = generator.save_to_pdf(summary)
        return pdf_bytes


    def Voice(self, link: str):
        chunk = self.Chunk(link)
        generator = VoiceSummaryGenerator()
        script = generator.generate_script(chunk)

        if script:
            return generator.synthesize_voice_to_bytes(script)  # <-- new method
        else:
            raise Exception("Summary script generation failed.")


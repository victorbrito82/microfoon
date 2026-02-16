import json
import time
import re
import google.generativeai as genai
from rich.console import Console

from microfoon.config import GEMINI_API_KEY, PROMPT_CLEANUP, PROMPT_TITLE

console = Console()

class GeminiProcessor:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
        genai.configure(api_key=GEMINI_API_KEY)
        # using flash for speed and cost, supports audio input
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def process_audio(self, audio_path, retry=True):
        """
        Uploads audio to Gemini and requests transcription, summary, and title in JSON format.
        Retries once on failure if retry=True.
        """
        max_attempts = 2 if retry else 1
        
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                console.log(f"[yellow]Retrying ({attempt}/{max_attempts})...[/yellow]")
                time.sleep(3)  # Brief delay before retry
            
            console.log(f"Uploading {audio_path} to Gemini... (attempt {attempt}/{max_attempts})")
            try:
                audio_file = genai.upload_file(path=audio_path)
                
                # Wait for processing state to be ACTIVE
                while audio_file.state.name == "PROCESSING":
                    time.sleep(2)
                    audio_file = genai.get_file(audio_file.name)

                if audio_file.state.name == "FAILED":
                    raise Exception("Audio file processing failed by Gemini.")

                console.log("Audio uploaded. Generating content...")
                
                prompt = f"""
                Please process the attached audio file.
                
                STEP 1: Transcribe the audio verbatim. Detect the language (English or Dutch) automatically based on the spoken words.
                
                STEP 2: Execute the following tasks STRICTLY in the detected language from Step 1.
                - {PROMPT_CLEANUP}
                - {PROMPT_TITLE}

                If the audio is short or ambiguous, prefer Dutch if there is any doubt.

                Output the result strictly in JSON format with the following keys:
                - "transcript": The full transcription text.
                - "cleanup": The cleaned up text.
                - "title": The generated title.
                - "language": The detected language code (e.g., "en", "nl").
                """

                response = self.model.generate_content(
                    [audio_file, prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Cleanup remote file
                try:
                    genai.delete_file(audio_file.name)
                except:
                    pass

                try:
                    result = json.loads(response.text)
                except json.JSONDecodeError:
                    # Gemini may occasionally return raw control chars inside JSON strings.
                    # Strip those chars and retry parsing once.
                    cleaned_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", response.text)
                    result = json.loads(cleaned_text)
                if attempt > 1:
                    console.log(f"[bold green]Retry successful![/bold green]")
                return result

            except Exception as e:
                console.log(f"[bold red]Gemini processing failed (attempt {attempt}/{max_attempts}):[/bold red] {e}")
                if attempt == max_attempts:
                    console.log(f"[bold red]All retry attempts exhausted.[/bold red]")
                    return None
        
        return None

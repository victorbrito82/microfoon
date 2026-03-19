import json
import time
import re
from google import genai
from rich.console import Console

from microfoon.config import GEMINI_API_KEY, PROMPT_CLEANUP, PROMPT_TITLE

console = Console()

class GeminiProcessor:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment variables.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        # using flash for speed and cost, supports audio input
        self.model_name = "gemini-2.0-flash"

    def process_audio(self, audio_path, retry=True):
        """
        Uploads audio to Gemini and requests transcription, summary, and title in JSON format.
        Retries on failure if retry=True with exponential backoff to handle rate limits (429).
        """
        max_attempts = 5 if retry else 1
        base_retry_delay = 15
        
        audio_file = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                delay = base_retry_delay * (2 ** (attempt - 2))
                console.log(f"[yellow]Retrying ({attempt}/{max_attempts}) after {delay} seconds...[/yellow]")
                time.sleep(delay)
            
            console.log(f"Preparing {audio_path} for Gemini... (attempt {attempt}/{max_attempts})")
            try:
                if audio_file is None:
                    audio_file = self.client.files.upload(file=str(audio_path))
                
                # Wait for processing state to be ACTIVE
                while audio_file.state.name == "PROCESSING":
                    time.sleep(10)
                    audio_file = self.client.files.get(name=audio_file.name)

                if audio_file.state.name == "FAILED":
                    raise Exception("Audio file processing failed by Gemini.")

                console.log("Audio ready. Generating content...")
                
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

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[audio_file, prompt],
                    config={"response_mime_type": "application/json"}
                )
                
                # Cleanup remote file
                try:
                    self.client.files.delete(name=audio_file.name)
                except:
                    pass
                audio_file = None

                try:
                    result = json.loads(response.text)
                except json.JSONDecodeError:
                    # Gemini may occasionally return raw control chars inside JSON strings.
                    # Strip those chars and retry parsing once.
                    cleaned_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", response.text)
                    result = json.loads(cleaned_text)
                if attempt > 1:
                    console.log(f"[bold green]Retry successful![/bold green]")
                return result

            except Exception as e:
                if attempt == max_attempts:
                    console.log(f"[bold red]Gemini processing failed (attempt {attempt}/{max_attempts}):[/bold red] {e}")
                    console.log(f"[bold red]All retry attempts exhausted.[/bold red]")
                    if audio_file is not None:
                        try:
                            self.client.files.delete(name=audio_file.name)
                        except:
                            pass
                    return None
                else:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        console.log(f"[yellow]API limit reached (429). Will retry...[/yellow]")
                    else:
                        console.log(f"[yellow]Gemini processing failed: {e}. Will retry...[/yellow]")
        
        return None
    def process_transcript(self, transcript, retry=True):
        """
        Uses an existing transcript to generate a summary and title.
        Avoids audio upload and re-transcription.
        """
        max_attempts = 5 if retry else 1
        base_retry_delay = 15
        
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                delay = base_retry_delay * (2 ** (attempt - 2))
                console.log(f"[yellow]Retrying ({attempt}/{max_attempts}) after {delay} seconds...[/yellow]")
                time.sleep(delay)
            
            console.log(f"Reprocessing transcript with Gemini... (attempt {attempt}/{max_attempts})")
            try:
                prompt = f"""
                Please process the following transcript.
                
                Execute these tasks:
                - {PROMPT_CLEANUP}
                - {PROMPT_TITLE}

                Output the result strictly in JSON format with the following keys:
                - "cleanup": The cleaned up text.
                - "title": The generated title.
                
                Transcript:
                {transcript}
                """

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                
                try:
                    result = json.loads(response.text)
                except json.JSONDecodeError:
                    cleaned_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", response.text)
                    result = json.loads(cleaned_text)
                
                if attempt > 1:
                    console.log(f"[bold green]Retry successful![/bold green]")
                return result

            except Exception as e:
                if attempt == max_attempts:
                    console.log(f"[bold red]Gemini processing failed (attempt {attempt}/{max_attempts}):[/bold red] {e}")
                    console.log(f"[bold red]All retry attempts exhausted.[/bold red]")
                    return None
                else:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        console.log(f"[yellow]API limit reached (429). Will retry...[/yellow]")
                    else:
                        console.log(f"[yellow]Gemini processing failed: {e}. Will retry...[/yellow]")
        
        return None

    def transcribe_audio_only(self, audio_path, retry=True):
        """
        Uploads an audio chunk and requests ONLY the verbatim transcription.
        """
        max_attempts = 5 if retry else 1
        base_retry_delay = 15
        
        audio_file = None
        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                delay = base_retry_delay * (2 ** (attempt - 2))
                console.log(f"[yellow]Retrying transcription ({attempt}/{max_attempts}) after {delay} seconds...[/yellow]")
                time.sleep(delay)
            
            console.log(f"Preparing {audio_path} for Gemini... (attempt {attempt}/{max_attempts})")
            try:
                if audio_file is None:
                    audio_file = self.client.files.upload(file=str(audio_path))
                
                while audio_file.state.name == "PROCESSING":
                    time.sleep(10)
                    audio_file = self.client.files.get(name=audio_file.name)

                if audio_file.state.name == "FAILED":
                    raise Exception("Audio file processing failed by Gemini.")

                console.log("Audio ready. Generating transcription...")
                
                prompt = """
                Please transcribe the attached audio file verbatim. Detect the language (English or Dutch) automatically based on the spoken words.
                Output the result strictly in JSON format with a single key 'transcript' containing the full text.
                """

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[audio_file, prompt],
                    config={"response_mime_type": "application/json"}
                )
                
                try:
                    self.client.files.delete(name=audio_file.name)
                except:
                    pass
                audio_file = None

                try:
                    result = json.loads(response.text)
                except json.JSONDecodeError:
                    cleaned_text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", response.text)
                    result = json.loads(cleaned_text)
                
                if attempt > 1:
                    console.log(f"[bold green]Retry successful![/bold green]")
                return result.get("transcript", "")

            except Exception as e:
                if attempt == max_attempts:
                    console.log(f"[bold red]Gemini transcription failed (attempt {attempt}/{max_attempts}):[/bold red] {e}")
                    console.log(f"[bold red]All retry attempts exhausted.[/bold red]")
                    if audio_file is not None:
                        try:
                            self.client.files.delete(name=audio_file.name)
                        except:
                            pass
                    return None
                else:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        console.log(f"[yellow]API limit reached (429). Will retry...[/yellow]")
                    else:
                        console.log(f"[yellow]Gemini processing failed: {e}. Will retry...[/yellow]")
        
        return None

    def process_large_audio(self, chunk_paths, retry=True):
        """Processes multiple audio chunks, combines transcripts, then summarizes."""
        full_transcript_parts = []
        for i, chunk in enumerate(chunk_paths, 1):
            console.log(f"\n[cyan]Transcribing chunk {i}/{len(chunk_paths)}:[/cyan] {chunk.name}")
            transcript = self.transcribe_audio_only(chunk, retry)
            if transcript:
                full_transcript_parts.append(transcript)
            else:
                raise Exception(f"Failed to transcribe chunk {i}")

        combined_transcript = "\n\n".join(full_transcript_parts)
        console.log(f"\n[bold green]Successfully combined {len(chunk_paths)} chunks.[/bold green] Generating final summary...")
        
        result = self.process_transcript(combined_transcript, retry)
        if result:
            result["transcript"] = combined_transcript
            return result
        return None

# tts.py — Reads every .txt file from the tts_ready_scripts folder and converts
# each one to a .wav audio file using the pyttsx3 text-to-speech engine.
#
# pyttsx3 works entirely offline — no internet or API key required.
# It uses the speech voices installed on your operating system.

import pyttsx3          # Offline text-to-speech engine; wraps the OS's built-in TTS voices
from pathlib import Path  # Cross-platform way to work with file and folder paths

# --- Settings ---
# Path(__file__).parent gives the folder this script is saved in.
# We then navigate relative to that so the script works regardless of where you run it from.
BASE_DIR = Path(__file__).parent

# Folder containing the cleaned .txt files produced by tts_cleaner.py
INPUT_DIR = BASE_DIR.parent / "tts_ready_scripts"

# Folder where the generated .wav audio files will be saved
OUTPUT_DIR = BASE_DIR.parent / "tts_audio"

# The voice ID to use for narration.
# This is an Apple macOS voice (Daniel, British English).
# To list all available voices on your machine, run:
#   import pyttsx3; e = pyttsx3.init(); print([v.id for v in e.getProperty('voices')])
VOICE_ID = "com.apple.speech.synthesis.voice.Daniel"

# Speaking rate in words per minute (default is ~200; 175 is slightly slower and clearer)
RATE = 175

# Volume level: 0.0 (silent) to 1.0 (maximum)
VOLUME = 1.0


def main():
    """
    Initialises the TTS engine, then iterates over every .txt file in INPUT_DIR,
    queuing each one for audio synthesis. All files are processed in a single
    engine.runAndWait() call, which is more efficient than running the engine once per file.
    """

    # Initialise the pyttsx3 engine — this connects to the OS's TTS subsystem
    engine = pyttsx3.init()

    # Apply the voice, rate, and volume settings defined above
    engine.setProperty('voice',  VOICE_ID)
    engine.setProperty('rate',   RATE)
    engine.setProperty('volume', VOLUME)

    # Create the output folder if it doesn't already exist.
    # parents=True creates any missing parent directories too.
    # exist_ok=True means no error is raised if the folder already exists.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Find all .txt files in the input folder, sorted alphabetically for consistent ordering
    txt_files = sorted(INPUT_DIR.glob("*.txt"))

    # Print the resolved absolute path so we can easily verify the script is looking in the right place
    print(f"Looking in: {INPUT_DIR.resolve()}")

    # Guard clause: nothing to do if there are no .txt files in the input folder
    if not txt_files:
        print("No .txt files found.")
        return

    for txt_file in txt_files:

        # Open and read the full contents of the .txt file
        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read().strip()

        # Skip files that are empty after stripping whitespace
        if not text:
            print(f"Skipping empty file: {txt_file.name}")
            continue

        # Build the output .wav path — same filename as the .txt but in OUTPUT_DIR with a .wav extension
        output_file = OUTPUT_DIR / (txt_file.stem + ".wav")

        # Queue this file for synthesis. save_to_file() does not process immediately —
        # it adds the job to a queue. All queued jobs run when engine.runAndWait() is called below.
        engine.save_to_file(text, str(output_file))
        print(f"Queued: {output_file.name}")

    # Process all queued synthesis jobs. This blocks until every file has been written to disk.
    engine.runAndWait()

    print("All files processed.")


# This block only runs when the file is executed directly (e.g. "python tts.py").
# If this file is imported by another script, this block is skipped entirely.
if __name__ == "__main__":
    main()

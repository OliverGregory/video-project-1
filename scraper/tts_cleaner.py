# tts_cleaner.py — Turns your Reddit JSON files into clean, Coqui TTS-ready .txt files.
#
# What this does:
#   1. Loads an enhanced_posts JSON file produced by reddit.py
#   2. For each post, assembles a full narration:
#        - A spoken HOOK (the question title, used as an opening line)
#        - The SCRIPT (the stitched comment answers from reddit.py)
#   3. Applies aggressive cleaning so the text is safe for Coqui TTS:
#        - Expands or removes acronyms (TL;DR, NASA, ISS, etc.)
#        - Replaces profanity with neutral alternatives
#        - Strips markdown formatting, URLs, and Reddit-specific artifacts
#        - Splits run-on sentences at natural boundaries
#        - Converts symbols to their spoken equivalents (%, &, °, etc.)
#        - Ensures every sentence ends with clean punctuation
#   4. Saves one .txt file per post into a nominated output folder
#
# Coqui TTS works best with:
#   - Plain sentences — no symbols or abbreviations
#   - No ALL CAPS words (they get mispronounced)
#   - No parentheses mid-sentence (causes unnatural pauses)
#   - Sentences under ~25 words
#   - Consistent punctuation (period, comma, question mark only)

import json      # For loading the enhanced_posts JSON file
import re        # For regex-based text substitutions throughout the cleaning pipeline
import os        # Not directly used but often needed for file path work
import sys       # For reading command-line arguments (sys.argv)
from pathlib import Path   # Modern, cross-platform way to work with file paths


# --- Acronym expansion dictionary ---
# Maps regex patterns to their spoken equivalents.
# An empty string means "remove this entirely" — it's not speakable in any useful form.
# Order matters: this runs BEFORE lowercasing, so case-sensitive matching still works here.
# Add new entries here as you spot new acronyms in your data.
ACRONYMS = {
    # Reddit-specific shorthand
    r'\bTL;?DR\b':        '',                        # "Too Long; Didn't Read" — not speakable, remove
    r'\bTLDR\b':          '',
    r'\bEDIT\b':          '',                        # Edit markers clutter the narration
    r'\bOP\b':            'the original poster',
    r'\bAITA\b':          'am I the jerk',
    r'\bIMO\b':           'in my opinion',
    r'\bIMHO\b':          'in my humble opinion',
    r'\bIIRC\b':          'if I recall correctly',
    r'\bAFAIK\b':         'as far as I know',
    r'\bFWIW\b':          'for what it is worth',
    r'\bFYI\b':           'for your information',
    r'\bELI5\b':          'explain it simply',
    r'\bIRL\b':           'in real life',
    r'\bTBH\b':           'to be honest',
    r'\bNGL\b':           'not going to lie',
    r'\bLMK\b':           'let me know',
    r'\bDM\b':            'direct message',
    r'\bPOV\b':           'point of view',
    r'\bETA\b':           'edited to add',

    # Science and space — spelled out so Coqui pronounces them correctly
    r'\bNASA\b':          'NASA',                    # Coqui handles this as-is — keep unchanged
    r'\bESA\b':           'the European Space Agency',
    r'\bISS\b':           'the International Space Station',
    r'\bLRO\b':           'the Lunar Reconnaissance Orbiter',
    r'\bUV\b':            'ultraviolet',
    r'\bDNA\b':           'DNA',                     # Coqui reads letter-by-letter fine
    r'\bRNA\b':           'RNA',
    r'\bCO2\b':           'carbon dioxide',
    r'\bH2O\b':           'water',
    r'\bO2\b':            'oxygen',

    # Units — converted to their spoken form
    r'\bkm\b':            'kilometres',
    r'\bkg\b':            'kilograms',
    r'\bmph\b':           'miles per hour',
    r'\bkph\b':           'kilometres per hour',
    r'\bkm/s\b':          'kilometres per second',
    r'\bm/s\b':           'metres per second',
    r'\bg\b(?=\s)':       'grams',                   # Only replaces standalone "g" followed by a space
    r'\bcm\b':            'centimetres',
    r'\bmm\b':            'millimetres',
}

# --- Profanity replacement dictionary ---
# Maps swear words to neutral alternatives that read naturally in a narration context.
# An empty string removes the word entirely (e.g. "fucking complex" → "complex").
# Extend this list as you encounter new words in your data.
PROFANITY = {
    r'\bfucking\b':   '',           # Adverbial use — removing it reads more cleanly than substituting
    r'\bf\*cking\b':  '',
    r'\bfuck\b':      'deal with',
    r'\bshit\b':      'stuff',
    r'\bshitty\b':    'poor',
    r'\bbullshit\b':  'nonsense',
    r'\bass\b':       '',
    r'\bdamn\b':      'really',
    r'\bcrap\b':      'rubbish',
    r'\bbastard\b':   'person',
    r'\bpissed\b':    'frustrated',
    r'\bcockpit\b':   'cockpit',    # Not profanity — explicitly kept to avoid false positive
}


def clean_for_tts(raw_text: str) -> str:
    """
    Master cleaning function. Takes raw Reddit text and returns a string
    that is safe and natural for Coqui TTS to read aloud.
    Applies all cleaning rules in the correct order — some steps depend on
    earlier ones having already run (e.g. acronyms must be expanded before lowercasing).

    Parameters:
        raw_text : the raw script string from a post's "script" field

    Returns:
        A cleaned string ready for TTS, or an empty string if the input is too short.
    """

    # Guard clause: if the text is missing or too short to be worth narrating, return nothing
    if not raw_text or len(raw_text.strip()) < 50:
        return ""

    text = raw_text.strip()

    # --- Step 1: Strip markdown formatting ---
    # Coqui reads raw characters — ** and __ appear as noise in the audio.
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)          # **bold** or ***bold*** → bold
    text = re.sub(r'_{1,2}(.*?)_{1,2}',   r'\1', text)          # __italic__ → italic
    text = re.sub(r'~~(.*?)~~',            '',    text)          # ~~strikethrough~~ → removed
    text = re.sub(r'`{1,3}(.*?)`{1,3}',   r'\1', text)          # `code` → code (keep the text)
    text = re.sub(r'#+\s*',               '',    text)          # ### headings → removed
    text = re.sub(r'^\s*[-*>]\s+', '', text, flags=re.MULTILINE) # Bullet points and blockquotes → removed

    # --- Step 2: Remove URLs ---
    # Coqui would try to read "https colon slash slash" aloud — remove them entirely.
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+',     '', text)

    # --- Step 3: Reddit-specific artifacts ---
    # Replace subreddit and user references with natural spoken equivalents
    text = re.sub(r'\br/(\w+)\b', r'the \1 forum', text)    # r/space → the space forum
    text = re.sub(r'\bu/(\w+)\b', r'a commenter',   text)   # u/someuser → a commenter

    # Remove entire lines that are just edit or update markers
    text = re.sub(r'^(EDIT|UPDATE|Edit|Update|Edited)[:\s].*$', '', text,
                  flags=re.MULTILINE | re.IGNORECASE)

    # Convert markdown hyperlinks [link text](url) to just the visible text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # --- Step 4: Expand acronyms ---
    # Must happen BEFORE lowercasing so the case-sensitive \b patterns still match correctly.
    for pattern, replacement in ACRONYMS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # --- Step 5: Replace profanity ---
    for pattern, replacement in PROFANITY.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # --- Step 6: Convert symbols to spoken words ---
    # These are done as simple string replacements, not regex, because no word-boundary logic is needed.
    text = text.replace('&',  ' and ')
    text = text.replace('%',  ' percent ')
    text = text.replace('$',  ' dollars ')
    text = text.replace('£',  ' pounds ')
    text = text.replace('@',  ' at ')
    text = text.replace('°',  ' degrees ')
    text = text.replace('×',  ' times ')
    text = text.replace('≈',  ' approximately ')
    text = text.replace('≥',  ' greater than or equal to ')
    text = text.replace('≤',  ' less than or equal to ')
    text = text.replace('>',  ' greater than ')    # Safe now — blockquotes were already removed in step 1
    text = text.replace('<',  ' less than ')
    text = text.replace('/',  ' or ')              # "km/s" was already handled in ACRONYMS; this catches the rest
    text = text.replace('+',  ' plus ')
    text = text.replace('=',  ' equals ')
    text = text.replace('#',  'number ')
    text = text.replace('~',  'approximately ')

    # --- Step 7: Normalise punctuation ---
    # Coqui pauses on commas and stops on periods — these need to be clean and consistent.
    text = re.sub(r'\.{2,}', '.', text)           # Ellipsis (... or ..) → single period
    text = re.sub(r'!{2,}',  '!', text)           # Multiple exclamation marks → single
    text = re.sub(r'\?{2,}', '?', text)           # Multiple question marks → single
    text = re.sub(r';',      ',', text)            # Semicolons → commas (more natural spoken pause)
    text = re.sub(r':\s',    '. ', text)           # Colons mid-sentence → period (forces a stop)
    text = re.sub(r'\s*-{2,}\s*', ', ', text)     # Em-dash or double-dash → comma

    # Convert parenthetical asides to natural comma phrasing so Coqui reads them smoothly.
    # "(which means X)" → ", which means X,"
    text = re.sub(r'\s*\(([^)]{3,60})\)\s*', r', \1, ', text)

    # Drop any remaining parentheses with very short content (abbreviations, single letters, etc.)
    text = re.sub(r'\([^)]*\)', '', text)

    # --- Step 8: Split long sentences ---
    # Coqui handles sentences over ~25 words poorly — they sound rushed and unnatural.
    # split_long_sentences() breaks them at conjunctions or commas near the midpoint.
    text = split_long_sentences(text)

    # --- Step 9: Convert paragraph structure to spoken flow ---
    # Double newlines (paragraph breaks) become a space — sentences already ended with periods.
    # Single newlines (line breaks within a paragraph) become a comma pause.
    text = re.sub(r'\n{2,}', ' ',  text)
    text = re.sub(r'\n',     ', ', text)

    # --- Step 10: Final whitespace and punctuation cleanup ---
    text = re.sub(r'\s{2,}', ' ', text).strip()   # Collapse multiple consecutive spaces to one
    text = re.sub(r'\s,',    ',', text)            # " ," → "," (space before comma removed)
    text = re.sub(r',\s*,',  ',', text)            # ",," → ","
    text = re.sub(r',\s*\.', '.', text)            # ",." → "."

    # Clean up sentence-start artifacts left after acronym removal (e.g. ". , word" → ". word")
    text = re.sub(r'(?<=[.!?])\s*,\s*', ' ', text)

    # Remove any leading comma or semicolon at the very start of the whole text
    text = re.sub(r'^\s*[,;]\s*', '', text)

    # --- Step 11: Ensure the text ends with a sentence-terminating character ---
    # Coqui needs a clear signal that the narration has finished.
    if text and text[-1] not in '.!?':
        text += '.'

    return text


def split_long_sentences(text: str) -> str:
    """
    Breaks sentences longer than 25 words into two shorter ones at the most
    natural split point — preferring a conjunction or comma over a hard mid-cut.
    Runs up to 3 passes because one split can still leave a long sentence.

    Parameters:
        text : the text string to process (may contain multiple sentences)

    Returns:
        The same text with long sentences split into shorter ones.
    """

    for _ in range(3):   # Up to 3 passes — most run-ons are resolved in 1 or 2
        # Split the text into individual sentences at sentence-ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = []

        for sentence in sentences:
            words = sentence.split()

            if len(words) <= 25:
                result.append(sentence)   # Short enough — keep as-is
                continue

            # Sentence is too long — find the best place to split it
            split_index = find_natural_split(words)
            first_half  = ' '.join(words[:split_index])
            second_half = ' '.join(words[split_index:])

            # The first half must end with a period so Coqui treats it as a complete sentence
            if first_half and first_half[-1] not in '.!?,':
                first_half += '.'

            # The second half should start with a capital letter
            if second_half:
                second_half = second_half[0].upper() + second_half[1:]

            result.append(first_half)
            result.append(second_half)

        text = ' '.join(result)

    return text


def find_natural_split(words: list) -> int:
    """
    Finds the best index at which to split a long list of words into two sentences.
    Searches a window of ±8 words around the midpoint, preferring conjunctions.
    Falls back to a comma position, then to a hard midpoint cut.

    Parameters:
        words : a list of word strings representing a single sentence

    Returns:
        An integer index — split the list at words[:index] and words[index:].
    """

    mid = len(words) // 2   # Ideal midpoint — we want splits as close to here as possible

    # Search within ±8 words of the midpoint (clamped to valid indices)
    search_start = max(1, mid - 8)
    search_end   = min(len(words) - 1, mid + 8)

    # Words that make a natural sentence boundary when split before them
    conjunctions = {'and', 'but', 'so', 'because', 'which', 'where',
                    'while', 'although', 'however', 'therefore', 'thus',
                    'since', 'unless', 'whereas'}

    # Find the conjunction closest to the midpoint within the search window
    best          = None
    best_distance = float('inf')   # Start with "infinitely far away" so any real result beats it

    for i in range(search_start, search_end):
        word_clean = words[i].lower().rstrip('.,')   # Strip trailing punctuation before comparing
        if word_clean in conjunctions:
            distance = abs(i - mid)
            if distance < best_distance:
                best_distance = distance
                best = i

    if best is not None:
        return best   # Split just before the nearest conjunction

    # No conjunction found — try splitting after a comma near the midpoint
    for i in range(search_start, search_end):
        if words[i].endswith(','):
            return i + 1   # Split after the comma word

    # Last resort: hard midpoint cut
    return mid


def build_spoken_hook(title: str) -> str:
    """
    Turns the post title into a natural spoken opening line for the narration.
    Currently returns the title as a question. This function is a hook point
    for more sophisticated intro generation in future.

    Parameters:
        title : the raw post title string

    Returns:
        A string suitable for use as the first sentence of the narration.
    """
    title = title.strip()
    return f"{title}?"


def process_reddit_json(json_filepath: str, output_folder: str = "tts_ready_scripts"):
    """
    Main entry point. Loads one enhanced_posts JSON file produced by reddit.py
    and writes one clean .txt narration file per post into the output folder.

    Parameters:
        json_filepath : path to the enhanced_posts JSON file
        output_folder : folder to write the .txt files into (created if it doesn't exist)
    """

    json_path = Path(json_filepath)

    # Guard clause: check the input file actually exists before trying to open it
    if not json_path.exists():
        print(f"File not found: {json_filepath}")
        return

    # Create the output folder if it doesn't already exist (parents=False since folder is flat)
    output_dir = Path(output_folder)
    output_dir.mkdir(exist_ok=True)

    # Load all posts from the JSON file into a Python list
    with open(json_path, encoding='utf-8') as f:
        posts = json.load(f)

    print(f"Processing {len(posts)} posts from {json_path.name}...")
    print(f"Output folder: {output_dir.resolve()}\n")

    saved_count = 0   # Track how many files we successfully write

    for i, post in enumerate(posts, start=1):
        script = post.get("script", "").strip()

        if not script:
            print(f"  #{i:02d} Skipped — no script field")
            continue

        # Run the full cleaning pipeline on the script body
        cleaned_script = clean_for_tts(script)

        # Skip posts where the cleaned result is too short to be worth narrating
        if len(cleaned_script) < 150:
            print(f"  #{i:02d} Skipped — cleaned script too short ({len(cleaned_script)} chars)")
            continue

        # Build the spoken opening hook from the post title
        title     = post.get("title", "")
        subreddit = post.get("subreddit", "unknown")
        hook      = build_spoken_hook(title)

        # Assemble the final narration: hook first, then the cleaned script body
        full_narration = f"{hook}\n\n{cleaned_script}"

        # Build a safe filename from the subreddit and a slugified version of the title.
        # re.sub removes any character that isn't a lowercase letter, digit, or underscore.
        # [:50] truncates to 50 characters to avoid excessively long filenames.
        title_slug = re.sub(r'[^a-z0-9]+', '_', title.lower())[:50].strip('_')
        filename   = f"{subreddit}_{title_slug}.txt"
        filepath   = output_dir / filename

        # Write the final narration text to disk in UTF-8 encoding
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_narration)

        print(f"  #{i:02d} Saved → {filename}  ({len(full_narration)} chars)")
        saved_count += 1

    print(f"\nDone! {saved_count} of {len(posts)} posts saved to: {output_dir.resolve()}")
    print("These .txt files are ready to feed directly into Coqui TTS.")


# This block only runs when the file is executed directly (e.g. "python tts_cleaner.py").
# If this file is imported by another script, this block is skipped entirely.
if __name__ == "__main__":

    print("Reddit → Coqui TTS Cleaner\n")

    # Accept an optional command-line argument for the JSON file path.
    # If none is provided, fall back to a sensible default filename.
    if len(sys.argv) > 1:
        json_file = sys.argv[1]   # e.g. python tts_cleaner.py my_posts.json
    else:
        json_file = "askscience_enhanced_posts.json"   # Default — change this if needed

    process_reddit_json(json_file)

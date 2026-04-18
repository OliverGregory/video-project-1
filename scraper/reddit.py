# reddit.py — Enhanced Reddit scraper for educational physics/space content.
# Grabs top posts and their top comments, filters for high-quality narration text,
# and prepares TTS-ready scripts sourced from either the post body or its comments.
#
# Key logic:
# For Q&A subreddits like askscience, the post body is usually just a question —
# not a useful TTS script. The real content lives in the comments.
# This script detects question-style posts and prefers comments for those cases.

import requests  # For making HTTP requests to Reddit's JSON API
import json      # For saving results to disk as JSON
import time      # For pausing between retries and being polite to Reddit's servers

# Reddit requires a User-Agent header to identify who is making requests.
# Without it, Reddit rejects the connection outright.
HEADERS = {
    "User-Agent": "video-project-1 personal project"  # A name tag so Reddit knows who is asking
}

# How many times to retry a failed request before giving up entirely
MAX_RETRIES = 3

# How long to wait (in seconds) after a 429 rate-limit response.
# Reddit sometimes includes a "Retry-After" header with an exact value —
# we use that if present, and fall back to this constant if not.
RETRY_AFTER_DEFAULT = 10

# Subreddits where the post body is typically just a question and the value is in the replies.
# For these we always prefer stitched comments over selftext as the narration script.
QA_SUBREDDITS = {
    "askscience", "askphysics", "askhistorians", "explainlikeimfive",
    "eli5", "asknasa", "astronomy"
}

# Minimum character thresholds for text to be considered usable as narration
MIN_SELFTEXT_CHARS = 300   # Shorter than this is likely just a question, not a full explanation
MIN_COMMENT_CHARS  = 150   # Comments shorter than this are too thin to narrate meaningfully
MIN_SCRIPT_CHARS   = 300   # The final assembled script must meet this length to be kept


def fetch_top_posts(subreddit, limit=10, timeframe="month"):
    """
    Visits Reddit's JSON API and returns a list of top posts from the given subreddit.
    Retries up to MAX_RETRIES times and handles network failures, rate limiting,
    and unexpected responses gracefully.

    Parameters:
        subreddit : which community to visit, e.g. "askscience"
        limit     : how many posts to fetch (Reddit's max is 100)
        timeframe : time window — "hour", "day", "week", "month", "year", or "all"

    Returns:
        A list of post dictionaries, or an empty list if every attempt fails.
    """

    # Build the URL for Reddit's JSON endpoint.
    # For r/askscience this becomes: https://www.reddit.com/r/askscience/top.json
    url = f"https://www.reddit.com/r/{subreddit}/top.json"

    # Query parameters tacked onto the URL: ?limit=10&t=month
    # Reddit reads these to know how many posts to return and over what time window.
    params = {"limit": limit, "t": timeframe}

    # Retry loop — attempt the request up to MAX_RETRIES times before giving up.
    # `attempt` counts from 0 up to (but not including) MAX_RETRIES.
    for attempt in range(MAX_RETRIES):

        print(f"Fetching top {limit} posts from r/{subreddit} "
              f"(timeframe: {timeframe})... [attempt {attempt + 1} of {MAX_RETRIES}]")

        # --- Outer try/except: catches network-level failures ---
        # These happen before Reddit even has a chance to respond —
        # no internet, DNS failure, or the server not responding in time.
        try:
            # Send the GET request. timeout=10 means: if Reddit doesn't respond
            # within 10 seconds, stop waiting and raise a Timeout error.
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)

        except requests.exceptions.ConnectionError:
            # Raised when the network itself is unreachable — no internet or Reddit is down.
            print(f"  Connection error. (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)   # Pause before the next attempt
            continue            # Jump to the next iteration of the retry loop

        except requests.exceptions.Timeout:
            # Raised when the server takes longer than the timeout value to respond.
            print(f"  Request timed out. (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            continue

        # --- HTTP status code checks ---
        # Even if the network request succeeded, Reddit may have sent back an error code.
        # response.status_code is a number: 200 = OK, 429 = rate limited, 5xx = server error.

        if response.status_code == 429:
            # 429 means "Too Many Requests" — we have been rate limited.
            # int(...) converts the header string to a number; fall back to our default if absent.
            wait_time = int(response.headers.get("Retry-After", RETRY_AFTER_DEFAULT))
            print(f"  Rate limited. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue   # Try again after the wait

        if response.status_code >= 500:
            # 5xx means something broke on Reddit's end. Wait and retry.
            print(f"  Reddit server error ({response.status_code}). (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            continue

        if response.status_code != 200:
            # Any other unexpected code (403 Forbidden, 404 Not Found, etc.).
            # These won't improve with retrying, so give up immediately.
            print(f"  Unexpected status: {response.status_code}. Giving up.")
            return []

        # --- Inner try/except: catches problems parsing the response body ---
        # Even with a 200 OK the content might not be valid JSON,
        # or might not have the nested structure we expect.
        try:
            # .json() parses Reddit's response text into a Python dictionary.
            # Raises ValueError if the body isn't valid JSON at all.
            data = response.json()

            # Posts are buried inside nested dictionaries like Russian dolls:
            #   data → "data" → "children" → list of posts
            # Each item in "children" is a wrapper; the actual post lives inside ["data"].
            # If any of these keys are missing, Python raises a KeyError.
            posts = data["data"]["children"]

        except (ValueError, KeyError) as e:
            # ValueError = response wasn't JSON. KeyError = JSON structure wasn't what we expected.
            # `e` contains details about exactly what went wrong, useful for debugging.
            print(f"  Error parsing response: {e}")
            return []

        # If we reach here without hitting any except block, everything worked.
        # Unwrap each post from its wrapper and return a plain list of post dictionaries.
        return [post["data"] for post in posts]

    # We only reach this line if every attempt in the loop failed.
    print(f"  Giving up after {MAX_RETRIES} failed attempts.")
    return []   # Return an empty list so the rest of the script can handle it gracefully


def fetch_comments(post_id, limit=5):
    """
    Fetches the top comments for a single post by its Reddit post ID.
    Skips deleted, removed, or very short comments.

    Parameters:
        post_id : the Reddit post ID string (e.g. "abc123")
        limit   : maximum number of usable comments to return

    Returns:
        A list of cleaned comment body strings, or an empty list on failure.
    """

    # Reddit's comment thread JSON endpoint for a given post ID
    url = f"https://www.reddit.com/comments/{post_id}.json"

    for attempt in range(MAX_RETRIES):
        print(f"  Fetching comments for post {post_id}... [attempt {attempt + 1}]")

        try:
            response = requests.get(url, headers=HEADERS, timeout=10)

            if response.status_code == 429:
                wait_time = int(response.headers.get("Retry-After", RETRY_AFTER_DEFAULT))
                print(f"    Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                print(f"    Unexpected status: {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)
                continue

            # Reddit returns a two-element list for comment threads.
            # Index 0 = the post itself; index 1 = the comments.
            data = response.json()
            comments_list = data[1]["data"]["children"]

            cleaned = []
            for comment in comments_list:
                body = comment.get("data", {}).get("body", "")

                # Skip deleted/removed placeholders and anything too short to be useful
                if body and body not in ["[deleted]", "[removed]"] and len(body.strip()) >= MIN_COMMENT_CHARS:
                    cleaned.append(body.strip())

                if len(cleaned) >= limit:
                    break   # Stop once we have enough good comments

            return cleaned

        except Exception as e:
            # Broad catch here because comment parsing can fail in many unexpected ways
            # (malformed JSON, missing keys, network errors mid-read, etc.)
            print(f"    Error: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
            continue

    return []


def is_question_post(post_data):
    """
    Returns True if the post looks like a question rather than a story or article.
    This tells select_best_script() to look at comments for the real narration content.

    We check three things:
        1. Is it from a known Q&A subreddit (e.g. askscience)?
        2. Does the title end with a question mark?
        3. Is the selftext short — i.e. just a question, not a detailed write-up?

    Parameters:
        post_data : a dictionary of post fields as returned by fetch_top_posts()

    Returns:
        True if the post is question-style, False otherwise.
    """
    subreddit = post_data.get("subreddit", "").lower()
    title     = post_data.get("title", "")
    selftext  = post_data.get("selftext", "").strip()

    # Known Q&A subreddits are almost always question-style by definition
    if subreddit in QA_SUBREDDITS:
        return True

    # A title ending in "?" with a thin body is almost certainly just a question
    if title.strip().endswith("?") and len(selftext) < MIN_SELFTEXT_CHARS:
        return True

    return False


def select_best_script(post_data):
    """
    Chooses the best narration-ready text for TTS from a post's available content.

    Logic:
        Question posts (askscience etc.): stitch together the top comments.
            The question title becomes an intro hook — it is NOT used as the main body.
        Story/article posts: use selftext if long enough; fall back to stitched comments.

    Why stitch multiple comments instead of picking just one?
    A single comment is often only 150-300 words. Several expert answers together
    give a richer, more complete narration — similar to a documentary that assembles
    multiple expert quotes into one flowing explanation.

    Parameters:
        post_data : a dictionary containing "title", "selftext", and "comments" keys

    Returns:
        (script_text, source_type) where source_type is "comments" or "selftext",
        or (None, None) if nothing usable is found.
    """
    selftext = post_data.get("selftext", "").strip()
    comments = post_data.get("comments", [])
    title    = post_data.get("title", "")

    # Filter down to only comments long enough to be worth narrating
    good_comments = [c for c in comments if len(c) >= MIN_COMMENT_CHARS]

    if is_question_post(post_data):
        # For Q&A posts, assemble top comments into one narration block.
        # We cap at 3 comments to keep the final script under ~90 seconds of TTS audio.
        if good_comments:
            script = assemble_comment_narrative(title, good_comments[:3])
            if len(script) >= MIN_SCRIPT_CHARS:
                return script, "comments"

        # Edge case: no usable comments — fall back to selftext if it is long enough
        if len(selftext) >= MIN_SELFTEXT_CHARS:
            return selftext, "selftext"

    else:
        # Non-Q&A post: prefer a long self-post (article or story format)
        if len(selftext) >= MIN_SELFTEXT_CHARS:
            return selftext, "selftext"

        # Fall back to stitched comments if selftext is too short
        if good_comments:
            script = assemble_comment_narrative(title, good_comments[:3])
            if len(script) >= MIN_SCRIPT_CHARS:
                return script, "comments"

    # Nothing usable found in any source
    return None, None


def assemble_comment_narrative(title, comments):
    """
    Stitches a list of comment strings into a single flowing narrative block.
    Uses simple deterministic transition phrases between answers so the result
    doesn't feel like a disconnected list.

    Structure:
        [Answer 1 — top comment, no transition]
        [Transition phrase] [Answer 2]
        [Transition phrase] [Answer 3]
        ...

    No AI is used here — tts_cleaner.py handles all further text cleanup.

    Parameters:
        title    : the post title (reserved for future use as a spoken intro hook)
        comments : a list of comment body strings to stitch together

    Returns:
        A single string with comments joined by double newlines (paragraph breaks).
    """

    # Transition phrases cycled between answers so successive comments don't feel abrupt.
    # We use modulo (%) to cycle through the list regardless of how many comments there are.
    transitions = [
        "Another important factor is this.",
        "A commenter added more detail.",
        "Someone else offered a different angle.",
        "To build on that point,",
        "Here is what else came up in the discussion.",
    ]

    parts = []

    for i, comment in enumerate(comments):
        if i == 0:
            # First comment needs no transition — it follows the question hook directly
            parts.append(comment)
        else:
            # i % len(transitions) cycles through 0,1,2,3,4,0,1,2... so we never go out of bounds
            transition = transitions[i % len(transitions)]
            parts.append(f"{transition} {comment}")

    # Join with double newlines so tts_cleaner.py treats each answer as a separate paragraph
    return "\n\n".join(parts)


def enhance_posts(posts, comment_limit=5):
    """
    Takes a list of raw post dictionaries, fetches comments for each one,
    selects the best script source, and returns a filtered list of
    fully assembled, TTS-ready post dictionaries.

    Posts with no usable text are silently dropped from the output.

    Parameters:
        posts         : raw list of post dictionaries from fetch_top_posts()
        comment_limit : how many comments to fetch per post

    Returns:
        A list of enriched post dictionaries, each containing a "script" key.
    """
    enhanced = []

    for post in posts:
        post_id = post.get("id")
        if not post_id:
            continue   # Skip any post that is missing an ID (shouldn't happen, but defensive)

        title     = post.get("title", "")
        selftext  = post.get("selftext", "").strip()
        score     = post.get("score", 0)
        subreddit = post.get("subreddit", "")

        print(f"\nProcessing: {title[:70]}...")
        print(f"  Subreddit: r/{subreddit} | Score: {score}")

        # Fetch the top comments for this post
        comments = fetch_comments(post_id, limit=comment_limit)

        # Be polite to Reddit's servers — wait 2 seconds between posts
        time.sleep(2)

        # Assemble a dictionary with everything we know about this post
        content = {
            "title":     title,
            "selftext":  selftext,
            "score":     score,
            "subreddit": subreddit,
            "comments":  comments,
            "url":       post.get("url", ""),
            "permalink": post.get("permalink", ""),
        }

        # Try to find the best narration script from available text sources
        script, source_type = select_best_script(content)

        if script:
            content["script"]      = script
            content["source_type"] = source_type
            enhanced.append(content)
            print(f"  Kept — source: {source_type} | script length: {len(script)} chars")
        else:
            print(f"  Skipped — no usable text found")

    print(f"\nEnhanced {len(enhanced)} high-quality posts.")
    return enhanced


def save_posts(posts, filepath):
    """
    Writes the enhanced post list to a JSON file on disk.

    Parameters:
        posts    : list of enhanced post dictionaries
        filepath : output file path, e.g. "askscience_enhanced_posts.json"
    """

    # Guard clause: nothing to write if the list is empty
    if not posts:
        print("No posts to save.")
        return

    # ensure_ascii=False preserves unicode characters (e.g. é, ñ, °) instead of escaping them
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(posts)} posts to '{filepath}'")


def print_summary(enhanced_posts):
    """
    Prints a human-readable summary of each enhanced post to the terminal,
    including a short preview of the assembled script.

    Parameters:
        enhanced_posts : list of enhanced post dictionaries from enhance_posts()
    """

    # Guard clause: nothing to print if the list is empty
    if not enhanced_posts:
        print("No posts to display.")
        return

    print("\nTTS-READY POSTS SUMMARY\n")

    for i, post in enumerate(enhanced_posts, start=1):
        title     = post.get("title", "N/A")
        score     = post.get("score", 0)
        subreddit = post.get("subreddit", "N/A")
        source    = post.get("source_type", "N/A")
        script    = post.get("script", "")

        # Show the first 300 characters of the script as a preview
        preview = script[:300] + "..." if len(script) > 300 else script

        # :02d pads the post number to two digits; :>6 right-aligns the score
        print(f"#{i:02d} | r/{subreddit} | Score: {score:>6} | Source: {source}")
        print(f"     {title}")
        print(f"     --- Script preview ---")
        print(f"     {preview}")
        print(f"     ({len(script)} characters total)")
        print()   # Blank line between posts for readability


# This block only runs when the file is executed directly (e.g. "python reddit.py").
# If this file is imported by another script, this block is skipped entirely.
if __name__ == "__main__":

    SUBREDDIT     = "askscience"
    LIMIT         = 10
    TIMEFRAME     = "month"
    COMMENT_LIMIT = 5
    OUTPUT_FILE   = f"{SUBREDDIT}_enhanced_posts.json"   # e.g. "askscience_enhanced_posts.json"

    print("Reddit Educational Scraper — TTS Script Builder\n")

    # Step 1: Fetch the raw posts from Reddit
    raw_posts = fetch_top_posts(subreddit=SUBREDDIT, limit=LIMIT, timeframe=TIMEFRAME)

    if raw_posts:
        # Step 2: Fetch comments, select scripts, and filter out poor-quality posts
        enhanced_posts = enhance_posts(raw_posts, comment_limit=COMMENT_LIMIT)

        # Step 3: Save the enriched data to disk as JSON
        save_posts(enhanced_posts, OUTPUT_FILE)

        # Step 4: Print a terminal summary so we can see what we got
        print_summary(enhanced_posts)
    else:
        print("No posts fetched. Check your internet connection or subreddit name.")

    print("\nDone! Feed the JSON into tts_cleaner.py to produce your .txt files.")

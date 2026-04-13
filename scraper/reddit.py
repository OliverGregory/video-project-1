# reddit.py — Grabs the top posts from a subreddit and saves them to a file on your computer.
import requests  # For making HTTP requests (visiting web pages programmatically)
import json      # For reading and writing JSON data
import time      # For pausing the script (used when waiting before a retry)

# When a browser visits a website it identifies itself with a "User-Agent" string.
# Reddit requires scripts to do the same, without it, requests are rejected.
HEADERS = {
    "User-Agent": "video-project-1 personal project"  # A name tag so Reddit knows who is asking
}

# How many times to retry a failed request before giving up entirely
MAX_RETRIES = 3

# How many seconds to wait before retrying after a 429 (rate limited) response.
# Reddit sometimes sends a "Retry-After" header with an exact value — we use that if available,
# and fall back to this constant if not.
RETRY_AFTER_DEFAULT = 10


def fetch_top_posts(subreddit, limit=5, timeframe="week"):
    """
    Visits Reddit's JSON API and returns a list of top posts from the given subreddit.
    Handles network failures, rate limiting, and unexpected responses gracefully.

    Parameters:
        subreddit : which community to visit, e.g. "space"
        limit     : how many posts to fetch (max 100)
        timeframe : time window — "hour", "day", "week", "month", "year", or "all"

    Returns:
        A list of post dictionaries, or an empty list if every attempt fails.
    """

    # Build the URL for Reddit's JSON endpoint.
    # For r/space this becomes: https://www.reddit.com/r/space/top.json
    url = f"https://www.reddit.com/r/{subreddit}/top.json"

    # Query parameters appended to the URL: ?limit=5&t=week
    # Reddit reads these to know how many posts to return and over what time window.
    params = {
        "limit": limit,    # How many posts we want
        "t": timeframe     # Which time window to look at
    }

    # Retry loop — attempt the request up to MAX_RETRIES times before giving up.
    # `attempt` counts from 0 up to (but not including) MAX_RETRIES.
    for attempt in range(MAX_RETRIES):

        print(f"Fetching top {limit} posts from r/{subreddit} "
              f"(timeframe: {timeframe})... [attempt {attempt + 1} of {MAX_RETRIES}]")

        # --- Outer try/except: catches network-level failures ---
        # These are problems that occur before Reddit even has a chance to respond,
        # e.g. no internet connection, DNS lookup failure, or the connection timing out.
        try:
            # Send the GET request — the equivalent of typing the URL into a browser and hitting Enter.
            # timeout=10 means: if Reddit doesn't respond within 10 seconds, raise a Timeout error.
            response = requests.get(url, headers=HEADERS, params=params, timeout=10)

        except requests.exceptions.ConnectionError:
            # Raised when the network itself is unreachable — no internet, or Reddit's servers are down.
            print(f"  Connection error: could not reach Reddit. "
                  f"Check your internet connection. (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                print("  Waiting 5 seconds before retrying...")
                time.sleep(5)    # Pause before the next attempt
            continue             # Jump to the next iteration of the retry loop

        except requests.exceptions.Timeout:
            # Raised when the server takes longer than the timeout value to respond.
            print(f"  Request timed out after 10 seconds. (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                print("  Waiting 5 seconds before retrying...")
                time.sleep(5)
            continue

        # HTTP status code checks:
        # Even if the network request succeeded, Reddit may have sent back an error code.
        # response.status_code is a number: 200 = OK, 429 = rate limited, 5xx = server error, etc.

        if response.status_code == 429:
            # 429 means "Too Many Requests" — we've been rate limited.
            # Reddit may include a "Retry-After" header with exactly how many seconds to wait.
            # int(...) converts the header string to a number; we fall back to our default if absent.
            wait_time = int(response.headers.get("Retry-After", RETRY_AFTER_DEFAULT))
            print(f"  Rate limited (429). Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)
            continue   # Try again after the wait

        if response.status_code >= 500:
            # 5xx codes mean something went wrong on Reddit's end (their servers are having issues).
            # Nothing we can do except wait and retry — the problem is on their side.
            print(f"  Reddit server error (status {response.status_code}). (attempt {attempt + 1})")
            if attempt < MAX_RETRIES - 1:
                print("  Waiting 5 seconds before retrying...")
                time.sleep(5)
            continue

        if response.status_code != 200:
            # Any other unexpected code (e.g. 403 Forbidden, 404 Not Found).
            # These won't improve with retrying, so give up immediately.
            print(f"  Unexpected response status: {response.status_code}. Giving up.")
            return []

        # Inner try/except: catches problems parsing Reddit's response:
        # Even with a 200 OK, the response body might not be valid JSON,
        # or might not have the structure we expect.
        try:
            # Reddit sends back a blob of JSON text.
            # .json() parses it into a Python dictionary we can dig into.
            # Raises JSONDecodeError if the body isn't valid JSON at all.
            data = response.json()

            # The posts are buried inside nested dictionaries, like Russian dolls:
            #   data  →  "data"  →  "children"  →  list of posts
            # Each item in "children" is a wrapper — the actual post lives inside ["data"].
            # If any of these keys are missing, Python raises a KeyError.
            posts = data["data"]["children"]

        except requests.exceptions.JSONDecodeError:
            # Reddit's response couldn't be parsed as JSON at all.
            # This can happen if Reddit is returning an HTML error page instead of JSON.
            print("  Error: Reddit's response was not valid JSON. "
                  "Reddit may be down or returning an error page.")
            return []

        except KeyError as e:
            # The JSON was valid but didn't have the structure we expected.
            # `e` contains the name of the missing key, which helps with debugging.
            print(f"  Error: Unexpected JSON structure — missing key: {e}. "
                  "Reddit may have changed their API format.")
            return []

        # If we've reached here without hitting any except block, everything worked.
        # Unwrap each post from its "children" wrapper and return the plain list.
        return [post["data"] for post in posts]

    # We only reach this line if every attempt in the retry loop failed.
    print(f"  Giving up after {MAX_RETRIES} failed attempts.")
    return []   # Return an empty list so the rest of the script can handle it gracefully


def save_posts(posts, filepath):
    """
    Writes the list of post dictionaries to a JSON file on disk.

    Parameters:
        posts    : the list of post dictionaries returned by fetch_top_posts()
        filepath : where to save the file, e.g. "space_posts.json"
    """

    # Guard clause: nothing to save if the list is empty
    # (which happens when fetch_top_posts() returned [] due to an error)
    if not posts:
        print("No posts to save.")
        return

    # try/except catches file system errors — e.g. the path doesn't exist,
    # or we don't have permission to write to that location.
    try:
        # "with open(...) as f:" opens a file for writing.
        # "w" = write mode: creates the file if it doesn't exist, or overwrites it if it does.
        # The "with" block automatically closes the file when we're done, even if an error occurs.
        with open(filepath, "w") as f:

            # json.dump() converts our Python list to JSON text and writes it to the file.
            # indent=2 makes the output human-readable with neat indentation.
            json.dump(posts, f, indent=2)

        print(f"Saved {len(posts)} posts to '{filepath}'")

    except OSError as e:
        # OSError covers a wide range of file system problems:
        # permission denied, disk full, invalid path, etc.
        # `e` contains a human-readable description of exactly what went wrong.
        print(f"  Error: Could not save file '{filepath}': {e}")


def print_summary(posts):
    """
    Prints a brief human-readable summary of each post to the terminal,
    so you can see what was fetched without opening the saved file.

    Parameters:
        posts : the list of post dictionaries returned by fetch_top_posts()
    """

    # Guard clause: nothing to print if the list is empty
    if not posts:
        print("No posts to display.")
        return

    print("\nHere are the posts we found:\n")
    print("-" * 60)  # A line of dashes used as a visual divider

    # enumerate() gives us a counter (i) alongside each post as we loop.
    # start=1 means we count from 1, not 0, which is more natural to read.
    for i, post in enumerate(posts, start=1):

        # .get("field", "N/A") safely retrieves a value from the dictionary.
        # If the key doesn't exist (Reddit sometimes omits fields), it returns "N/A" instead of crashing.
        title  = post.get("title", "N/A")
        author = post.get("author", "N/A")
        score  = post.get("score", 0)     # score = upvotes minus downvotes
        url    = post.get("url", "N/A")

        # :02d pads the post number to two digits (01, 02 ... 10, 11)
        # :>6 right-aligns the score in a 6-character wide column so numbers line up neatly
        print(f"#{i:02d} | Score: {score:>6} | u/{author}")
        print(f"     {title}")
        print(f"     {url}")
        print()  # Blank line between posts for readability


# This block only runs when the file is executed directly (e.g. "python reddit.py").
# If this file were imported by another script, this block would be skipped.
# Think of it as the "green flag" in Scratch — the designated starting point.
if __name__ == "__main__":

    SUBREDDIT   = "space"             # Which subreddit to scrape
    LIMIT       = 5                   # How many posts to grab
    TIMEFRAME   = "week"              # Top posts from the past week
    OUTPUT_FILE = "space_posts.json"  # Where to save the results on disk

    # Step 1: Fetch posts from Reddit.
    # Returns an empty list rather than crashing if anything goes wrong.
    posts = fetch_top_posts(subreddit=SUBREDDIT, limit=LIMIT, timeframe=TIMEFRAME)

    # Step 2: Save them to a JSON file (skipped gracefully if posts is empty)
    save_posts(posts, OUTPUT_FILE)

    # Step 3: Print a quick summary to the terminal (skipped gracefully if posts is empty)
    print_summary(posts)

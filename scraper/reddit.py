# ============================================================
# reddit.py — A script that grabs the top posts from Reddit
# and saves them to a file on your computer.
#
# Think of it like this:
#   - Reddit is a giant library full of posts
#   - This script walks in, grabs the top 25 posts from r/space
#   - Then writes them down in a neat list (a JSON file)
# ============================================================

# "import" means we're borrowing tools that someone else already built.
# We don't have to build everything from scratch!

import requests  # This tool knows how to talk to websites (like a web browser, but in code)
import json      # This tool knows how to read and write JSON (a way of storing data neatly)


# ============================================================
# HEADERS — telling Reddit who we are
#
# When your browser visits a website, it quietly tells the site
# "hey, I'm Chrome on a Mac" — this is called a User-Agent.
# Reddit asks that scripts do the same, so we introduce ourselves.
# ============================================================
HEADERS = {
    "User-Agent": "video-project-1 personal project"  # Just a name tag so Reddit knows it's us
}


# ============================================================
# FUNCTION: fetch_top_posts
#
# Ingredients:
#   subreddit  — which community to visit, e.g. "space"
#   limit      — how many posts to grab (max 100)
#   timeframe  — "week" means top posts from the last 7 days
# ============================================================
def fetch_top_posts(subreddit, limit=5, timeframe="week"):

    # Build the URL we want to visit.
    # For r/space it becomes:
    #   https://www.reddit.com/r/space/top.json
    # The f"..." bit lets us drop variables right into the text.
    url = f"https://www.reddit.com/r/{subreddit}/top.json"

    # These are extra options we tack onto the URL, like:
    #   ?limit=5&t=week
    # Reddit reads these to know how many posts to send back.
    params = {
        "limit": limit,       # How many posts we want
        "t": timeframe        # Which time window (hour / day / week / month / year / all)
    }

    # Actually visit the URL — like typing it into a browser and hitting Enter.
    # requests.get() sends a GET request (just "please give me data", not "change anything").
    print(f"Fetching top {limit} posts from r/{subreddit} (timeframe: {timeframe})...")
    response = requests.get(url, headers=HEADERS, params=params)

    # Reddit sends back a big blob of JSON text.
    # .json() turns that text into a Python dictionary we can dig into.
    data = response.json()

    # The posts are buried inside the response like Russian dolls:
    #   data  ➜  "data"  ➜  "children"  ➜  list of posts
    # Each item in "children" is a wrapper — the actual post lives inside ["data"].
    posts = data["data"]["children"]

    # Loop through every post, unwrap it, and return just the good stuff.
    # This gives us a plain list of dictionaries, one per post.
    return [post["data"] for post in posts]


# ============================================================
# FUNCTION: save_posts
#
# Once we have the list of posts, this function writes them
# to a file on your computer so you can look at them later
# without having to ask Reddit again.
#
# Ingredients:
#   posts    — the list of post dictionaries we fetched above
#   filepath — where to save the file, e.g. "space_posts.json"
# ============================================================
def save_posts(posts, filepath):

    # "with open(...) as f:" opens a file for writing.
    # The "w" means write mode — it creates the file if it doesn't exist,
    # or wipes it clean and starts fresh if it does.
    with open(filepath, "w") as f:

        # json.dump() takes our Python list and writes it into the file
        # in JSON format. indent=2 makes it human-readable (nicely spaced out).
        json.dump(posts, f, indent=2)

    print(f"Saved {len(posts)} posts to '{filepath}'")


# ============================================================
# FUNCTION: print_summary
#
# A little bonus function that prints a quick human-readable
# summary of each post straight to the terminal —
# so you don't have to open the file just to see what we got.
# ============================================================
def print_summary(posts):

    print("\nHere are the posts we found:\n")
    print("-" * 60)  # Print a line of dashes as a divider

    # "enumerate" gives us a counter (i) alongside each post.
    # We start counting from 1 because humans don't start at 0!
    for i, post in enumerate(posts, start=1):

        # Pull out just the fields we care about.
        # .get("field", "N/A") means: grab this field, but if it's missing, say "N/A".
        title   = post.get("title", "N/A")
        author  = post.get("author", "N/A")
        score   = post.get("score", 0)        # "score" = upvotes minus downvotes
        url     = post.get("url", "N/A")

        print(f"#{i:02d} | Score: {score:>6} | u/{author}")
        print(f"     {title}")
        print(f"     {url}")
        print()  # Blank line between posts


# ============================================================
# MAIN BLOCK
#
# This is the "start here" sign.
# The special line below means: only run this code if we're
# running THIS file directly (not importing it from somewhere else).
#
# Think of it like the green flag in Scratch — it only runs
# when YOU press play.
# ============================================================
if __name__ == "__main__":

    # --- Settings for our test run ---
    SUBREDDIT  = "space"           # Which subreddit to scrape
    LIMIT      = 5                # How many posts to grab
    TIMEFRAME  = "week"            # Top posts from the past week
    OUTPUT_FILE = "space_posts.json"  # Where to save the results

    # Step 1: Go fetch the posts from Reddit
    posts = fetch_top_posts(subreddit=SUBREDDIT, limit=LIMIT, timeframe=TIMEFRAME)

    # Step 2: Save them to a JSON file on disk
    save_posts(posts, OUTPUT_FILE)

    # Step 3: Print a quick summary so we can see what we got
    print_summary(posts)

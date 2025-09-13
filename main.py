import streamlit as st
import streamlit_authenticator as stauth
import sqlite3
import hashlib
import uuid
from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime

# For demo, tweets generation is mocked.
# Replace this with your real Google Gemini code.
def generate_tweets(number, topic, language):
    tweets = [f"Key point {i+1} for {topic} in {language}\nTweet content #{i+1}" for i in range(number)]
    return "\n\n".join(tweets)

# --- Database setup ---
conn = sqlite3.connect("tweets_users.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    password_hash TEXT NOT NULL
)""")

c.execute("""CREATE TABLE IF NOT EXISTS tweet_histories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    topic TEXT NOT NULL,
    language TEXT NOT NULL,
    number INTEGER NOT NULL,
    tweets TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)""")

c.execute("""CREATE TABLE IF NOT EXISTS tweet_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_history_id INTEGER NOT NULL,
    rater_user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,  -- 1 for like, -1 for dislike
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tweet_history_id, rater_user_id),
    FOREIGN KEY (tweet_history_id) REFERENCES tweet_histories(id),
    FOREIGN KEY (rater_user_id) REFERENCES users(id)
)""")

conn.commit()

# --- Helper functions ---

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def add_user(username, name, password):
    try:
        c.execute("INSERT INTO users (username, name, password_hash) VALUES (?, ?, ?)",
                  (username, name, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    if not result:
        return False
    return verify_password(password, result[0])

def get_user_id(username):
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    res = c.fetchone()
    if res:
        return res[0]
    return None

def save_tweet_history(user_id, topic, language, number, tweets):
    c.execute("""INSERT INTO tweet_histories (user_id, topic, language, number, tweets) 
                 VALUES (?, ?, ?, ?, ?)""",
                 (user_id, topic, language, number, tweets))
    conn.commit()
    return c.lastrowid

def get_tweet_histories_by_user(user_id):
    c.execute("""SELECT id, topic, language, number, tweets, created_at 
                 FROM tweet_histories WHERE user_id = ? ORDER BY created_at DESC""", (user_id,))
    return c.fetchall()

def get_tweet_history_by_id(tweet_history_id):
    c.execute("""SELECT tweet_histories.id, users.username, tweet_histories.topic, tweet_histories.language,
                        tweet_histories.number, tweet_histories.tweets, tweet_histories.created_at
                 FROM tweet_histories JOIN users ON tweet_histories.user_id = users.id
                 WHERE tweet_histories.id = ?""", (tweet_history_id,))
    return c.fetchone()

def has_user_rated(tweet_history_id, user_id):
    c.execute("""SELECT rating FROM tweet_ratings WHERE tweet_history_id = ? AND rater_user_id = ?""",
              (tweet_history_id, user_id))
    return c.fetchone()

def add_rating(tweet_history_id, user_id, rating):
    try:
        c.execute("""INSERT INTO tweet_ratings (tweet_history_id, rater_user_id, rating) VALUES (?, ?, ?)""",
                  (tweet_history_id, user_id, rating))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_rating_counts(tweet_history_id):
    c.execute("""SELECT 
                    SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) as likes,
                    SUM(CASE WHEN rating=-1 THEN 1 ELSE 0 END) as dislikes
                 FROM tweet_ratings WHERE tweet_history_id = ?""", (tweet_history_id,))
    res = c.fetchone()
    return res if res != (None, None) else (0,0)

# --- User Authentication setup ---

# For demo purposes: predefined users
# In production, use the DB and a sign-up flow instead
usernames = ["alice", "bob"]
names = ["Alice", "Bob"]
passwords = ["passalice", "passbob"]  # plaintext for demo, hash before storing in production

# This creates a hashed credential dictionary for streamlit-authenticator
hashed_passwords = [hash_password(p) for p in passwords]
credentials = {
    "usernames": {
        usernames[i]: {
            "name": names[i],
            "password": hashed_passwords[i]
        } for i in range(len(usernames))
    }
}

# streamlit-authenticator uses hashed passwords
authenticator = stauth.Authenticate(
    credentials,
    "tweet_generator_cookie", "tweet_generator_key", cookie_expiry_days=1
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status:
    st.sidebar.write(f"Welcome, {name}! ([logout](#))")
    authenticator.logout("Logout", "sidebar")

    user_id = get_user_id(username)
    if user_id is None:
        # Add demo user to DB if not exists - in real app handle signups properly
        add_user(username, name, passwords[usernames.index(username)])
        user_id = get_user_id(username)

    query_params = st.experimental_get_query_params()
    shared_tid = query_params.get("tweet_id", [None])[0]

    if shared_tid:
        # Show shared tweet history page (view and rate)
        tweet_data = get_tweet_history_by_id(shared_tid)
        if tweet_data:
            (tid, owner_username, topic, language, number, tweets, created_at) = tweet_data
            st.title(f"Shared Tweets by {owner_username}")
            st.markdown(f"**Topic:** {topic}")
            st.markdown(f"**Language:** {language}")
            st.markdown(f"**Number of Tweets:** {number}")
            st.markdown(f"**Generated At:** {created_at}")
            st.text(tweets)

            # Like/dislike from current user if not owner
            if username != owner_username:
                rated = has_user_rated(tid, user_id)
                likes, dislikes = get_rating_counts(tid)

                col1, col2, col3 = st.columns([1,1,1])
                with col1:
                    if rated:
                        st.button("👍 Like", disabled=True, key=f"like_{tid}")
                    else:
                        if st.button("👍 Like", key=f"like_{tid}"):
                            add_rating(tid, user_id, 1)
                            st.experimental_rerun()
                with col2:
                    if rated:
                        st.button("👎 Dislike", disabled=True, key=f"dislike_{tid}")
                    else:
                        if st.button("👎 Dislike", key=f"dislike_{tid}"):
                            add_rating(tid, user_id, -1)
                            st.experimental_rerun()
                with col3:
                    st.write(f"Likes: {likes}  Dislikes: {dislikes}")
            else:
                st.info("This is your own tweet history.")
        else:
            st.error("Invalid tweet history link: not found.")
    else:
        # Logged-in user main UI - generate tweets and see own history
        st.title("Tweet Generator - SAMVED")
        st.subheader("Generate tweets using Generative AI")

        topic = st.text_input("Topic")
        number = st.number_input("Number of tweets", min_value=1, max_value=10, value=1)
        language_selected = st.selectbox("Language", options=[
            "English", "Hindi", "French", "Spanish", "German", "Bengali", "Tamil", "Telugu"
        ])

        if st.button("Generate") and topic.strip():
            # Replace with your Google Gemini call, here mocked
            tweets = generate_tweets(number, topic, language_selected)
            st.text_area("Generated Tweets with Key Points", tweets, height=300)

            # Save to DB
            tweet_id = save_tweet_history(user_id, topic, language_selected, number, tweets)

            # Generate share link
            base_url = st.request.url if hasattr(st, 'request') else 'http://localhost:8501'
            share_link = f"{base_url}?tweet_id={tweet_id}"
            st.markdown(f"Share these tweets: [{share_link}]({share_link})")

        # Show user’s tweet history with links and rating counts
        st.markdown("## Your Tweet Histories")
        histories = get_tweet_histories_by_user(user_id)
        if histories:
            for tid, topic, language, number, tweets, created_at in histories:
                st.markdown(f"**Topic:** {topic} | **Language:** {language} | **Count:** {number} | **Date:** {created_at}")
                st.text(tweets)
                likes, dislikes = get_rating_counts(tid)
                share_link = f"?tweet_id={tid}"
                st.markdown(f"[View & Share Link]({share_link})  |  Likes: {likes}  Dislikes: {dislikes}")
                st.markdown("---")
        else:
            st.info("No tweet histories found. Generate some!")

elif authentication_status is False:
    st.error("Username/password is incorrect")
else:
    st.info("Please enter your username and password")

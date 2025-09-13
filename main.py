import streamlit as st
import os
import uuid
import sqlite3
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import PromptTemplate

# Setup DB connection
conn = sqlite3.connect('tweet_history.db', check_same_thread=False)
c = conn.cursor()

# Create tables if not exists
c.execute('''
CREATE TABLE IF NOT EXISTS tweets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    number INTEGER,
    language TEXT,
    tweets TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id INTEGER,
    user_id TEXT,
    rating INTEGER,
    UNIQUE(tweet_id, user_id)
)
''')
conn.commit()

# Setup GPT and Prompt
os.environ['GOOGLE_API_KEY'] = st.secrets['GOOGLE_API_KEY']

LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Bengali": "bn",
    "Tamil": "ta",
    "Telugu": "te"
}

tweet_template = "Generate {number} tweets on '{topic}' in {language}."
tweet_prompt = PromptTemplate(template=tweet_template, input_variables=['number', 'topic', 'language'])
gemini_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
tweet_chain = tweet_prompt | gemini_model

st.header("Tweet Generator - SAMVED")
st.subheader("Generate tweets using Generative AI")

if 'user_id' not in st.session_state:
    st.session_state['user_id'] = str(uuid.uuid4())

topic = st.text_input("Topic")
number = st.number_input("Number of tweets", min_value=1, max_value=10, value=1)
language = st.selectbox("Language", options=list(LANGUAGES.keys()))

if st.button("Generate") and topic.strip():
    response = tweet_chain.invoke({"number": number, "topic": topic, "language": language})
    tweets_content = response.content

    # Save to DB
    c.execute('INSERT INTO tweets (topic, number, language, tweets) VALUES (?, ?, ?, ?)',
              (topic, number, language, tweets_content))
    conn.commit()
    st.success("Tweets generated and saved!")

# Fetch all tweet histories from DB
c.execute('SELECT id, topic, number, language, tweets FROM tweets ORDER BY id DESC')
all_tweets = c.fetchall()

st.markdown("### Global Tweet History (All Users)")
for tweet_id, topic, number, language, tweets in all_tweets:
    st.markdown(f"**Topic:** {topic} | Language: {language} | Count: {number}")
    st.text(tweets)

    # Fetch ratings for this tweet
    c.execute('SELECT COUNT(*) FROM ratings WHERE tweet_id = ? AND rating=1', (tweet_id,))
    likes = c.fetchone()[0] or 0

    c.execute('SELECT COUNT(*) FROM ratings WHERE tweet_id = ? AND rating=-1', (tweet_id,))
    dislikes = c.fetchone()[0] or 0
    
    # Check if current user has already rated this tweet
    c.execute('SELECT rating FROM ratings WHERE tweet_id = ? AND user_id = ?',
              (tweet_id, st.session_state['user_id']))
    user_rating = c.fetchone()
    rated = user_rating is not None

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if rated:
            st.button("👍 Like", disabled=True, key=f"like_{tweet_id}")
        else:
            if st.button("👍 Like", key=f"like_{tweet_id}"):
                try:
                    c.execute('INSERT INTO ratings (tweet_id, user_id, rating) VALUES (?, ?, 1)',
                              (tweet_id, st.session_state['user_id']))
                    conn.commit()
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    pass
    with col2:
        if rated:
            st.button("👎 Dislike", disabled=True, key=f"dislike_{tweet_id}")
        else:
            if st.button("👎 Dislike", key=f"dislike_{tweet_id}"):
                try:
                    c.execute('INSERT INTO ratings (tweet_id, user_id, rating) VALUES (?, ?, -1)',
                              (tweet_id, st.session_state['user_id']))
                    conn.commit()
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    pass
    with col3:
        st.write(f"Likes: {likes}  Dislikes: {dislikes}")

    st.markdown("---")

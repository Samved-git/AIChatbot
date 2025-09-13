from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import PromptTemplate
import streamlit as st
import os
import uuid

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

tweet_template = (
    "Generate {number} tweets on '{topic}' in {language}. "
    "For each tweet, also list key points or the main idea before the tweet."
)
tweet_prompt = PromptTemplate(
    template=tweet_template,
    input_variables=['number', 'topic', 'language']
)

gemini_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
tweet_chain = tweet_prompt | gemini_model

st.header("Tweet Generator - SAMVED")
st.subheader("Generate tweets using Generative AI")

# Global state dictionary - shared for all users while app runs
if 'global_history' not in st.session_state:
    st.session_state['global_history'] = {
        "tweet_history": [],
        "likes": [],
        "dislikes": [],
        "rated": {}  # key: (user_session_id, tweet_idx), value: "like"/"dislike"
    }

history_store = st.session_state['global_history']

if 'user_session_id' not in st.session_state:
    st.session_state['user_session_id'] = str(uuid.uuid4())

while len(history_store['likes']) < len(history_store['tweet_history']):
    history_store['likes'].append(0)
while len(history_store['dislikes']) < len(history_store['tweet_history']):
    history_store['dislikes'].append(0)

topic = st.text_input("Topic")
number = st.number_input("Number of tweets", min_value=1, max_value=10, value=1, step=1)
language_selected = st.selectbox("Language", options=list(LANGUAGES.keys()))

if st.button("Generate") and topic.strip():
    tweets_output = tweet_chain.invoke({
        "number": number,
        "topic": topic,
        "language": language_selected
    })
    history_store['tweet_history'].append({
        "topic": topic,
        "number": number,
        "language": language_selected,
        "tweets": tweets_output.content
    })
    history_store['likes'].append(0)
    history_store['dislikes'].append(0)
    st.experimental_rerun()

if history_store['tweet_history']:
    st.markdown("### Global Tweet History (All Users)")
    for i, entry in enumerate(reversed(history_store['tweet_history'])):
        idx = len(history_store['tweet_history']) - 1 - i
        st.markdown(
            f"**{i + 1}. Topic:** {entry['topic']} | "
            f"**Language:** {entry['language']} | "
            f"**Tweets Count:** {entry['number']}"
        )
        st.write(entry['tweets'])
        user_vote_key = (st.session_state['user_session_id'], idx)
        has_rated = user_vote_key in history_store['rated']

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if has_rated:
                st.button("👍 Like", key=f"like_{idx}", disabled=True)
            else:
                if st.button("👍 Like", key=f"like_{idx}"):
                    history_store['likes'][idx] += 1
                    history_store['rated'][user_vote_key] = "like"
                    st.experimental_rerun()
        with col2:
            if has_rated:
                st.button("👎 Dislike", key=f"dislike_{idx}", disabled=True)
            else:
                if st.button("👎 Dislike", key=f"dislike_{idx}"):
                    history_store['dislikes'][idx] += 1
                    history_store['rated'][user_vote_key] = "dislike"
                    st.experimental_rerun()
        with col3:
            st.write(
                f"Likes: {history_store['likes'][idx]}  "
                f"Dislikes: {history_store['dislikes'][idx]}"
            )
        st.markdown("---")

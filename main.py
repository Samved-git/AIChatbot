from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import PromptTemplate
import streamlit as st
import os

os.environ['GOOGLE_API_KEY'] = st.secrets['GOOGLE_API_KEY']

# Supported languages dictionary
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

# Prompt template to generate tweets with key points
tweet_template = (
    "Generate {number} tweets on '{topic}' in {language}. "
    "For each tweet, also list key points or the main idea before the tweet."
)
tweet_prompt = PromptTemplate(
    template=tweet_template,
    input_variables=['number', 'topic', 'language']
)

# Initialize Google's Gemini model
gemini_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
tweet_chain = tweet_prompt | gemini_model

st.header("Tweet Generator - SAMVED")
st.subheader("Generate tweets using Generative AI")

# Initialize session state variables if not present
if 'tweet_history' not in st.session_state:
    st.session_state['tweet_history'] = []
if 'likes' not in st.session_state:
    st.session_state['likes'] = []
if 'dislikes' not in st.session_state:
    st.session_state['dislikes'] = []

topic = st.text_input("Topic")
number = st.number_input("Number of tweets", min_value=1, max_value=10, value=1, step=1)
language_selected = st.selectbox("Language", options=list(LANGUAGES.keys()))

if st.button("Generate") and topic.strip():
    # Generate tweets with the chain
    tweets_output = tweet_chain.invoke({
        "number": number,
        "topic": topic,
        "language": language_selected
    })

    # Store generation and initialize likes/dislikes for this entry
    st.session_state['tweet_history'].append({
        "topic": topic,
        "number": number,
        "language": language_selected,
        "tweets": tweets_output.content
    })
    st.session_state['likes'].append(0)
    st.session_state['dislikes'].append(0)

# Display tweet history with Like and Dislike buttons
if st.session_state['tweet_history']:
    st.markdown("### Tweet History")
    # Display in reverse order, newest first
    for i, entry in enumerate(reversed(st.session_state['tweet_history'])):
        idx = len(st.session_state['tweet_history']) - 1 - i  # original index in session state
        
        st.markdown(
            f"**{i + 1}. Topic:** {entry['topic']} | "
            f"**Language:** {entry['language']} | "
            f"**Tweets Count:** {entry['number']}"
        )
        st.write(entry['tweets'])

        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button(f"👍 Like", key=f"like_{idx}"):
                st.session_state['likes'][idx] += 1
        with col2:
            if st.button(f"👎 Dislike", key=f"dislike_{idx}"):
                st.session_state['dislikes'][idx] += 1
        with col3:
            st.write(f"Likes: {st.session_state['likes'][idx]}  Dislikes: {st.session_state['dislikes'][idx]}")
        
        st.markdown("---")

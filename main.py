from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import PromptTemplate
import streamlit as st
import os

os.environ['GOOGLE_API_KEY'] = st.secrets['GOOGLE_API_KEY']

# Define supported languages
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

# Create prompt template to generate tweets along with key points
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

# LLM chain for tweet generation
tweet_chain = tweet_prompt | gemini_model

st.header("Tweet Generator - SAMVED")
st.subheader("Generate tweets using Generative AI")

topic = st.text_input("Topic")
number = st.number_input("Number of tweets", min_value=1, max_value=10, value=1, step=1)
language_selected = st.selectbox("Language", options=list(LANGUAGES.keys()))
language_code = LANGUAGES[language_selected]

if st.button("Generate"):
    tweets_output = tweet_chain.invoke({
        "number": number,
        "topic": topic,
        "language": language_selected
    })
    # Split output into individual tweets and key points if structured that way
    # This assumes model returns tweets in desired structure, otherwise parse as needed
    st.write(tweets_output.content)

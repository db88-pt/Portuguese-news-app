import streamlit as st
import feedparser
from google import genai
from datetime import datetime
import time
import json

# Mobile UI styling cleanup
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# Initialize Gemini Client via Streamlit Secrets
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Fetch RSS feed and initialize Session State memory for dismissed items
@st.cache_data(ttl=3600)
def fetch_feed():
    return feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")

feed = fetch_feed()

if "dismissed" not in st.session_state:
    st.session_state.dismissed = []

# Sidebar control: CEFR Level selector only (Mode switcher removed)
selected_level = st.sidebar.selectbox("Nível CEFR", ["A1", "A2", "B1", "B2"])

# Filter out dismissed articles and grab only the single next article
active_articles = [
    art for art in feed.entries 
    if art.link not in st.session_state.dismissed
]

if not active_articles:
    st.write("Sem mais artigos disponíveis no momento.")
    display_article = False
else:
    current_article = active_articles[0]  # Always grab the top fresh article
    display_article = True

# Render Current Article & Action Buttons
if display_article and current_article:
    st.subheader("📰 Leitor de Notícias")
    
    act_col1, act_col2 = st.columns(2)
    with act_col1:
        if st.button("❌ Não tenho interesse"):
            st.session_state.dismissed.append(current_article.link)
            st.rerun()
    with act_col2:
        if st.button("✅ Concluído"):
            st.session_state.dismissed.append(current_article.link)
            st.rerun()

    # Dynamic Prompt incorporating your exact instructions
    prompt = f"""
    You are a European Portuguese language teacher.
    Rewrite, adapt and translate the following English news summary into European Portuguese suitable for a {selected_level} CEFR learner.
    With all levels, heavily adapt and change the article if needed - Portuguese language practice is more important than copying the article exactly
    Output ONLY the structured sections requested below. DO NOT include any introductory conversational text (e.g., "Olá! Here is an adapted version...").
    Translate from English into European Portuguese (pt-PT). Maintain European Portuguese spelling, grammar, and phrasing (pt-PT).
    Keep the original facts and context intact.
    Adjust vocabulary, sentence complexity and article length and structure to broadly match CEFR level {selected_level}.
    Output the rewritten Portuguese text, but add brief outro notes if this is suitable.

    Instructions for A1 Level:
    - Keep sentences extremely short (max 5-8 words per sentence)
    - Use present tense verbs where possible (e.g., use 'há' instead of 'houve').
    - Use basic, everyday European Portuguese vocabulary suitable for complete beginners.

    Instructions for A2 Level:
    - Keep sentences short (max 30 words per sentence)
    - Use present tense verbs where possible (e.g., use 'há' instead of 'houve').
    - Use basic, everyday European Portuguese vocabulary suitable for beginners.
    - Provide clear contextual vocabulary notes for key terms.

    Instructions for B1 Level:
    - Use moderate sentence complexity, everyday idiomatic expressions, and mixed tenses.
    - Provide helpful vocabulary notes for key intermediate terms.

    Instructions for B2 Level:
    - Use natural, fluid European Portuguese syntax with upper-intermediate sentence structures.
    - Provide advanced vocabulary notes for nuanced phrasing.

    Original Title: {current_article.title}
    Original Text: {current_article.summary}
    """

    max_retries = 3
    response = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt
            )
            break  # Success! Exit the loop immediately.
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                time.sleep(2)  # Transient error — wait, then let the loop try again
            elif "503" in str(e):
                # Last attempt, still failing
                st.error(f"Erro ao carregar tradução após tentativas: {e}")
                break
            else:
                # Not a 503 — retrying won't help, stop now
                st.error(f"Erro ao carregar tradução: {e}")
                break

    if response and hasattr(response, 'text'):
        st.markdown(response.text)
        
        import streamlit.components.v1 as components

        speech_html = f"""
        <div style="margin-top: 10px; margin-bottom: 10px; display: flex; gap: 8px;">
            <button onclick="playSpeech()" style="padding: 6px 12px; background-color: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">
                ▶️ Ouvir
            </button>
            <button onclick="pauseSpeech()" style="padding: 6px 12px; background-color: #e65c00; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">
                ⏸️ Pausa
            </button>
            <button onclick="stopSpeech()" style="padding: 6px 12px; background-color: #cc0000; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 13px;">
                ⏹️ Parar
            </button>
        </div>

        <script>
        let utterance = null;

        function cleanText(rawText) {{
            let storyOnly = rawText.split(/(Vocabulário|Notas|Vocabulary|Notes)/i)[0];
            return storyOnly.replace(/[#*_-]/g, '').trim();
        }}

        function playSpeech() {{
            if (window.speechSynthesis.paused && utterance) {{
                window.speechSynthesis.resume();
                return;
            }}
            window.speechSynthesis.cancel();
            const text = cleanText({json.dumps(response.text)});
            utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'pt-PT';
            window.speechSynthesis.speak(utterance);
        }}

        function pauseSpeech() {{
            if (window.speechSynthesis.speaking) {{
                window.speechSynthesis.pause();
            }}
        }}

        function stopSpeech() {{
            window.speechSynthesis.cancel();
        }}
        </script>
        """
        components.html(speech_html, height=60)

    st.markdown(f"[Ler artigo completo na source]({current_article.link})")
    

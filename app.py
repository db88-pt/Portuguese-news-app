import streamlit as st
import feedparser
from google import genai
from datetime import datetime, timedelta

# Mobile UI styling cleanup
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

# Initialize Gemini Client via Streamlit Secrets
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# Fetch RSS feed and initialize Session State memory
feed = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")

if "dismissed" not in st.session_state:
    st.session_state.dismissed = []

if "read_later" not in st.session_state:
    st.session_state.read_later = []

# Cleanup 7+ day old items from "Read Later"
now = datetime.now()
st.session_state.read_later = [
    item for item in st.session_state.read_later 
    if now - item[1] < timedelta(days=7)
]

# Filter out dismissed articles from the main feed stream
active_articles = [
    art for art in feed.entries 
    if art.link not in st.session_state.dismissed
][:5]

# Sidebar controls: Mode switcher and CEFR Level selector
app_mode = st.sidebar.radio("Modo de Leitura", ["Feed Principal", "Ler Mais Tarde"])
selected_level = st.sidebar.selectbox("Nível CEFR", ["A1", "A2", "B1", "B2"])

# Handle "Read Later" view
if app_mode == "Ler Mais Tarde":
    st.subheader("📚 Artigos Guardados (7 dias máx)")
    if not st.session_state.read_later:
        st.info("Ainda não guardaste nenhum artigo.")
    else:
        saved_articles = [item[0] for item in st.session_state.read_later]
        if "saved_index" not in st.session_state:
            st.session_state.saved_index = 0
        
        st.session_state.saved_index = min(st.session_state.saved_index, len(saved_articles) - 1)
        current_article = saved_articles[st.session_state.saved_index]
        
        st.write(f"Artigo {st.session_state.saved_index + 1} de {len(saved_articles)}")
        if st.button("Próximo guardado ➡️") and st.session_state.saved_index < len(saved_articles) - 1:
            st.session_state.saved_index += 1
            st.rerun()
            
        display_article = True
else:
    # Handle Main Feed view
    if "article_index" not in st.session_state:
        st.session_state.article_index = 0
        
    st.session_state.article_index = min(st.session_state.article_index, max(0, len(active_articles) - 1))
    
    if not active_articles:
        st.write("Sem mais artigos disponíveis no momento.")
        display_article = False
    else:
        current_article = active_articles[st.session_state.article_index]
        display_article = True
        
        # Navigation controls
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Anterior") and st.session_state.article_index > 0:
                st.session_state.article_index -= 1
                st.rerun()
        with col2:
            st.write(f"**{st.session_state.article_index + 1} / {len(active_articles)}**")
        with col3:
            if st.button("Próximo ➡️") and st.session_state.article_index < len(active_articles) - 1:
                st.session_state.article_index += 1
                st.rerun()

# Render Current Article & Action Buttons
if display_article and current_article:
    st.divider()
    
    act_col1, act_col2 = st.columns(2)
    with act_col1:
        if st.button("❌ Não tenho interesse"):
            st.session_state.dismissed.append(current_article.link)
            if app_mode == "Feed Principal":
                st.session_state.article_index = max(0, st.session_state.article_index - 1)
                st.rerun()
    with act_col2:
        if app_mode == "Feed Principal":
            if st.button("📌 Ler mais tarde"):
                st.session_state.read_later.append((current_article, datetime.now()))
                st.success("Guardado!")
                st.rerun()

    # Dynamic Prompt incorporating your exact instructions
    prompt = f"""
    You are a European Portuguese language teacher.
    Rewrite, adapt and translate the following English news summary into European Portuguese suitable for a {selected_level} CEFR learner.
    With all levels, heavily adapt and change the article if needed - Portuguese language practice is more important than copying the article exactly 

    Instructions for A1 Level:
    - Output ONLY the structured sections requested below. DO NOT include any introductory conversational text (e.g., "Olá! Here is an adapted version...").
    - Keep sentences extremely short (max 5-8 words per sentence)
    - Use present tense verbs where possible (e.g., use 'há' instead of 'houve').
    - Use basic, everyday European Portuguese vocabulary suitable for complete beginners.

    Instructions for A2 Level:
    - Output ONLY the structured sections requested below. DO NOT include any introductory conversational text (e.g., "Olá! Here is an adapted version...").
    - Keep sentences short (max 30 words per sentence)
    - Use present tense verbs where possible (e.g., use 'há' instead of 'houve').
    - Use basic, everyday European Portuguese vocabulary suitable for beginners.
    - Provide clear contextual vocabulary notes for key terms.

    Instructions for B1 Level:
    - Output ONLY the structured sections requested. DO NOT include introductory conversational text.
    - Use moderate sentence complexity, everyday idiomatic expressions, and mixed tenses.
    - Provide helpful vocabulary notes for key intermediate terms.

    Instructions for B2 Level:
    - Output ONLY the structured sections requested. DO NOT include introductory conversational text.
    - Use natural, fluid European Portuguese syntax with upper-intermediate sentence structures.
    - Provide advanced vocabulary notes for nuanced phrasing.

    Rules:
    - Translate from English into European Portuguese (pt-PT). Maintain European Portuguese spelling, grammar, and phrasing (pt-PT).
    - Keep the original facts and context intact.
    - Adjust vocabulary, sentence complexity and article length and structure to broadly match CEFR level {selected_level}.
    - Output the rewritten Portuguese text, but add brief outro notes if this is suitable.

    Original Title: {current_article.title}
    Original Text: {current_article.summary}
    """

    import time

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
            time.sleep(2)  # Wait 2 seconds before trying again
        else:
            if attempt == max_retries - 1:
                st.error(f"Erro ao carregar tradução após tentativas: {e}")
            else:
                st.error(f"Erro ao carregar tradução: {e}")

   st.markdown(f"[Ler artigo completo na source]({current_article.link})")
    

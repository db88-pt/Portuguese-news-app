import streamlit as st
import feedparser
from google import genai

# Mobile page setup
st.set_page_config(page_title="Notícias em Português", page_icon="📰", layout="centered")

# Get API key securely from Streamlit Cloud secrets
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("Erro: A chave GEMINI_API_KEY não foi encontrada nos segredos do Streamlit.")
    st.stop()

# Initialize the Gemini Client
client = genai.Client(api_key=api_key)

st.write([m.name for m in client.models.list()])

st.title("Notícias em Português 📰")

# Sidebar preference controls
st.sidebar.header("Preferências")
category = st.sidebar.selectbox(
    "Escolha a fonte de notícias:",
    ["BBC - Principais Notícias", "BBC - Reino Unido", "BBC - Mundo", "The Guardian - Reino Unido", "The Guardian - Cultura"]
)

level = st.sidebar.select_slider(
    "Nível de Português:",
    options=["A1", "A2", "B1", "B2"],
    value="A2"
)

# RSS feeds from BBC News and The Guardian
RSS_FEEDS = {
    "BBC - Principais Notícias": "http://feeds.bbci.co.uk/news/rss.xml",
    "BBC - Reino Unido": "http://feeds.bbci.co.uk/news/uk/rss.xml",
    "BBC - Mundo": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "The Guardian - Reino Unido": "https://www.theguardian.com/uk/rss",
    "The Guardian - Cultura": "https://www.theguardian.com/culture/rss"
}
    

# Fetch and parse the selected feed
feed_url = RSS_FEEDS[category]
feed = feedparser.parse(feed_url)

if not feed.entries:
    st.info("Não foi possível carregar as notícias neste momento. Tente novamente mais tarde.")
else:
    for item in feed.entries[:5]: # Display top 5 articles
        st.subheader(item.title)
        
        summary = item.get("summary", "")
        
        if level == "Texto Original":
            st.write(summary)
        else:
            prompt = f"""
            You are a European Portuguese language teacher.
            Rewrite, adapt and translate the following English news summary into European Portuguese suitable for a {level} CEFR learner.
            
            Rules:
            - Translate from English into European Portuguese (pt-PT). Maintain European Portuguese spelling, grammar, and phrasing (pt-PT).
            - Keep the original facts and context intact.
            - Adjust vocabulary, sentence complexity and article length and structure to broadly match CEFR level {level}.
            - Output the rewritten Portuguese text, but add intro or outro notes if this is suitable.
            
            Summary:
            {summary}
            """
            
            with st.spinner("A adaptar o texto..."):
                try:
                    response = client.models.generate_content(
                        model='models/gemini-flash-latest',
                        contents=prompt
                    )
                    st.write(response.text)
                except Exception as e:
                    st.error("Erro ao adaptar com Gemini. A mostrar texto original:")
                    st.write(summary)
        
        st.markdown(f"[Ler artigo completo na RTP ↗]({item.link})")
        st.divider()
      

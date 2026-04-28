import os
import json
import re
import sys
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.tokenize import word_tokenize
import requests
from bs4 import BeautifulSoup

# Force UTF-8 encoding for stdout/stderr (needed for Windows)
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# Paths
DATA_PATH = os.path.join('data', 'news_data.json')
USERS_PATH = os.path.join('data', 'user_profiles.json')
TOPICS_OUTPUT_SBERT = os.path.join('data', 'topics_summary_sbert.txt')
TOPICS_OUTPUT_GMM   = os.path.join('data', 'topics_summary_gmm.txt')
VALIDATION_OUTPUT   = os.path.join('data', 'validation_sample.txt')
EVAL_OUTPUT         = os.path.join('data', 'evaluation_report.txt')

# Sources
LOCAL_SOURCES = [
    "Times of Malta", "MaltaToday", "The Shift News", 
    "Newsbook (EN)", "TVM News", "Lovin Malta", "MaltaDaily",
    "Malta Independent", "BusinessNow"
]

INTL_SOURCES = [
    "BBC World News", "BBC UK Politics", "Al Jazeera", "The Guardian World", 
    "Reuters Top", "FOX News", "CNN", "Breitbart", "Jacobin", "MSNBC",
    "BBC Tech", "Wired Tech", "The Guardian Culture", "BBC Business", "Yahoo Finance"
]

# Noise Filtering
TECH_NOISE = set([
    "javascript", "cookies", "enable", "disable", "extensions", 
    "browsers", "please", "continue", "loading", "browser", 
    "website", "experience", "accept", "policy", "updated", "details", "read",
    "blockers", "appeared", "interfere", "script", "blocking",
    "ads", "support", "content", "free", "journalism", "independent",
    "facebook", "twitter", "whatsapp", "instagram", "share", "comment",
    "related", "video", "photos", "photo", "image", "reporting", "reported",
    "source", "news", "sign", "email", "address", "subscribe", "newsletter",
    "rights", "reserved", "click", "here", "following", "advertisement",
    "mailchimp", "signup", "register", "join", "member", "membership",
    "latest", "stories", "sent", "inbox", "directly", "unsubscribe",
    "external", "link", "opens", "window", "edition", "advertising", "privacy", 
    "disclosures", "secured", "compare", "best", "terms", "conditions", "data", "protection",
    "said", "would", "could", "also", "time", "year",
    "years", "like", "says", "told", "first", "many", "much", "even",
    "http", "world", "people", "february", "last", "month", "post", "public", "state",
    "theguardian", "href", "strong", "reading", "image", "photo", "caption", "copyright",
    "guardian", "newsletter", "sign", "email", "subscription", "support", "contribution"
])

# Ensure NLTK data is ready
def setup_nltk():
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    nltk.download('wordnet', quiet=True)

EN_STOPWORDS = None

def get_stopwords():
    global EN_STOPWORDS
    if EN_STOPWORDS is None:
        setup_nltk()
        EN_STOPWORDS = set(stopwords.words('english')).union(TECH_NOISE)
    return EN_STOPWORDS

lemmatizer = WordNetLemmatizer()

def preprocess_text(text):
    """Deep NLP preprocessing: lower, tokenize, POS filter (Nouns/Adjs), lemmatize."""
    if not text:
        return []
    
    stop_words = get_stopwords()
    
    # 1. Clean basic noise
    text = text.lower()
    text = re.sub(r'[^a-z\s]', ' ', text)
    
    # 2. Tokenize
    tokens = word_tokenize(text)
    
    # 3. Filter short words & basic stopwords
    tokens = [t for t in tokens if len(t) > 3 and t not in stop_words]
    
    if not tokens:
        return []

    # 4. POS Tagging
    tagged = pos_tag(tokens)
    
    # 5. Keep ONLY Nouns and Adjectives
    allowed_tags = ['NN', 'NNS', 'JJ', 'JJR', 'JJS']
    filtered_tokens = []
    
    for word, tag in tagged:
        if tag in allowed_tags:
            # 6. Lemmatize
            base_form = lemmatizer.lemmatize(word)
            if base_form not in stop_words:
                filtered_tokens.append(base_form)
                
    return filtered_tokens

def clean_html(text):
    """Remove HTML tags and decode entities."""
    if not text:
        return ""
    text = re.sub(r'<.*?>', ' ', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&apos;', "'").replace('&#039;', "'").replace('&nbsp;', " ")
    return " ".join(text.split()).strip()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_full_text(url):
    """Attempt to fetch the full article text from the URL."""
    if not url or not url.startswith('http'):
        return ""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for script_or_style in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script_or_style.decompose()
            
        # Common content containers
        article_body = soup.find('article') or soup.find('div', class_=re.compile(r'content|article|post-body|entry-content|text-container', re.I))
        
        if article_body:
            paragraphs = article_body.find_all('p')
            content = " ".join([p.get_text() for p in paragraphs])
        else:
            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text() for p in paragraphs])
            
        return clean_html(content)
    except Exception:
        return ""

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from newspaper import Article
import nltk
from nltk import sent_tokenize, word_tokenize, pos_tag
nltk.download('all')
from collections import Counter
import json
import psycopg2
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = 'your_secret_key'

nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="dpg-cnmnd8gcmk4c73aikuc0-a",
    database="newsdb_egtu",
    user="yash",
    password="chdGWMaJ1yfG7mUHzyN58YzOaHNFhLXg"
)
cur = conn.cursor()

def create_table():
    # Create a table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_analysis (
            id SERIAL PRIMARY KEY,
            url VARCHAR(255),
            title VARCHAR(255),
            content TEXT,
            num_sentences INTEGER,
            num_words INTEGER,
            pos_counts JSON
        )
    """)
    conn.commit()

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # For simplicity, you can use a hardcoded username and password here
        if request.form['username'] == 'admin' and request.form['password'] == '123':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

# Protected route (requires authentication)
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'logged_in' in session and session['logged_in']:
        # Fetch past analyses from the database
        cur.execute("SELECT * FROM news_analysis")
        past_analyses = cur.fetchall()
        return render_template('admin_dashboard.html', past_analyses=past_analyses)
    else:
        return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/result', methods=['GET', 'POST'])
def result():
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            title, content, images = fetch_news_content(url)

            # Check if the fetch was successful
            if title is None or content is None or images is None:
                flash("Error fetching content. Please check the URL and try again.", 'error')
            else:
                num_sentences, num_words, pos_counts = analyze_text(content)
                pos_counts_json = json.dumps(pos_counts)

                create_table()
                cur.execute("""
                    INSERT INTO news_analysis (url, title, content, num_sentences, num_words, pos_counts)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (url, title, content, num_sentences, num_words, pos_counts_json))

                conn.commit()

                # Render the result template with the analysis details
                return render_template('result.html', title=title, content=content,
                                       num_sentences=num_sentences, num_words=num_words, pos_counts=pos_counts)

    # flash("Invalid request.", 'error')
    # return redirect(url_for('admin_dashboard'))

def fetch_news_content(url):
    try:
        # Fetch HTML content using newspaper library
        article = Article(url)
        article.download()
        article.parse()

        title = article.title if article.title else 'Title not found'
        text = article.text if article.text else 'Content not found'
        images = article.images if article.images else []

        return title, text, images
    except Exception as e:
        print(f"Error fetching content: {e}")
        return None, None, None

def analyze_text(text):
    # Tokenize text into sentences
    sentences = sent_tokenize(text)
    
    # Count number of sentences and words
    num_sentences = len(sentences)
    words = word_tokenize(text)
    num_words = len(words)
    
    # Tag words with POS
    pos_tags = pos_tag(words,  tagset='universal')
    
    # Count POS tags
    pos_counts = Counter(tag for word, tag in pos_tags)
    
    return num_sentences, num_words, pos_counts


usernames = ["atmabodha",""]
@app.route('/login/github')
def github_login():
    github = oauth.create_client('github')
    redirect_uri = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/authorize')
def github_authorize():
    try:
        github = oauth.create_client('github')
        token = github.authorize_access_token()
        session['github_token'] = token
        resp = github.get('user').json()
        print(f"\n{resp}\n")
        username = resp.get('login')
        if username in usernames:
            cur = conn.cursor()
            cur.execute("SELECT * FROM news_analysis")
            data = cur.fetchall()
            conn.close()
            return render_template("admin_dashboard.html", data=data)
        else:
            return redirect(url_for('home'))
    except:
        return redirect(url_for('home'))

@app.route('/logout/github')
def github_logout():
    session.clear()
    print("logout")
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
    cur.close()
    conn.close()

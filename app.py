from flask import Flask, render_template, request
import pandas as pd
import random
from flask_sqlalchemy import SQLAlchemy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "alskdjfwoeieiurlskdjfslkdjf"

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root:@localhost/ecom"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load trending products
try:
    trending_products = pd.read_csv("models/trending_products.csv")
except FileNotFoundError:
    trending_products = pd.DataFrame()

# Load training data
try:
    train_data = pd.read_csv("models/clean_data.csv")
    train_data['Tags'] = train_data['Tags'].fillna('')
except FileNotFoundError:
    train_data = pd.DataFrame(columns=['Name', 'Tags', 'ReviewCount', 'Brand', 'ImageURL', 'Rating'])

# Database model
class Signup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(255), nullable=False)

# Helper function
def truncate(text, length):
    return text[:length] + "..." if len(text) > length else text

def content_based_recommendations(train_data, item_name, top_n=10):
    if item_name not in train_data['Name'].values:
        return pd.DataFrame()
    
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix_content = tfidf_vectorizer.fit_transform(train_data['Tags'])
    cosine_similarities_content = cosine_similarity(tfidf_matrix_content, tfidf_matrix_content)

    item_index = train_data[train_data['Name'] == item_name].index[0]
    similar_items = sorted(
        list(enumerate(cosine_similarities_content[item_index])),
        key=lambda x: x[1],
        reverse=True
    )[1:top_n + 1]
    recommended_item_indices = [x[0] for x in similar_items]

    return train_data.iloc[recommended_item_indices][['Name', 'ReviewCount', 'Brand', 'ImageURL', 'Rating']]

app.jinja_env.filters['truncate'] = truncate

# Static image URLs
random_image_urls = [f"static/img/img_{i}.png" for i in range(1, 9)]

# Routes
@app.route("/")
@app.route("/index")
def index():
    random_product_image_urls = [random.choice(random_image_urls) for _ in range(len(trending_products))]
    price = [40, 50, 60, 70, 100, 122, 106, 50, 30, 50]
    return render_template('index.html',
                           trending_products=trending_products.head(8),
                           truncate=truncate,
                           random_product_image_urls=random_product_image_urls,
                           random_price=random.choice(price))

@app.route("/main")
def main():
    return render_template('main.html', content_based_rec=pd.DataFrame(), message="Search for products to get recommendations.", random_price=[])

@app.route("/signup", methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        new_signup = Signup(username=username, email=email, password=password)
        db.session.add(new_signup)
        db.session.commit()

        random_product_image_urls = [random.choice(random_image_urls) for _ in range(len(trending_products))]
        return render_template('index.html', trending_products=trending_products.head(8), truncate=truncate,
                               random_product_image_urls=random_product_image_urls,
                               random_price=random.randint(30, 120),
                               signup_message='User signed up successfully!')
    return render_template('signup.html')

@app.route('/signin', methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        username = request.form['signinUsername']
        password = request.form['signinPassword']

        user = Signup.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            random_product_image_urls = [random.choice(random_image_urls) for _ in range(len(trending_products))]
            return render_template('index.html', trending_products=trending_products.head(8), truncate=truncate,
                                   random_product_image_urls=random_product_image_urls,
                                   random_price=random.randint(30, 120),
                                   signup_message='User signed in successfully!')
        else:
            return render_template('signin.html', error='Invalid username or password.')

    return render_template('signin.html')

@app.route("/recommendations", methods=['POST'])
def recommendations():
    prod = request.form.get('prod')
    nbr_raw = request.form.get('nbr', '').strip()
    
    try:
        nbr = int(nbr_raw) if nbr_raw else 5
    except ValueError:
        nbr = 5

    content_based_rec = content_based_recommendations(train_data, prod, top_n=nbr)

    if content_based_rec.empty:
        return render_template('main.html', content_based_rec=pd.DataFrame(), message="No recommendations available for this product.", random_price=[])

    random_product_image_urls = [random.choice(random_image_urls) for _ in range(len(content_based_rec))]
    random_prices = [random.randint(30, 120) for _ in range(len(content_based_rec))]
    return render_template('main.html',
                           content_based_rec=content_based_rec,
                           truncate=truncate,
                           random_product_image_urls=random_product_image_urls,
                           random_price=random_prices,
                           message=None)

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, jsonify
# import psycopg
#import os

app = Flask(__name__)



# url =  os.environ["DATABASE_URL"]

# schema = """
# CREATE TABLE IF NOT EXISTS profiles (
#     profile_id SERIAL PRIMARY KEY,
#     name VARCHAR(20) NOT NULL,
#     bio  VARCHAR(100) ,
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );

# """
# with psycopg.connect(url) as conn:
#         with conn.cursor() as cur:
#             cur.execute(schema)


@app.route("/")
@app.route("/signin")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/feeds")
def feeds():
    return render_template("feeds.html")

@app.route("/profile")
def feed():
    return render_template("profile.html")
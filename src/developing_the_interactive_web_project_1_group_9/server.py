from flask import Flask, render_template, request, jsonify
from . import database
import psycopg
import os

app = Flask(__name__)



url =  os.environ["DATABASE_URL"]



@app.route("/")
@app.route("/signin")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/feeds")
def feeds():
    posts = database.get_posts_with_usernames()
    return render_template("feeds.html", posts=posts)

@app.route("/profile")
def feed():
    return render_template("profile.html")

@app.route("/post/<int:post_id>")
def post_page(post_id):
    post = database.get_post(post_id)
    print(post)
    comments = database.get_comments(post_id)
    print(comments)
    return render_template("post.html", post=post, comments=comments)
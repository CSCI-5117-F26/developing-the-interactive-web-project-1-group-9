from flask import Flask, flash, render_template, request, g, Response, make_response, redirect, url_for
from auth0_server_python.auth_types import LogoutOptions
from developing_the_interactive_web_project_1_group_9.auth import init_auth0
from dotenv import load_dotenv
from developing_the_interactive_web_project_1_group_9.database import *
from developing_the_interactive_web_project_1_group_9.llm import *

# import psycopg
import os

app = Flask(__name__)
app.secret_key = os.getenv('AUTH0_SECRET')

load_dotenv()
# url =  os.environ["DATABASE_URL"]



@app.route("/")
async def index():
    return redirect(url_for('feeds'))

@app.route("/signin")
async def login():
    """Redirect to Auth0 login"""
    auth0 = init_auth0()
    response = make_response()
    store_options = {"request": request, "response": response}
    authorization_url = await auth0.start_interactive_login({}, store_options)
    response.status_code = 302
    response.headers["Location"] = authorization_url
    return response


@app.route('/callback')
async def callback():
    """Handle Auth0 callback after login"""
    auth0 = init_auth0()
    response = make_response()
    store_options = {"request": request, "response": response}
    try:
        result = await auth0.complete_interactive_login(str(request.url), store_options)
        user = result["state_data"]["user"]

        auth0_id = user["sub"]
        email = user["email"]
        username = user.get("username", email.split("@")[0]) # if no username just use email
        userid = get_user_by_auth0(auth0_id)
        if userid is None:
            create_user(auth0_id, username, email)
        response.status_code = 302
        response.headers["Location"] = url_for('feed')
        return response
    except Exception as e:
        return f"Authentication error: {str(e)}", 400

@app.route('/logout')
async def logout():
    """Logout and redirect to Auth0 logout"""
    auth0 = init_auth0()
    response = make_response()
    store_options = {"request": request, "response": response}
    options = LogoutOptions(return_to=url_for("feeds", _external=True))
    logout_url = await auth0.logout(options, store_options)
    response.status_code = 302
    response.headers["Location"] = logout_url
    return response

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/feeds")
async def feeds():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    # Whatever logic we use to personalize feed to user goes here
    posts = get_posts_with_usernames()
    return render_template("feeds.html", posts=posts)


@app.route('/search', methods=["POST"])
async def search():
    search_term = request.form.get("search")
    print("search term")
    print (search_term)
    search_results = search_database(search_term, 20)
    print("search results")
    print (search_results)
    search_type = search_term.startswith('@')
    return render_template("search.html", search_results=search_results, profile=search_type, search_term=search_term)

# default profile call routes to current auth0 users profile
@app.route("/profile")
async def feed():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    if not user:
        return redirect(url_for('login'))
    # fetch profile info from db using auth0 id
    userid = get_user_by_auth0(user["sub"])
    user_data = get_user(userid)
    return redirect(f"/profile/{user_data['username']}")

# profile display route used to display own (sets is_owner tr\ue) or other's profiles
@app.route("/profile/<username>")
async def user_profile(username):
    auth0 = init_auth0()
    store_options = {"request": request}
    current_user = await auth0.get_user(store_options) # current auth0 user
    user = get_user_by_username(username) # user from username passed through route
    if not user:
        return "User not found", 404
    user["pfp"] = f"/pfp/{user['id']}"
    user["banner"] = f"/banner/{user['id']}"
    is_owner = False
    following = False
    if current_user:
        current_user_id = get_user_by_auth0(current_user["sub"])
        if current_user_id == user["id"]:
            is_owner = True
        else:
            following = is_following(current_user_id, user["id"])
    posts = get_posts_by_id(user["id"])
    return render_template("profile.html", user=user, is_owner=is_owner, following=following, posts=posts)

@app.route("/profile/edit", methods=["POST"])
async def update_profile():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    if not user:
        return redirect(url_for('login'))
    
    userid = get_user_by_auth0(user["sub"])
    nickname = request.form.get("nickname")
    bio = request.form.get("bio")
    profile_picture = request.files.get("profile_picture")
    profile_banner = request.files.get("profile_banner")

    if nickname:
        set_nickname(userid, nickname)
    if bio:
        set_bio(userid, bio)

    if profile_picture and profile_picture.filename:
        pfp_name = profile_picture.filename
        pfp = profile_picture.read()
        set_profile_picture(userid, pfp_name, pfp)

    if profile_banner and profile_banner.filename:
        banner_name = profile_banner.filename
        banner = profile_banner.read()
        set_banner(userid, banner_name, banner)

    return redirect("/profile")

# trying with just jpeg for now for simplicity
@app.route("/pfp/<int:userid>")
def pfp(userid):
    image = get_profile_picture(userid)
    if not image:
        return "", 404
    return Response(image[0], mimetype="image/jpeg")

@app.route("/banner/<int:userid>")
def banner(userid):
    image = get_banner(userid)
    if not image:
        return "", 404
    return Response(image[0], mimetype="image/jpeg")

@app.route("/post/<int:post_id>")
def post_page(post_id):
    post = get_post(post_id)
    comments = get_comments(post_id)
    return render_template("post.html", post=post, comments=comments)

@app.route("/post", methods=['POST'])
async def submit_post():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)

    if not user:
        return redirect(url_for('login'))
    
    user_id = get_user_by_auth0(user["sub"])

    # get form data
    title = request.form.get("title")
    post = request.form.get("post")

    if not title or not post:
        flash("Title and post content are required.")
        return redirect(url_for("feeds"))

    # moderate both title and content
    approved_title = moderate_post(title)
    approved_post = moderate_post(post)
    
    if approved_title is True and approved_post is True:
        create_post(user_id, title, post)
        flash("Post created successfully!")
    elif approved_title is False and approved_post is False:
        flash("Your post was rejected!")
    else:
        flash("Your post was not successful")
        
    return redirect(url_for('feeds'))

@app.route("/follow/<username>", methods=["POST"])
async def follow(username):
    auth0 = init_auth0()
    store_options = {"request": request}
    auth_user = await auth0.get_user(store_options)
    if not auth_user:
        return redirect(url_for("login"))
    follower_id = get_user_by_auth0(auth_user["sub"])
    following_id = get_user_id(username)
    if not following_id:
        return "User not found", 404
    follow_user(follower_id, following_id)
    return redirect(f"/profile/{username}")

@app.route("/unfollow/<username>", methods=["POST"])
async def unfollow(username):
    auth0 = init_auth0()
    store_options = {"request": request}
    auth_user = await auth0.get_user(store_options)
    if not auth_user:
        return redirect(url_for("login"))
    follower_id = get_user_by_auth0(auth_user["sub"])
    following_id = get_user_id(username)
    if not following_id:
        return "User not found", 404
    unfollow_user(follower_id, following_id)
    return redirect(f"/profile/{username}")

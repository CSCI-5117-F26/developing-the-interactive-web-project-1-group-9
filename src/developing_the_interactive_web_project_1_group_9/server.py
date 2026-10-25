from flask import Flask, flash, render_template, request, g, Response, make_response, redirect, url_for
from auth0_server_python.auth_types import LogoutOptions
from developing_the_interactive_web_project_1_group_9.auth import init_auth0
from dotenv import load_dotenv
from .database import *
from .llm import *

# import psycopg
import os

app = Flask(__name__)
app.secret_key = os.getenv('AUTH0_SECRET')


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
    return render_template("feeds.html")

# I'm assuming /profile is personal profile, and there's different route
# For looking at other people's profile?
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
    user_data["pfp"] = f"/pfp/{userid}" # append pfp and banner photos to user data object for simplicity
    user_data["banner"] = f"/banner/{userid}"
    return render_template("profile.html", user=user_data)

@app.route("/profile/edit", methods=["POST"])
async def update_profile():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    if not user:
        return redirect(url_for('login'))
    
    userid = get_user_by_auth0(user["sub"])
    bio = request.form.get("bio")
    profile_picture = request.files.get("profile_picture")
    profile_banner = request.files.get("profile_banner")

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


@app.route("/post", methods=['POST'])
async def submit_post():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)

    if not user:
        return redirect(url_for('login'))
    
    user_id = get_user_by_auth0(user["sub"])

    title = request.form.get("title")
    post = request.form.get("post")
    approved_title = moderate_post(title)
    approved_post = moderate_post(post)
    
    if approved_title is True and approved_post is True:
        post_id = create_post(user_id, title, post)
        print("Created post ID:", post_id)
        flash("Post created successfully!")
        return redirect(url_for('feeds'))
    elif approved_title is False and approved_post is False:
        flash("Your post was rejected!")
        return redirect(url_for('feeds'))
    else:
        flash("Your post was not successful")
        return redirect(url_for('feeds'))

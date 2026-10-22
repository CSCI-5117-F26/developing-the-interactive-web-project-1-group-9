from flask import Flask, render_template, request, jsonify, g, Response, make_response, redirect, url_for
from auth0_server_python.auth_types import LogoutOptions
from developing_the_interactive_web_project_1_group_9.auth import auth0
from dotenv import load_dotenv
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
@app.route("/signin")
async def login():
    """Redirect to Auth0 login"""
    response = make_response()
    store_options = {"request": request, "response": response}
    authorization_url = await auth0.start_interactive_login({}, store_options)
    response.status_code = 302
    response.headers["Location"] = authorization_url
    return response


@app.route('/callback')
async def callback():
    """Handle Auth0 callback after login"""
    response = make_response()
    store_options = {"request": request, "response": response}
    try:
        result = await auth0.complete_interactive_login(str(request.url), store_options)
        response.status_code = 302
        response.headers["Location"] = url_for('index')
        return response
    except Exception as e:
        return f"Authentication error: {str(e)}", 400

@app.route('/logout')
async def logout():
    """Logout and redirect to Auth0 logout"""
    response = make_response()
    store_options = {"request": request, "response": response}
    options = LogoutOptions(return_to=url_for("index", _external=True))
    logout_url = await auth0.logout(options, store_options)
    response.status_code = 302
    response.headers["Location"] = logout_url
    return response

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/feeds")
async def feeds():
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    # Whatever logic we use to personalize feed to user goes here
    return render_template("feeds.html")

# I'm assuming /profile is personal profile, and there's different route
# For looking at other people's profile?
@app.route("/profile")
async def feed():
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    if not user:
        return redirect(url_for('login'))
    
    # Logic to get profile info
    return render_template("profile.html")

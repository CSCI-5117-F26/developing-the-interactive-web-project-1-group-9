from flask import Flask, render_template, request, jsonify, g, redirect, url_for, make_response, Response
# import psycopg
import os
from .auth import auth0
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('AUTH0_SECRET')

# Configure session for Auth0
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

#@app.before_request
#def store_request_response():
#    """Make request/response available for Auth0 SDK"""
#    g.store_options = {"request": request}

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


@app.route("/login")
async def login():
    """Redirect to Auth0 login"""
    store_options = {"request": request, "response": make_response()}
    authorization_url = await auth0.start_interactive_login({}, store_options)
    return redirect(authorization_url)

@app.route('/callback')
async def callback():
    """Handle Auth0 callback after login"""
    store_options = {"request": request, "response": make_response()}
    try:
        result = await auth0.complete_interactive_login(str(request.url), store_options)
        return redirect(url_for('feed'))
    except Exception as e:
        return f"Authentication error: {str(e)}", 400


@app.route('/logout')
async def logout():
    """Logout and redirect to Auth0 logout"""
    store_options = {"request": request, "response": make_response()}
    options = LogoutOptions(return_to=url_for("feed", _external=True))
    logout_url = await auth0.logout(options, store_options)
    return redirect(logout_url)

@app.route("/feed")
async def feed():
    store_options = {"request": request, "response": make_response()}
    user = await auth0.get_user(store_options)
    return render_template("feed.html", user=user)
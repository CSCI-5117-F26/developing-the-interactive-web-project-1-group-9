from flask import Flask, abort, flash, render_template, request, g, Response, make_response, redirect, url_for
from auth0_server_python.auth_types import LogoutOptions
from developing_the_interactive_web_project_1_group_9.auth import init_auth0
from dotenv import load_dotenv
from developing_the_interactive_web_project_1_group_9.database import *
from developing_the_interactive_web_project_1_group_9.llm import *
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SearchField, HiddenField
from wtforms.validators import Optional, DataRequired, Length
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename

# import psycopg
import os

app = Flask(__name__)
app.secret_key = os.getenv('AUTH0_SECRET')

load_dotenv()
# url =  os.environ["DATABASE_URL"]


prev_search = ""
prev_type = ""
prev_term = ""

@app.route("/")
async def index():
    return redirect(url_for('feeds'))

# Auth stuff has to be protected route, silently signing out is used
# in phising attacks!!! :0
class AuthLoginForm(FlaskForm):
    submit = SubmitField('sign in', render_kw={"class": "btn btn-primary"})

@app.route("/login")
async def login():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    if user:
        redirect(url_for('feeds'))
    form = AuthLoginForm()
    return render_template("login.html", form=form)

@app.route("/signin", methods=["POST"])
async def signin():
    form = AuthLoginForm()
    if form.validate():
        """Redirect to Auth0 login"""
        auth0 = init_auth0()
        response = make_response()
        store_options = {"request": request, "response": response}
        authorization_url = await auth0.start_interactive_login({}, store_options)
        response.status_code = 302
        response.headers["Location"] = authorization_url
        return response
    else:
        return redirect(url_for('feeds'))

# I think complete interactive login will fail if attacker links to it
# I think auth0 already uses transactions for one time tokens (or it should anyways)
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

class AuthLogoutForm(FlaskForm):
    submit = SubmitField('Log out', render_kw={"class": "btn btn-block"})

@app.route('/logout', methods=["POST"])
async def logout():
    form = AuthLogoutForm()
    if form.validate():
        """Logout and redirect to Auth0 logout"""
        auth0 = init_auth0()
        response = make_response()
        store_options = {"request": request, "response": response}
        options = LogoutOptions(return_to=url_for("feeds", _external=True))
        logout_url = await auth0.logout(options, store_options)
        response.status_code = 302
        response.headers["Location"] = logout_url
        return response
    else:
        return redirect(url_for('feeds'))

# I think search should be protected from XSS, but seems kinda pointless given
# get is accepted for pagination... :/
class SearchForm(FlaskForm):
    # 200 should be plenty...
    search = SearchField(validators=[DataRequired(), Length(max=200)], render_kw={
                        'type': 'search',
                        'placeholder': 'Search people and posts'})
    submit = SubmitField()

class PostUnlikeForm(FlaskForm):
    submit = SubmitField(render_kw={"class": "post-action"})

class PostLikeForm(FlaskForm):
    submit = SubmitField(render_kw={"class": "post-action"})

class CreatePostForm(FlaskForm):
    post = TextAreaField('post', validators=[DataRequired(), Length(max=500)],
                        render_kw={"rows":"3", "placeholder":"What's making you happy today?"})
    submit = SubmitField('Post', render_kw={"class": "btn btn-primary"})

@app.route("/feeds")
async def feeds():
    filter_type = request.args.get('filter', 'recent')
    print(filter_type)
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    # Whatever logic we use to personalize feed to user goes here
    search_form = SearchForm()
    post_like_form = PostLikeForm()
    post_unlike_form = PostUnlikeForm()
    create_post_form = CreatePostForm()
    if filter_type == "following" and not user:
      return redirect(url_for('login'))
    userid = get_user_by_auth0(user["sub"]) if user else None
    posts = get_posts_with_usernames(filter_type, userid) 
    if posts:
      page = request.args.get('page', 1, type=int)
      per_page = 5
      start = (page - 1) * per_page
      end = start + per_page
      total_pages = (len(posts) + per_page - 1) // per_page
      posts_on_page = posts[start:end]
      return render_template("feeds.html", posts=posts_on_page, total_pages = total_pages, page=page, filter_type=filter_type, search_form=search_form, post_like_form=post_like_form, post_unlike_form=post_unlike_form, create_post_form=create_post_form)
    return render_template("feeds.html", posts=posts, filter_type=filter_type, search_form=search_form, post_like_form=post_like_form, post_unlike_form=post_unlike_form, create_post_form=create_post_form)


@app.route('/search', methods=["POST", "GET"])
async def search():
    search_form = SearchForm()
    post_like_form = PostLikeForm()
    post_unlike_form = PostUnlikeForm()
    if request.method == 'POST':
        if search_form.validate():
            search_term = search_form.search.data
            print("search term:")
            print (search_term)
            page = 1
        else:
            print("Someone tried to search but form failed")
            redirect(url_for('feeds'))
    else:
        # request comes from pagination
        search_term = request.args.get('keyword')
        page = request.args.get('page', 1, type=int)
    
    search_results = search_database(search_term, 20)
    if search_term != None:
      search_type = search_term.startswith('@')
      if search_results:  
          page = request.args.get('page', 1, type=int)
          per_page = 5
          start = (page - 1) * per_page
          end = start + per_page
          total_pages = (len(search_results) + per_page - 1) // per_page
          results_on_page = search_results[start:end]
          return render_template("search.html", search_results=results_on_page, profile=search_type, search_term=search_term, total_pages = total_pages, page=page,pagination=True, search_form=search_form, post_like_form=post_like_form, post_unlike_form=post_unlike_form)
      return render_template("search.html", search_results=search_results, profile=search_type, search_term=search_term, search_form=search_form, post_like_form=post_like_form, post_unlike_form=post_unlike_form)
    return redirect('/feeds')

# All right folks we got a whole bunch of forms in profile that need to be protected at all costs!!!
# FileAllowed(['jpg', 'jpeg', 'png']), Optional()
class ProfileEditForm(FlaskForm):
    nickname = StringField('nickname', validators=[Optional()], render_kw={"class": "pure-input-1-4"})
    bio = TextAreaField('bio', validators=[Optional()], render_kw={"class": "pure-input-1-2"})
    profile_picture = FileField('profile_picture', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif']), Optional()])
    profile_banner = FileField('profile_banner', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif']), Optional()])
    submit = SubmitField('Save Changes', render_kw={"class": "pure-button pure-button-primary"})

class ProfileUnfollowForm(FlaskForm):
    submit = SubmitField('Unfollow', render_kw={"class": "btn btn-block"})

class ProfileFollowForm(FlaskForm):
    submit = SubmitField('Follow', render_kw={"class": "btn btn-primary btn-block"})

class PostDeleteForm(FlaskForm):
    submit = SubmitField('Delete', render_kw={"class": "pure-menu-link"})

class PostEditForm(FlaskForm):
    post = TextAreaField('post', validators=[DataRequired(), Length(max=500)],
                        render_kw={"rows":"3"})
    submit = SubmitField('Save Changes', render_kw={"class": "btn btn-primary"})

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
    auth_logout_form = None
    profile_edit_form = None
    profile_unfollow_form = None
    profile_follow_form = None
    post_delete_form = None
    post_like_form = PostLikeForm()
    post_unlike_form = PostUnlikeForm()
    post_edit_form = None
    search_form = SearchForm()
    current_user_id = None
    if current_user:
        current_user_id = get_user_by_auth0(current_user["sub"]) 
        if current_user_id == user["id"]:
            is_owner = True
            auth_logout_form = AuthLogoutForm()
            profile_edit_form = ProfileEditForm()
            post_delete_form = PostDeleteForm()
            post_edit_form = PostEditForm()
        else:
            following = is_following(current_user_id, user["id"])
            if following:
                profile_unfollow_form = ProfileUnfollowForm()
            else:
                profile_follow_form = ProfileFollowForm()

    posts = get_posts_by_id(user["id"], current_user_id)
    following_users = get_following(user["id"])
    followers = get_followers(user["id"])
    if posts:
        page = request.args.get('page', 1, type=int)
        per_page = 5
        start = (page - 1) * per_page
        end = start + per_page
        total_pages = (len(posts) + per_page - 1) // per_page
        posts_on_page = posts[start:end]
        return render_template("profile.html", user=user, is_owner=is_owner, following=following, following_users=following_users, followers=followers, posts=posts_on_page, total_pages = total_pages, page=page, profile_unfollow_form=profile_unfollow_form, profile_follow_form=profile_follow_form, post_delete_form=post_delete_form ,post_unlike_form=post_unlike_form, post_like_form=post_like_form, post_edit_form=post_edit_form, auth_logout_form=auth_logout_form, search_form=search_form, profile_edit_form=profile_edit_form)
    return render_template("profile.html", user=user, is_owner=is_owner, following=following, following_users=following_users, followers=followers, posts=posts, profile_unfollow_form=profile_unfollow_form, profile_follow_form=profile_follow_form, post_delete_form=post_delete_form ,post_unlike_form=post_unlike_form, post_like_form=post_like_form, post_edit_form=post_edit_form, auth_logout_form=auth_logout_form, search_form=search_form, profile_edit_form=profile_edit_form)

@app.route("/profile/edit", methods=["POST"])
async def update_profile():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)
    if not user:
        return redirect(url_for('login'))
    userid = get_user_by_auth0(user["sub"])

    form = None
    nickname = None
    bio = None
    profile_picture = None
    profile_banner = None
    form = ProfileEditForm()
    if form.validate():
        nickname = form.nickname.data
        bio = form.bio.data
        profile_picture = form.profile_picture.data
        profile_banner = form.profile_banner.data
    else:
        print("Someone tried to edit profile %s but form failed", userid)
        print(form.errors)

    # Since everything is set to None, just silently fail to leak
    # as little information as posisble to attacker. I guess timing
    # leak is possible as checking None on form validation fail is faster
    # than if it succeeds. Side channel attacks are such a mess...
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

class CreateCommentForm(FlaskForm):
    post_id = HiddenField('post_id', validators=[DataRequired()])
    comment = TextAreaField('comment', validators=[DataRequired(), Length(max=500)],
                        render_kw={"rows":"3", "placeholder":"What a beautiful day for commenting!"})
    submit = SubmitField('Post', render_kw={"class": "btn btn-primary"})

@app.route("/post/<int:post_id>")
async def post_page(post_id):
    auth0 = init_auth0()
    store_options = {"request": request}
    auth_user = await auth0.get_user(store_options)
    post = get_post(post_id)
    comments = get_comments(post_id)
    if not comments:
      comments = ""
    liked = False
    search_form = SearchForm()
    post_like_form = PostLikeForm()
    post_unlike_form = PostUnlikeForm()
    create_comment_form = CreateCommentForm(data={'post_id' : post_id})
    if auth_user:
        userid = get_user_by_auth0(auth_user["sub"])
        liked = has_liked(userid, post_id)
    if comments:
        page = request.args.get('page', 1, type=int)
        per_page = 5
        start = (page - 1) * per_page
        end = start + per_page
        total_pages = (len(comments) + per_page - 1) // per_page
        comments_on_page = comments[start:end]
        return render_template("post.html", post=post, comments=comments_on_page, liked=liked, total_pages = total_pages, page=page, post_id=post_id, create_comment_form=create_comment_form, post_like_form=post_like_form, post_unlike_form=post_unlike_form, search_form=search_form)
    return render_template("post.html", post=post, comments=comments, liked=liked, create_comment_form=create_comment_form, post_like_form=post_like_form, post_unlike_form=post_unlike_form, search_form=search_form)

@app.route("/post/<int:post_id>/edit", methods=["POST"])
async def update_post(post_id):
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)

    if not user:
        return redirect(url_for("login"))

    user_id = get_user_by_auth0(user["sub"])

    # Get the specific post
    existing_post = get_post(post_id)

    if not existing_post:
        # Make error state same as success to leak as little info
        # Again, there is a timing side channel
        # I don't know what we're going to do about side channel attacks :/
        # Using print, should have a more robust security log system in real web app
        print("Someone tried to edit non-existent post %s", post_id)
        flash("Your changes could not be approved.")
        redirect("/profile")

    # Verify post ownership
    if existing_post["user_id"] != user_id:
        print("Someone tried to edit post %s without ownership", post_id)
        flash("Your changes could not be approved.")
        redirect("/profile")

    # Get form data
    form = PostEditForm()
    post = None
    if form.validate():
        post = form.post.data.strip()

        # Moderate updated content
        approved_post = moderate_post(post)

        if approved_post is True:
            edit_post(post_id, post)
            flash("Post updated successfully!")
        else:
            flash("Your changes could not be approved.")

        return redirect("/profile")

    else:
        print("Post edit attempted but form failed on post %s", post_id)
        flash("Your changes could not be approved.")
        return redirect("/profile")

@app.route("/post/<int:post_id>/delete", methods=["POST"])
async def delete_post(post_id):
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)

    if not user:
        return redirect(url_for("login"))

    user_id = get_user_by_auth0(user["sub"])

    # Get the specific post
    existing_post = get_post(post_id)

    if not existing_post:
        print("Someone tried to delete non-existant post %s", post_id)
        flash("Post deleted unsuccessfully.")
        return redirect("/profile")

    # Verify post ownership
    if existing_post["user_id"] != user_id:
        print("Someone tried to delete post %s without ownership", post_id)
        flash("Post deleted unsuccessfully.")
        return redirect("/profile")

    form = PostDeleteForm()
    if form.validate():
        delete_post_db(user_id, post_id)
        flash("Post deleted successfully!.")
    else:
        print("Someone tried to delete post %s but form failed", post_id)
        flash("Post deleted unsuccessfully.")
    return redirect("/profile")

@app.route("/post", methods=['POST'])
async def submit_post():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)

    if not user:
        return redirect(url_for('login'))
    
    user_id = get_user_by_auth0(user["sub"])

    # get form data
    # title = request.form.get("title")
    form = CreatePostForm()
    if form.validate():
        
        post = form.post.data

        if not post:
            flash("Content is required to make a post.")
            return redirect(url_for("feeds"))

        # moderate both title and content
        # approved_title = moderate_post(title)
        approved_post = moderate_post(post)
        
        if approved_post is True:
            create_post(user_id, post)
            flash("Post created successfully!")
        elif approved_post is False:
            flash("Your post was rejected!")
        else:
            flash("Your post was not successful")
    else:
        print("Someone tried to post on %s behalf but form failed", user_id)
        flash("Your post was not successful")
    return redirect(url_for('feeds'))

@app.route("/comment", methods=['POST'])
async def submit_comment():
    auth0 = init_auth0()
    store_options = {"request": request}
    user = await auth0.get_user(store_options)

    if not user:
        return redirect(url_for('login'))
    
    form = CreateCommentForm()
    if form.validate():

        user_id = get_user_by_auth0(user["sub"])
        comment = form.comment.data
        postid = form.post_id.data
        if not comment:
            flash("Comment content is required.")
            if request.referrer:
                return redirect(request.referrer)
            return redirect(url_for('feeds'))

        # moderate both title and content
        approved_comment = moderate_post(comment)
        
        if approved_comment is True:
            create_comment(user_id, postid, comment)
            flash("Comment created successfully!")
            print("Comment created!")
        else:
            flash("Your comment was not successful")
            
    print(form.errors)
    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for('feeds'))

@app.route("/follow/<username>", methods=["POST"])
async def follow(username):
    form = ProfileFollowForm()
    if form.validate():
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
    form = ProfileUnfollowForm()
    if form.validate():
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

@app.route("/like/<int:post_id>", methods=["POST"])
async def like(post_id):
    form = PostLikeForm()
    if form.validate():
        auth0 = init_auth0()
        store_options = {"request": request}
        user = await auth0.get_user(store_options)
        if not user:
            return redirect(url_for("login"))
        userid = get_user_by_auth0(user["sub"])
        like_post(userid, post_id)
    return redirect(request.referrer or url_for("feeds"))

@app.route("/unlike/<int:post_id>", methods=["POST"])
async def unlike(post_id):
    form = PostUnlikeForm()
    if form.validate():
        auth0 = init_auth0()
        store_options = {"request": request}
        user = await auth0.get_user(store_options)
        if not user:
            return redirect(url_for("login"))
        userid = get_user_by_auth0(user["sub"])
        unlike_post(userid, post_id)
    return redirect(request.referrer or url_for("feeds"))

import psycopg
import os

#TODO: find a better way to organize these, post edit/delete, comment edit/delete, like/double liking posts/comments,
#      following other users, reporting posts and admin side report management, check if user owns post

# CURRENT FUNCTIONS:
# create_user, update_bio, set_profile_picture, set_profile_banner, make_admin, is_admin, get_user_id
# create_post, get_post, edit_post
# create_comment
conn = psycopg.connect(os.environ["DATABASE_URL"])

#user management
def create_user(username, email, password):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, email, user_password) VALUES (%s, %s, %s) RETURNING id;""", (username, email, password))
    user_id = cur.fetchone()[0] # should only fetch id of current user
    conn.commit()
    cur.close()
    conn.close()
    return user_id

def update_bio(userid, bio):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE users SET bio = %s WHERE id = %s;""", (bio, userid))
    conn.commit()
    cur.close()
    conn.close()

#need to figure out image uploading first
# def set_profile_picture(userid, picture_path):
#     conn = psycopg.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_DATABASE"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"))
#     cur = conn.cursor()
#     cur.execute("""UPDATE users SET profile_picture = %s WHERE id = %s;""", (picture_path, userid))
#     conn.commit()
#     cur.close()
#     conn.close()

# def set_profile_banner(userid, picture_path):
#     conn = psycopg.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_DATABASE"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"))
#     cur = conn.cursor()
#     cur.execute("""UPDATE users SET profile_banner = %s WHERE id = %s;""", (picture_path, userid))
#     conn.commit()
#     cur.close()
#     conn.close()

def make_admin(userid):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE users SET is_admin = TRUE WHERE id = %s;""", (userid,))
    conn.commit()
    cur.close()
    conn.close()

def is_admin(userid):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT is_admin FROM users WHERE id = %s;""", (userid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False

def get_user_id(username):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT id FROM users WHERE username = %s;""", (username,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False

def get_username(userid):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT username FROM users WHERE id = %s;""", (userid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False



#post management
def create_post(userid, title, content):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s) RETURNING id;""", (userid, title, content))
    post_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return post_id

def get_post(postid):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT
                     posts.id,
                     posts.user_id,
                     posts.content,
                     posts.likes_count,
                     users.username,
                     posts.post_created
                  FROM posts 
                  JOIN users on posts.user_id = users.id
                  WHERE posts.id = %s; """, (postid,)
                     )
    post = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if post:
        post = list(post)
        print(post[5])
        post[5] = post[5].strftime("%m/%d/%y")
        print(post[5])

    return post

def get_posts():
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT * FROM posts;""")
    post = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return post

def get_posts_with_usernames():
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
      """
      SELECT
        posts.id,
        posts.content,
        users.username,
        posts.likes_count,
        posts.comment_count,
        posts.post_created
      FROM posts
      JOIN users ON posts.user_id = users.id;
      """
    )
    posts = cur.fetchall()
    if posts:
        posts = [
        [row[0], row[1], row[2], row[3], row[4], row[5].strftime("%m/%d/%y")]
        for row in posts
    ]
    print(posts)
    return posts

def edit_post(postid, title, content):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE posts SET title = %s, content = %s, last_updated = CURRENT_TIMESTAMP WHERE id = %s;""", (title, content, postid))
    conn.commit()
    cur.close()
    conn.close()

#comment management
def create_comment(userid, postid, content):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("""INSERT INTO comments (user_id, post_id, content) VALUES (%s, %s, %s) RETURNING id;""", (userid, postid, content))
    comment_id = cur.fetchone()[0]
    #need to update count of comments for post comment is under
    cur.execute("""UPDATE posts SET comment_count = comment_count + 1 WHERE id = %s""", (postid,))
    conn.commit()
    cur.close()
    conn.close()
    return comment_id


def get_comments(postid):
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute(
      """
      SELECT
        comments.post_id,
        comments.content,
        users.username
      FROM comments
      JOIN users ON comments.user_id = users.id
      WHERE post_id = (%s);
      """, (postid,)
    )
    comments = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return comments
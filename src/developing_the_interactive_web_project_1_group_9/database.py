import psycopg
import os

#TODO: find a better way to organize these, post edit/delete, comment edit/delete, like/double liking posts/comments,
#      following other users, reporting posts and admin side report management, check if user owns post

# CURRENT FUNCTIONS:
# create_user, update_bio, set_profile_picture, set_profile_banner, make_admin, is_admin, get_user_id
# create_post, get_post, edit_post
# create_comment


#user management
def create_user(auth_id, username, email):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (auth_id, username,nickname, email) VALUES (%s, %s, %s, %s) RETURNING id;""", (auth_id, username, username, email))
    user_id = cur.fetchone()[0] # should only fetch id of current user
    conn.commit()
    cur.close()
    conn.close()
    return user_id

def set_nickname(userid, nickname):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE users SET nickname = %s WHERE id = %s;""", (nickname, userid))
    conn.commit()
    cur.close()
    conn.close()

def set_bio(userid, bio):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE users SET bio = %s WHERE id = %s;""", (bio, userid))
    conn.commit()
    cur.close()
    conn.close()

def set_profile_picture(userid, filename, image):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pfps (user_id, file_name, image_data)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET
        file_name = EXCLUDED.file_name,
        image_data = EXCLUDED.image_data;
    """, (userid, filename, psycopg.Binary(image)))
    conn.commit()
    cur.close()
    conn.close()

def set_banner(userid, filename, image):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO banners (user_id, file_name, image_data)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET
        file_name = EXCLUDED.file_name,
        image_data = EXCLUDED.image_data;
    """, (userid, filename, psycopg.Binary(image)))
    conn.commit()
    cur.close()
    conn.close()

def get_user(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT id, username, nickname, email, bio, follower_count, following_count FROM users WHERE id = %s;""", (userid,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        return None
    return {
        "id": user[0],
        "username": user[1],
        "nickname": user[2],
        "email": user[3],
        "bio": user[4],
        "follower_count": user[5],
        "following_count": user[6]
    }

def get_user_by_username(username):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT id, username, nickname, email, bio, follower_count, following_count FROM users WHERE username = %s;""", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        return None
    return {
        "id": user[0],
        "username": user[1],
        "nickname": user[2],
        "email": user[3],
        "bio": user[4],
        "follower_count": user[5],
        "following_count": user[6]
    }


def get_profile_picture(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT image_data FROM pfps WHERE user_id = %s;""", (userid,))
    pfp = cur.fetchone()
    cur.close()
    conn.close()
    return pfp

def get_banner(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT image_data FROM banners WHERE user_id = %s;""", (userid,))
    banner = cur.fetchone()
    cur.close()
    conn.close()
    return banner

def make_admin(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE users SET is_admin = TRUE WHERE id = %s;""", (userid,))
    conn.commit()
    cur.close()
    conn.close()

def is_admin(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT is_admin FROM users WHERE id = %s;""", (userid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False

def get_user_id(username):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT id FROM users WHERE username = %s;""", (username,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False

def get_user_by_auth0(auth0_id):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE auth_id = %s;", (auth0_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
            return result[0]
    return None


def get_username(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT username FROM users WHERE id = %s;""", (userid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False

def get_post(postid):
    conn = psycopg.connect(os.environ["DB_URL"])
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
    cur.close()
    conn.close()
    if not post:
      return None
    return {
        "post_id": post[0],
        "user_id": post[1],
        "content": post[2],
        "likes": post[3],
        "username": post[4],
        "time_created": post[5].strftime("%m/%d/%y"),
        "pfp": f"/pfp/{post[1]}"
    }

def get_posts():
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""SELECT * FROM posts;""")
    post = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return post

def get_posts_with_usernames():
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute(
      """
      SELECT
        posts.id,
        posts.content,
        users.username,
        posts.likes_count,
        posts.comment_count,
        posts.post_created,
        posts.user_id
      FROM posts
      JOIN users ON posts.user_id = users.id;
      """
    )
    posts = cur.fetchall()
    if not posts:
      return None
    
    return [
        {
          "post_id": post[0],
          "content": post[1],
          "username": post[2],
          "likes": post[3],
          "comment_count": post[4],
          "time_created": post[5].strftime("%m/%d/%y"),
          "pfp": f"/pfp/{post[6]}"
      }
      for post in posts
    ]

def get_posts_by_id(userid):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute(
      """
      SELECT
        posts.id,
        posts.content,
        posts.likes_count,
        posts.comment_count,
        posts.post_created,
        posts.user_id
      FROM posts
      WHERE posts.user_id = %s;""", (userid,)
    )
    posts = cur.fetchall()
    if not posts:
      return None
    return [
        {
          "post_id": post[0],
          "content": post[1],
          "likes": post[2],
          "comment_count": post[3],
          "time_created": post[4].strftime("%m/%d/%y"),
          "pfp": f"/pfp/{post[5]}"
      }
      for post in posts
    ]



#post management
def create_post(userid, title, content):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s) RETURNING id;""", (userid, title, content))
    post_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return post_id





def edit_post(postid, title, content):
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute("""UPDATE posts SET title = %s, content = %s, last_updated = CURRENT_TIMESTAMP WHERE id = %s;""", (title, content, postid))
    conn.commit()
    cur.close()
    conn.close()

#comment management
def create_comment(userid, postid, content):
    conn = psycopg.connect(os.environ["DB_URL"])
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
    conn = psycopg.connect(os.environ["DB_URL"])
    cur = conn.cursor()
    cur.execute(
      """
      SELECT
        comments.post_id,
        comments.content,
        users.username,
        comments.likes_count,
        comments.comment_created,
        users.id
      FROM comments
      JOIN users ON comments.user_id = users.id
      WHERE post_id = (%s);
      """, (postid,)
    )
    comments = cur.fetchall()
    if not comments:
      return None
    cur.close()
    conn.close()
    return [
      {
          "comment_id": comment[0],
          "content": comment[1],
          "username": comment[2],
          "likes": comment[3],
          "time_created": comment[4].strftime("%m/%d/%y"),
          "pfp": f"/pfp/{comment[5]}"
      }
      for comment in comments
    ]

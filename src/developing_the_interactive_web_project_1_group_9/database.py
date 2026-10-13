import psycopg2
import os

conn = psycopg2.connect(host=os.getenv("DB_HOST"), database=os.getenv("DB_DATABASE"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"))

#TODO: find a better way to organize these, post edit/delete, comment edit/delete, like/double liking posts/comments,
#      following other users, reporting posts and admin side report management

#user management
def create_user(username, email, password):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, email, user_password) VALUES (%s, %s, %s) RETURNING id;""", (username, email, password))
    user_id = cur.fetchone()[0] # should only fetch id of current user
    conn.commit()
    cur.close()
    conn.close()
    return user_id

def update_bio(userid, bio):
    cur = conn.cursor()
    cur.execute("""UPDATE users SET bio = %s WHERE id = %s;""", (bio, userid))
    conn.commit()
    cur.close()
    conn.close()

def set_profile_picture(userid, picture_path):
    cur = conn.cursor()
    cur.execute("""UPDATE users SET profile_picture = %s WHERE id = %s;""", (picture_path, userid))
    conn.commit()
    cur.close()
    conn.close()

def set_profile_banner(userid, picture_path):
    cur = conn.cursor()
    cur.execute("""UPDATE users SET profile_banner = %s WHERE id = %s;""", (picture_path, userid))
    conn.commit()
    cur.close()
    conn.close()

def make_admin(userid):
    cur = conn.cursor()
    cur.execute("""UPDATE users SET is_admin = TRUE WHERE id = %s;""", (userid,))
    conn.commit()
    cur.close()
    conn.close()

def is_admin(userid):
    cur = conn.cursor()
    cur.execute("""SELECT is_admin FROM users WHERE id = %s;""", (userid,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return False

#post management
def create_post(userid, title, content):
    cur = conn.cursor()
    cur.execute("""INSERT INTO posts (user_id, title, content) VALUES (%s, %s, %s) RETURNING id;""", (userid, title, content))
    post_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return post_id

#comment management
def create_comment(userid, postid, content):
    cur = conn.cursor()
    cur.execute("""INSERT INTO comments (user_id, post_id, content) VALUES (%s, %s, %s) RETURNING id;""", (userid, postid, content))
    comment_id = cur.fetchone()[0]

    #need to update count of comments for post comment is under
    cur.execute("""UPDATE posts SET comment_count = comment_count + 1 WHERE id = %s""", (postid))
    conn.commit()
    cur.close()
    conn.close()
    return comment_id
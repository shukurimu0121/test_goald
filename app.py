from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import random
import math
import os
import psycopg2
from psycopg2.extras import DictCursor
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

# localhost 
DATABASE_URL = "postgres://hpobhxuditpwle:f50f465838805b73f6eb6b9906d0d627cfba1178dd4989a5032acbd3cc8d08ef@ec2-52-205-55-36.compute-1.amazonaws.com:5432/ddngmugcbbk0mf"

# deploy on heroku
# DATABASE_URL = os.environ['DATABASE_URL']

app = Flask(__name__)

# connect to database
def connect_to_database():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

#configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# login required decorator
def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# each route 
# index route
@app.route("/")
@login_required
def index():
    # show users goal
    user_id = session["user_id"]

    # if users goal deadline is passed, notify it

    # get the user's goal from database
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
                goal = cur.fetchone()
    except:
        return render_template("apology.html", msg="失敗しました")

    # get username
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                username = cur.fetchone()["name"]
    except:
        return render_template("apology.html", msg="失敗しました")

    if goal:
        return render_template("index.html", goal=goal["goal"], username=username)
    
    else:
        return render_template("index.html", username=username)


# login route
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # When POST
    if request.method == "POST":
        # get the user's input
        username = request.form.get("username")
        password = request.form.get("password")

        # When invalid input
        if not username:
            return render_template("apology.html", msg="ユーザーネームを入力してください")

        elif not password:
            return render_template("apology.html", msg="パスワードを入力してください")

        # Get imput username from database
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE name = %s", (username,))
                    user = cur.fetchone()
        except:
            return render_template("apology.html", msg="失敗しました")
        
        # Check the username and password are correct
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("apology.html", msg="不当なユーザーネームまたはパスワードです")

        # All OK add user to session
        session["user_id"] = user["id"]

        # Redirect user to home page
        return redirect("/")

    # When GET
    else:
        return render_template("login.html")
    
# logout route
@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# register route
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
     # When POST
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return render_template("apology.html", msg="ユーザーネームを入力してください")

        # Ensure password was submitted
        elif not password:
            return render_template("apology.html", msg="パスワードを入力してください")

        # Ensure password was submitted again
        elif not confirmation:
            return render_template("apology.html", msg="パスワードを再度入力してください")

        # password matches confirmation
        elif password != confirmation:
            return render_template("apology.html", msg="パスワードを正しく入力してください")

        # Check the username already exists
        # Query database for username
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE name = %s", (username,))
                    user = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")
        
        if  len(user) != 0:
            return render_template("apology.html", msg="そのユーザーネームはすでに使われています")

        else:
            # Insert username and password hash to table
            password_hash = generate_password_hash(password)
            try:
                with connect_to_database() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO users (name, password_hash) VALUES (%s, %s)", (username, password_hash))
                    conn.commit()
            except:
                return render_template("apology.html", msg="失敗しました")

            # redirect log in page
            return redirect("/login")

    else:
        return render_template("register.html")
    
# room route
@app.route("/make_room", methods=["GET", "POST"])
@login_required
def make_room():
    """Make Room"""
    # get the user's id
    user_id = session["user_id"]

    # When POST
    if request.method == "POST":
        
        # get the user's input
        room_id = int(request.form.get("room_id"))
        room_password = request.form.get("room_password")

        # When invalid input
        if not room_id or not room_password:
            return render_template("apology.html", msg="ルームIDとパスワードを入力してください")
        
        # when room id is mainus, return apology
        if room_id < 0:
            return render_template("apology.html", msg="ルームIDは正の整数を入力してください")
        
        # if the room id already exists, return apology
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
                    room = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        if len(room) != 0:
            return render_template("apology.html", msg="そのルームIDはすでに使われています")

        # password to hash
        room_password_hash = generate_password_hash(room_password)

        # Put room info to database        
        try:
            with connect_to_database() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO rooms (room_id, room_password_hash, user_id) VALUES (%s, %s, %s)", (room_id, room_password_hash, user_id))
                conn.commit()
        except:
            return render_template("apology.html", msg="失敗しました")
        
        return redirect("/enter_room")
    

    # When GET
    else:
        # if user already join a room, tell it
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM rooms WHERE user_id = %s", (user_id,))
                    room = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")
        
        if len(room) != 0:
            return render_template("make_room.html", msg="すでにルームに参加しています")
        
        # check user submit goal
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
                    goal = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        if len(goal) == 0:
            return render_template("apology.html", msg="目標を設定してください")
        
        else:
            return render_template("make_room.html")
    
# enter room route
@app.route("/enter_room", methods=["GET", "POST"])
@login_required
def enter_room():
    """enter room"""
    # get the user's id
    user_id = session["user_id"]

    # When POST
    if request.method == "POST":
        # get the user's input
        room_id = int(request.form.get("room_id"))
        room_password = request.form.get("room_password")
        
        # When invalid input
        if not room_id or not room_password:
            return render_template("apology.html", msg="ルームIDとパスワードを入力してください")
        
        # when room id is mainus, return apology
        if room_id < 0:
            return render_template("apology.html", msg="ルームIDは正の整数を入力してください")
        
        # check user submit goal
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
                    goal = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        if len(goal) == 0:
            return render_template("apology.html", msg="目標を設定してください")
        
        # Get room info from database)
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
                    room = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        # Check the room id and password are correct
        if len(room) == 0 or not check_password_hash(room[0]["room_password_hash"], room_password):
            return render_template("apology.html", msg="不当なルームIDまたはパスワードです")
        
        else:
            #パスワードをハッシュ化
            room_password_hash = generate_password_hash(room_password)
            # ユーザーを部屋に追加
            try:
                with connect_to_database() as conn:
                    with conn.cursor() as cur:
                        cur.execute("INSERT INTO rooms (room_id, room_password_hash, user_id) VALUES (%s, %s, %s)", (room_id, room_password_hash, user_id))
                    conn.commit()
            except:
                return render_template("apology.html", msg="失敗しました")
            
            return redirect(url_for("room", room_id=room_id))
        
    # When GET
    else:
        """if user already join a room, redirect to room page"""
        # get the user's id
        user_id = session["user_id"]

        # check user submit goal
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
                    goal = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        if len(goal) == 0:
            return render_template("apology.html", msg="目標を設定してください")

        # get the user's room info from database
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM rooms WHERE user_id = %s", (user_id,))
                    room = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        # if user already join a room, redirect to room page
        if len(room) != 0:
            return redirect(url_for("room", room_id=room[0]["room_id"]))
        
        else:
            return render_template("enter_room.html")
    
# room route
@app.route("/room")
@login_required
def room():
    user_id = session["user_id"]
    room_id = request.args.get("room_id")

    #if the room does not exist, return apology
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE room_id = %s", (room_id,))
                room = cur.fetchall()
    except:
        return render_template("apology.html", msg="失敗しました")

    if len(room) == 0:
        return render_template("apology.html", msg="そのルームは存在しません")

    # if the user does not join the room, return apology
    room_users_ids = []
    for room_user in room:
        room_users_ids.append(room_user["user_id"])

    if user_id not in room_users_ids:
        return render_template("apology.html", msg="このルームに参加していません")
    
    goals = []
    # get all menbers' goal info
    for room_user_id in room_users_ids:
        # 各user_idごとの目標と進捗率を取得し、辞書に追加
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM goals WHERE user_id = %s", (room_user_id,))
                    user_goals = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")
        user_goal_dicts = [{"goal": goal["goal"], "progress_rate": goal["progress_rate"], "user_id": goal["user_id"], "deadline": goal["deadline"]} for goal in user_goals]
        goals.extend(user_goal_dicts)
    
    # get all members' username
    usernames = []
    for room_user_id in room_users_ids:
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM users WHERE id = %s", (room_user_id,))
                    username = cur.fetchone()["name"]
        except:
            return render_template("apology.html", msg="失敗しました")
        
        usernames.append(username)
    
    #shuffle usernames and goals
    random.shuffle(usernames)
    random.shuffle(goals)
    
    # get the number of members
    number_of_members = len(usernames)

    # get progress rate average
    progress_rate_sum = 0
    for goal in goals:
        progress_rate_sum += goal["progress_rate"]
    progress_rate_average = progress_rate_sum / number_of_members  
    average = math.floor(progress_rate_average) 

    return render_template("room.html", goals=goals, usernames=usernames, user_id=user_id, number_of_members=number_of_members, average=average)

# leave room route
@app.route("/leave_room", methods=["POST"])
@login_required
def leave_room():
    """leave room"""
    # get the user's id
    user_id = session["user_id"]

    # delete user from room
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM rooms WHERE user_id = %s", (user_id,))
            conn.commit()
    except:
        return render_template("apology.html", msg="失敗しました")
    
    return redirect("/enter_room")
    
# goal route
@app.route("/goal", methods=["GET", "POST"])
@login_required
def goal():
    """goal"""
    # Get user's id
    user_id = session["user_id"]

    # When POST
    if request.method == "POST":
        # get the user's goal input
        goal = request.form.get("goal")
        date = request.form.get("date")
        time = request.form.get("time")

        # When invalid input
        if not goal or not date or not time:
            return render_template("apology.html", msg="正しく入力してください")

        datetime_data = datetime.strptime(date + " " + time, '%Y-%m-%d %H:%M')

        # deadline to datetime
        deadline = datetime_data

        # date created
        date_created = datetime.now()

        # Put goal info to database
        # put into goals table
        try:
            with connect_to_database() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO goals (goal, date_created, deadline, user_id) VALUES (%s, %s, %s, %s)", (goal, date_created, deadline, user_id))
                conn.commit()
        except:
            return render_template("apology.html", msg="失敗しました")
        
        # put into goals_history table
        default_progress_rate = 0
        try:
            with connect_to_database() as conn:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO goals_history (goal, user_id, progress_rate) VALUES (%s, %s, %s)", (goal, user_id, default_progress_rate))
                conn.commit()
        except:
            return render_template("apology.html", msg="失敗しました")
        
        return redirect("/goal")

    # When GET
    else:
        # if user already has a goal, display it
        try:
            with connect_to_database() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute("SELECT * FROM goals WHERE user_id = %s", (user_id,))
                    goal = cur.fetchall()
        except:
            return render_template("apology.html", msg="失敗しました")

        today = datetime.now().strftime('%Y-%m-%d')
        if len(goal) == 1:
            return render_template("goal.html", goal=goal[0]["goal"], id=goal[0]["id"], progress_rate=goal[0]["progress_rate"], deadline=goal[0]["deadline"], today=today)
        else:
            return render_template("goal.html", today=today)
        
# delete goal route
@app.route("/delete_goal", methods=["POST"])
@login_required
def delete_goal():
    """delete goal"""

    # get user id
    user_id = session["user_id"]

    # delete goal from database    
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM goals WHERE user_id = %s", (user_id,))
            conn.commit()
    except:
        return render_template("apology.html", msg="失敗しました")
    
    return redirect("/goal")

# update progress rate route
@app.route("/update_progress_rate", methods=["POST"])
@login_required
def update_progress_rate():
    """update progress rate"""
    # get user id
    user_id = session["user_id"]

    # get room id user in
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE user_id = %s", (user_id,))
                room = cur.fetchall()
    except:
        return render_template("apology.html", msg="失敗しました")

    # get progress rate
    progress_rate = int(request.form.get("progress"))

    # update progress rate
    # update goals table
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE goals SET progress_rate = %s WHERE user_id = %s", (progress_rate, user_id))
            conn.commit()
    except:
        return render_template("apology.html", msg="失敗しました")
    
    # update goals_history table
    try:
        with connect_to_database() as conn:
            with connect_to_database() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE goals_history SET progress_rate = %s WHERE user_id = %s", (progress_rate, user_id))
            conn.commit()
    except:
        return render_template("apology.html", msg="失敗しました")
    
    # if user in a room, redirect to room page
    if len(room) != 0:
        return redirect(url_for("room", room_id=room[0]["room_id"]))
    
    # if user not in a room, redirect to goal page
    else:
        return redirect("/goal")
    
# notion route
@app.route("/notion")
@login_required
def notion():
    """notion"""
    return render_template("notion.html")

# update deadline route
@app.route("/update_deadline", methods=["POST"])
@login_required
def update_deadline():
    # get user id
    user_id = session["user_id"]

    # get new deadline from users input
    date = request.form.get("date")
    time = request.form.get("time")

    # When invalid input
    if not date or not time:
        return render_template("apology.html", msg="正しく入力してください")
    
    new_deadline = datetime.strptime(date + " " + time, '%Y-%m-%d %H:%M')

    # update user's goal deadline
    try:
        with connect_to_database() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE goals SET deadline = %s WHERE user_id = %s", (new_deadline, user_id))
            conn.commit()
    except:
        return render_template("apology.html", msg="失敗しました")
    
    return redirect("/goal")

# profile route
@app.route("/profile")
@login_required
def profile():
    """profile"""
    # get user id
    user_id = session["user_id"]

    # get username  
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                username = cur.fetchone()["name"]
    except:
        return render_template("apology.html", msg="失敗しました")

    # get user's goal history
    try:
        with connect_to_database() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM goals_history WHERE user_id = %s", (user_id,))
                goals_history = cur.fetchall()
    except:
        return render_template("profile.html")

    return render_template("profile.html", username=username, goals_history=goals_history)


# linebot 
#Token取得

YOUR_CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
YOUR_CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# Webhook
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# Message handler
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    return_text = event.message.text
    return TextSendMessage(text=return_text)
        


if __name__ == '__main__':
    app.run(debug=True)


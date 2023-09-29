from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import random
import math

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///goald.db'
db = SQLAlchemy(app)

# create database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    goal = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    progress_rate = db.Column(db.Integer, nullable=False, default=0)
    
class Room(db.Model):
    id = db.Column(db.Integer, nullable=False, primary_key=True, autoincrement=True)
    room_id = db.Column(db.Integer, nullable=False)
    room_password_hash = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

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

    # get the user's goal
    goal = Goal.query.filter(Goal.user_id == user_id).all()

    # get username
    username = User.query.filter(User.id == user_id).first().name

    if len(goal) != 0:
        user_goal = goal[0].goal
        return render_template("index.html", goal=user_goal, username=username)
    
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
        user = User.query.filter(User.name == username).all()

        # Check the username and password are correct
        if len(user) != 1 or not check_password_hash(user[0].password_hash, password):
            return render_template("apology.html", msg="不当なユーザーネームまたはパスワードです")

        # All OK add user to session
        session["user_id"] = user[0].id

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
        user = User.query.filter(User.name == username).all()
        if  len(user) != 0:
            return render_template("apology.html", msg="そのユーザーネームはすでに使われています")

        else:
            # Insert username and password hash to table
            password_hash = generate_password_hash(password)
            new_user = User(name=username, password_hash=password_hash)

            db.session.add(new_user)
            db.session.commit()

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
        
        # if the room id already exists, return apology
        room = Room.query.filter(Room.room_id == room_id).all()
        if len(room) != 0:
            return render_template("apology.html", msg="そのルームIDはすでに使われています")

        # password to hash
        room_password_hash = generate_password_hash(room_password)

        # Put room info to database
        try:
            new_room_user = Room(room_id=room_id, room_password_hash=room_password_hash, user_id=user_id)

            db.session.add(new_room_user)
            db.session.commit()
            return redirect(url_for("room", room_id=room_id))
        
        except:
            return render_template("apology.html", msg="すでにルームに参加しています")

    # When GET
    else:
        # if user already join a room, tell it
        room = Room.query.filter(Room.user_id == user_id).all()
        if len(room) != 0:
            return render_template("make_room.html", msg="すでにルームに参加しています")
        
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
        
        # check user submit goal
        goal = Goal.query.filter(Goal.user_id == user_id).all()
        if len(goal) == 0:
            return render_template("apology.html", msg="目標を設定してください")
        
        # Get room info from database
        room = Room.query.filter(Room.room_id == room_id).all()

        # Check the room id and password are correct
        if len(room) == 0 or not check_password_hash(room[0].room_password_hash, room_password):
            return render_template("apology.html", msg="不当なルームIDまたはパスワードです")
        
        else:
            #パスワードをハッシュ化
            room_password_hash = generate_password_hash(room_password)
            # ユーザーを部屋に追加
            new_room_user = Room(room_id=room_id, room_password_hash=room_password_hash, user_id=user_id)
            db.session.add(new_room_user)
            db.session.commit()
            return redirect(url_for("room", room_id=room_id))
    # When GET
    else:
        """if user already join a room, redirect to room page"""
        # get the user's id
        user_id = session["user_id"]

        # get the user's room info from database
        room = Room.query.filter(Room.user_id == user_id).all()

        # if user already join a room, redirect to room page
        if len(room) != 0:
            return redirect(url_for("room", room_id=room[0].room_id))
        
        else:
            return render_template("enter_room.html")
    
# room route
@app.route("/room")
@login_required
def room():
    user_id = session["user_id"]
    room_id = request.args.get("room_id")

    #if the room does not exist, return apology
    room = Room.query.filter(Room.room_id == room_id).all()
    if len(room) == 0:
        return render_template("apology.html", msg="そのルームは存在しません")

    # if the user does not join the room, return apology
    room_users_ids = []
    for room_user in room:
        room_users_ids.append(room_user.user_id)
    if user_id not in room_users_ids:
        return render_template("apology.html", msg="このルームに参加していません")
    
    goals = []
    # get all menbers' goal info
    for room_user_id in room_users_ids:
        # 各user_idごとの目標と進捗率を取得し、辞書に追加
        user_goals = Goal.query.filter(Goal.user_id == room_user_id).all()
        user_goal_dicts = [{"goal": goal.goal, "progress_rate": goal.progress_rate, "user_id": goal.user_id, "deadline": goal.deadline} for goal in user_goals]
        goals.extend(user_goal_dicts)
    
    # get all members' username
    usernames = []
    for room_user_id in room_users_ids:
        username = User.query.filter(User.id == room_user_id).first().name
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
        delete_user = Room.query.filter(Room.user_id == user_id).first()
        db.session.delete(delete_user)
        db.session.commit()
        return redirect("/")

    except:
        return render_template("apology.html", msg="このルームに参加していません")
    
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

        datetime_data = datetime.strptime(date + " " + time, '%Y-%m-%d %H:%M')

        # deadline to datetime
        deadline = datetime_data

        # When invalid input
        if not goal or not date or not time:
            return render_template("apology.html", msg="正しく入力してください")
        
        # Put goal info to database
        try:
            date_created = datetime.now()
            new_goal = Goal(goal=goal, date_created=date_created, deadline=deadline, user_id=user_id)
            db.session.add(new_goal)
            db.session.commit()
            return redirect("/goal")

        except:
            return render_template("apology.html", msg="失敗しました")
    
    # When GET
    else:
        # if user already has a goal, display it
        goal = Goal.query.filter(Goal.user_id == user_id).all()
        today = datetime.now().strftime('%Y-%m-%d')
        if len(goal) == 1:
            return render_template("goal.html", goal=goal[0].goal, id=goal[0].id, progress_rate=goal[0].progress_rate, deadline=goal[0].deadline, today=today)
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
        delete_goal = Goal.query.filter(Goal.user_id == user_id).first()
        db.session.delete(delete_goal)
        db.session.commit()
        return redirect("/goal")
    
    except:
        return render_template("apology.html", msg="失敗しました")

# update progress rate route
@app.route("/update_progress_rate", methods=["POST"])
@login_required
def update_progress_rate():
    """update progress rate"""
    # get user id
    user_id = session["user_id"]

    # get progress rate
    progress_rate = int(request.form.get("progress"))

    # update progress rate
    try:
        update_goal = Goal.query.filter(Goal.user_id == user_id).first()
        update_goal.progress_rate = progress_rate
        db.session.commit()
        return redirect("/")
    
    except:
        return render_template("apology.html", msg="失敗しました")  

if __name__ == '__main__':
    app.run()


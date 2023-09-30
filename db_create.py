import psycopg2
import os

# connect to database
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# create cursor
cur = conn.cursor()

# create table
create_users_table_query = "CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(50) NOT NULL, password_hash VARCHAR(200) NOT NULL);"
create_goals_table_query = "CREATE TABLE goals (id SERIAL PRIMARY KEY, goal VARCHAR(200) NOT NULL, date_created TIMESTAMP NOT NULL, deadline TIMESTAMP NOT NULL, user_id INTEGER NOT NULL, progress_rate INTEGER NOT NULL DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users (id), CONSTRAINT unique_user_goal UNIQUE (user_id));"
create_rooms_table_query = "CREATE TABLE rooms (id SERIAL PRIMARY KEY, room_id INTEGER NOT NULL, room_password_hash VARCHAR(200) NOT NULL, user_id INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES users (id), CONSTRAINT unique_user_room UNIQUE (user_id));"

cur.execute(create_users_table_query)
cur.execute(create_goals_table_query)
cur.execute(create_rooms_table_query)

# commit changes
conn.commit()

# close cursor and connection
cur.close()
conn.close()


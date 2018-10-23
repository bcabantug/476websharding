from flask import Flask, request, jsonify, g, Response
from flask_basicauth import BasicAuth
import sqlite3
import json
from datetime import datetime
from time import gmtime, strftime

app = Flask(__name__)
app.config["DEBUG"] = True

# Global db variable
DATABASE = 'forum.db'

# From http://flask.pocoo.org/docs/1.0/patterns/sqlite3/
# Connects to and returns the db used in init_db() and query_db()
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = dict_factory
    return db

# From http://flask.pocoo.org/docs/1.0/patterns/sqlite3/
# Closes the db at the end of each rquest for get_db()
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# From http://flask.pocoo.org/docs/1.0/patterns/sqlite3/
# query: query as string; e.g. 'Select * from Users'
# args: query arguments, leave empty if no args; e.g. ['user', 'password']
# one: Set to true if only 1 row is required for query else keep false
# returns results of the query
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

# dictionary function taken from programminghistorian for placement purposes
def dict_factory(cursor, row):
    d={}
    for idx, col in enumerate(cursor.description):
        d[col[0]]= row[idx]
    return d

#subclass of BasicAuth (based off Flask-BasicAuth extension)
class NewAuth(BasicAuth):
    #override of check_credentials
    # returns true if the username and password matches else returns false
    def check_credentials(self, username, password):
        user = query_db('SELECT Username, Password from Users where Username = ? and password = ?', [username, password], one=True)
        if user is not None:
            return True
        else:
            return False

#function to check the auth object for present authorization
def auth_check(auth):
    #auth = request.authorization
    if (auth) == None:
        return False
    else:
        # check_auth returns True or False depending on the credentials
        check_auth = NewAuth().check_credentials(auth.username, auth.password)
        if check_auth is False:
            return False

# returns a JSON response with status code and optional body and location
def get_response(status, body=None, location=None):
    if body != None:
        response = jsonify(body)
    else:
        response = jsonify()
    response.status_code = status
    if location != None:
        response.headers['Location'] = location
    return response

# from http://blog.luisrei.com/articles/flaskrest.html
@app.errorhandler(404)
def not_found(error=None):
    message = {
            'status': 404,
            'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp


#list available discussion forums GET
@app.route('/forums', methods=['GET', 'POST'])
def forum():
    #creating a new discussion forum
    if request.method == 'POST':
        # auth contains the username and Password
        auth = request.authorization

        if auth_check(auth) is False:
            return get_response(401)


        forum_submit = request.get_json()
        #parse the name from JSON
        forum_name = forum_submit.get('name')
        # If forumn name does't exist insert it into the db and return success
        if query_db('SELECT ForumsName from Forums where ForumsName = ?', [request.get_json().get('name')], one=True) is None:
            query = 'INSERT into Forums (CreatorId, ForumsName) Values ((Select UserId from Users where Username = ?), ?);'
            conn = get_db()
            cur = conn.cursor()
            cur.execute(query, (auth.username, str(forum_name)))
            forum = cur.execute('SELECT last_insert_rowid() as ForumId;').fetchall()
            forumid = dict(forum[0]).get('ForumId')
            conn.commit()
            conn.close()
            return get_response(201, body=None, location=('/forums/'+str(forumid)))
        else:
            return get_response(409)
    #request for all the present forums
    elif request.method == 'GET':
        query = 'SELECT Users.Username as creator, Forums.ForumId as id, Forums.ForumsName as name FROM Forums, Users where CreatorId = UserId;'
        '''
            [
                {
                    "id": 1,
                    "name": "redis",
                    "creator": "alice"
                },
                {
                    "id": 2,
                    "name": "mongodb",
                    "creator": "bob"
                }
            ]
        '''
        '''
            Commands for accessing sqlite3
            1. type sqlite3 into command
            2. sqlite> prompt will appear
            3. enter .read [File]
            4. .tables will show if file was read
        '''
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = dict_factory
        cur = conn.cursor()
        all_forums = cur.execute(query).fetchall()

        return Response(None, 200)
        #return jsonify(all_forums)
    else:
        return get_response(405)

#list threads in the specified forum GET
@app.route('/forums/<forum_id>', methods=['GET', 'POST'])
def thread(forum_id):
    #creating a new thread in a specified forum
    if request.method == 'POST':
        # auth contains the username and Password
        auth = request.authorization

        if auth_check(auth) is False:
            return get_response(401)

        if forum_id:
            checkifforumexists = query_db('SELECT 1 from Forums where ForumId = ?;', [forum_id])
            if checkifforumexists == []:
                return get_response(404)
            user = query_db('SELECT UserId from Users where Username = ?;', [auth.username])
            userid = dict(user[0]).get('UserId')
            requestJSON = request.get_json()
            conn = get_db()
            cur = conn.cursor()
            cur.execute('INSERT Into Threads (`ForumId`, `ThreadsTitle`) Values (?,?);', (int(forum_id), requestJSON.get('title')))
            thread = cur.execute('SELECT last_insert_rowid() as ThreadId;').fetchall()
            threadid = dict(thread[0]).get('ThreadId')
            timestamp = strftime('%a, %d %b %Y %H:%M:%S', gmtime()) + ' GMT'
            cur.execute('INSERT into Posts (`AuthorId`, `ThreadBelongsTo`, `PostsTimestamp`, `Message`) values (?,?,?,?);', (userid, threadid, timestamp, requestJSON.get('text')))
            conn.commit()
            conn.close()

            return get_response(201, body={}, location=('/forums/'+forum_id+'/'+str(threadid)))
        else:
            return get_response(404)

    elif request.method == 'GET':
        query = 'SELECT id, title, Users.Username as creator, timestamp from (select id, AuthorId, timestamp, title from (select Threads.ThreadId as id, AuthorId, timestamp, Threads.ThreadsTitle as title, Threads.ForumId as Fid from (select ThreadBelongsTo, AuthorId, PostsTimestamp as timestamp, Posts.PostId from Posts) join Threads on ThreadBelongsTo = Threads.ThreadId group by Threads.ThreadId having max(PostId) order by PostId desc) join Forums on Fid = Forums.ForumId where Forums.ForumId = ?) join Users where AuthorId = Users.UserId'
        to_filter = []
        #return all the threads from the forum
        if forum_id:
            conn = sqlite3.connect(DATABASE)
            conn.row_factory = dict_factory
            cur = conn.cursor()
            all_threads = cur.execute(query, [str(forum_id)]).fetchall()
            # If the the quey returns an empty result
            # e.g. http://127.0.0.1:5000/forums/100
            if all_threads == []:
                return get_response(404)
            else:
                return jsonify(all_threads)
        # What is an example of this case?
        if not forum_id:
            return get_response(404)
    else:
        return get_response(405)


# @app.route('/')
# def index():
#     return render_template('index.html')
#
# @app.route('/login')
# def login():
#     return render_template('login.html')
#
# @app.route('/dashboard')
# def dashboard():
#     return render_template('dashboard.html')

#list posts to the specified thread GET
@app.route('/forums/<forum_id>/<thread_id>', methods=['GET', 'POST'])
def post(forum_id, thread_id):
    if request.method == 'POST':
        auth = request.authorization
        if auth_check(auth) is False:
            return get_response(401)

        if forum_id and thread_id:
            checkifforumexists = query_db('SELECT 1 from Forums where ForumId = ?;', [forum_id])
            checkifthreadexists = query_db('SELECT 1 from Threads where ThreadId = ?;', [thread_id])
            if (checkifforumexists == []) or (checkifthreadexists == []):
                return get_response(404)

            user = query_db('SELECT UserId from Users where Username = ?;', [auth.username])
            userid = dict(user[0]).get('UserId')
            requestJSON = request.get_json()
            timestamp = strftime('%a, %d %b %Y %H:%M:%S', gmtime()) + ' GMT'
            conn = get_db()
            cur = conn.cursor()
            cur.execute('INSERT into Posts (`AuthorId`, `ThreadBelongsTo`, `PostsTimestamp`, `Message`) values (?,?,?,?);', (userid, thread_id, timestamp, requestJSON.get('text')))
            conn.commit()
            conn.close()

            return get_response(201)
        else:
            return get_response(404)


    elif request.method == 'GET':
        # check if the forum exists
        checkifforumexists = query_db('SELECT 1 from Forums where ForumId = ?;', [forum_id])
        if checkifforumexists == []:
            return get_response(404)
        # Get all posts from specified thread
        query = 'SELECT Username as author, Message as text, PostsTimestamp as timestamp from Posts join Users on AuthorId = UserId and ThreadBelongsTo = ?;'
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = dict_factory
        cur = conn.cursor()
        # all_threads = cur.execute(query).fetchall()
        allPosts = cur.execute(query, [thread_id]).fetchall()
        conn.close()
        if allPosts == []:
            return get_response(404)
        else:
            return get_response(200, body=allPosts)

    else:
        return get_response(405)

@app.route('/users', methods=['POST'])
def user():
    if request.method == 'POST':
        # curl -X POST -H "Content-Type: application/json" -d '{"username": "tuvwxyz", "password": "123" }' http://localhost:5000/users
        data = request.get_json()
        username = data['username']
        password = data['password']
        query = 'SELECT Username FROM Users WHERE Username=?'
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        # https://stackoverflow.com/questions/16856647/sqlite3-programmingerror-incorrect-number-of-bindings-supplied-the-current-sta
        # Was running into an issue regarding the execute statement and needed to include a ',' after data['username'] in order for the query
        # to be ran
        user = cur.execute(query, (username,)).fetchall()

        if user == []:
            query = 'INSERT INTO Users (Username, Password) VALUES (?, ?);'
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            # Need to use parameterised queries so API can insert values for username and
            # password into the query at the places with a ?
            # sources:
            # https://stackoverflow.com/questions/32945910/python-3-sqlite3-incorrect-number-of-bindings
            # https://stackoverflow.com/questions/32240718/dict-object-has-no-attribute-id
            cur.execute(query, (data['username'], data['password']))
            conn.commit()
            return get_response(201)
        else:
            return get_response(409)

    else:
        return get_response(405)

#create a new user POST

#changes a user's password PUT
@app.route('/users/<username>', methods=['PUT'])
def change_pass(username):
    if request.method == 'PUT':
        # auth contains the username and Password
        auth = request.authorization

        # check_auth returns True or False depending on the credentials
        #check_auth = NewAuth().check_credentials(auth.username, auth.password)
        if auth_check(auth) is False:
            return get_response(401)

        # password contain the value of the new password after getting it from data with the appropriate key
        data = request.get_json()
        password = data.get('password')

        # Query the db to determine if the username has an account
        query = "SELECT Username FROM Users WHERE Username=?"
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        # https://stackoverflow.com/questions/14861162/cursor-fetchall-returns-extra-characters-using-mysqldb-and-python
        # If using fetchall() there is a potential error because it returns a list of tuples rather than just one tuple
        user = cur.execute(query, [data.get('username')]).fetchone()

        if user == None:
            #print ("hah not found")
            return get_response(404)
        # elif auth is False or auth_check(auth) is False:
        #     #print ("wrong password dummy")
        #     return get_response(401)
        elif auth.username != username or auth.username != data.get('username'):
            #print ("hey you, stop it")
            return get_response(409)
        else:
            query = "UPDATE Users SET Password=? WHERE Username=?"
            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()
            cur.execute(query, (password, username))
            conn.commit()

            return get_response(200)

    else:
        return get_response(405)

#from http://flask.pocoo.org/docs/1.0/cli/
# CLI command for initlizing the db
@app.cli.command()
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('init.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
    print ('Database Initilaized')


if __name__ == "__main__":
    app.run()

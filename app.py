from flask import Flask, render_template,url_for,request, redirect,flash,session, send_file, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import random
from functools import wraps
import csv
import io
import re
import difflib
import string
from PIL import Image
from flask_compress import Compress


app = Flask(__name__)

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.memespace

app.secret_key = 'hello mr.nk'

bcrypt = Bcrypt(app)

# Configure Compressing
COMPRESS_MIMETYPES = ['text/html', 'text/css', 'text/xml', 'application/json', 'application/javascript']
COMPRESS_LEVEL = 6
COMPRESS_MIN_SIZE = 500

def configure_app(app):
    Compress(app)

path1 = os.path.abspath('C:/Users/Administrator/PycharmProjects/meme-space/static/images/uploads')    #for others
app.config['UPLOAD'] = path1

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
SIZE_1500 = (1500,1500)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#for csv upload
ALLOWED_DATA_EXTENSIONS = set(['csv'])
def allowed_data_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_DATA_EXTENSIONS


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'username' in session:
            return f(*args, **kwargs)
        else:
            #flash('Login required, please login', 'danger')
            return redirect(url_for('login'))
    return wrap

def is_already_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'username' in session:
            if session['user_type']=='admin':
                return redirect(url_for('mrnk'))
            else:
                ques = db.questions.find()
                que_one = db.questions.find_one()
                return redirect(url_for('questions_page',ques=ques, que_one=que_one))
        else:
            return f(*args, **kwargs)
    return wrap

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/questions_page')
@is_logged_in
def questions_page():
    ques = db.questions.find()
    que_one = db.questions.find_one()
    return render_template('questions_page.html',ques = ques, que_one=que_one)

@app.route('/login/')
@is_already_logged_in
def login():
    return render_template('login.html')

@app.route('/signup/')
@is_already_logged_in
def signup():
    return render_template('signup.html')

@app.route('/instructions/')
@is_logged_in
def instructions():
    return render_template('assets/inst.html')

@app.route('/mrnk/')
@is_logged_in
def mrnk():
    if session['user_type']=='admin':
        return render_template('admin.html')
    return redirect(url_for('index'))

@app.route('/list/')
@is_logged_in
def list():
    if session['user_type'] == 'admin':
        data = db.users.find({'type':'participant'})
        count = db.users.find({'type': 'participant'}).count()
        return render_template('list.html', data=data,count=count)
    return redirect(url_for('index'))

@app.route('/login_user', methods = ['POST'])
@is_already_logged_in
def login_user():
    if request.method == 'POST':
        login_user = db.users.find_one({"email":request.values.get("username")})
        if login_user and bcrypt.check_password_hash(login_user["pass"], request.values.get("password")) :
            if login_user['type'] == 'participant':

                # if login_user['promoted']:
                #     session['username'] = login_user['email']
                #     session['fname'] = login_user['name']
                #     return redirect(url_for('upload'))
                if not login_user['validated']:
                    flash('You are not validated for the test','danger')
                    return redirect(url_for('login'))
                try:
                    if login_user['score'] or login_user['score']==0:
                        flash('Test already taken for this user','danger')
                        return redirect(url_for('login'))
                except:
                    pass
            session['user_type'] = login_user['type']
            session['username'] = login_user['email']
            session['fname'] = login_user['name']
            if session["user_type"] == "admin":
                return redirect(url_for('mrnk'))

            return redirect(url_for('instructions'))
        flash('Invalid username or password','danger')
        return redirect(url_for('login'))
    return redirect(url_for('index'))

@app.route('/logout/')
@is_logged_in
def logout():
    if session['user_type'] == 'participant':
        session.pop('time', None)
    session.pop('username', None)
    session.pop('user_type', None)
    session.pop('fname', None)
    return redirect(url_for('login'))

# @app.route('/add_user')
# #@is_logged_in
# def add_user():
#     return render_template('add_user.html')

@app.route('/upload_file', methods=['GET','POST'])
#@is_logged_in
def upload_file():
    if request.method == 'POST':
        f = request.files['datafile']
        if not allowed_data_file(f.filename):
            flash('Invalid file type, only .csv extension allowed', 'danger')
            return redirect(url_for('add_user'))
        stream = io.StringIO(f.stream.read().decode("UTF8"))
        csv_input = csv.DictReader(stream)
        users_added=0
        line=1
        errors = {}             #dictionary to save errors
        count = db.users.find().count()
        for data in csv_input:
            line=line+1
            #check for required fields
            if not (data['first_name'] and data['last_name'] and data['email']):
                errors[line] = "Data missing"
                continue
            # check for validation
            if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", data['email']):
                errors[line] = "Invalid email"
                continue
            # check for duplicate account
            if db.users.find_one({'email':data['email']}):
                errors[line] = "user already exists"
                continue

            users_added = users_added + 1
            count = count + 1
            rn = str(random.randint(10000, 90000))
            pw_hash = bcrypt.generate_password_hash(rn)
            db.users.insert({'fname':data['first_name'],'lname':data['last_name'],'email':data['email'],'contact':data['contact'],'type':'participant','pass':pw_hash, 'pw':rn})

        flash(str(users_added)+' new User/s added successfully','info')
        return render_template('assets/csv_result.html',errors=errors)

    return redirect(url_for(index))


@app.route('/signup_user', methods=['POST'])
#@is_logged_in
def signup_user():
    if request.method == 'POST':
        email = request.values.get("email")
        existing_user = db.users.find_one({"email": email})

        if existing_user is None:
            name = request.values.get("name").capitalize()
            email = request.values.get("email")
            contact = request.values.get("contact")
            college = request.values.get("college")
            pw = request.values.get("password")
            pw_hash = bcrypt.generate_password_hash(pw)
            db.users.insert({'name': name, 'email': email,'contact': contact, 'type': 'participant','college':college,'pass': pw_hash, 'pw': pw,'validated':0,'promoted':0})
            flash('Account created, login here', 'success')
            return redirect(url_for('login'))
        flash('User already exists', 'danger')
        return redirect(url_for('signup'))
    return redirect(url_for('signup'))

@app.route('/meme/<que_id>')
@is_logged_in
def meme(que_id):
    ques = db.questions.find_one({'_id':ObjectId(que_id)})
    ans_set = db.users.find_one({'email':session['username'],'Response.q_id':que_id},{'Response.ans':1,'Response.q_id':1,'_id':0})
    ans=0
    #print(ans_set)
    try:
        for d in ans_set['Response']:
            try:
                if d['q_id'] == que_id:
                    ans=d['ans']
                    if ques['type'] == 'mcq':
                        ans = int(ans)
            except KeyError:
                pass
    except:
        pass

    next = db.questions.find_one({'_id':{'$gt':ObjectId(que_id)}},{'_id':1})  # after

    return render_template('memepage.html', ques=ques, ans=ans, next=next)

@app.route('/meme_questions')
@is_logged_in
def meme_questions():
    if session['user_type']=='admin':
        ques = db.questions.find().sort('id',-1)
        count = db.questions.find().count()
        return render_template('meme_questions.html',ques=ques,count=count)
    return redirect(url_for('index'))

@app.route('/add_que', methods=['GET','POST'])
@is_logged_in
def add_que():
    if session['user_type']=='admin':
        ques = db.questions.find()
        if request.method == 'POST':
            rn = str(random.randint(1000000, 900000000))
            file = request.files['image']
            if file:
                filename = secure_filename(file.filename)
                i = Image.open(file)
                i.thumbnail(SIZE_1500)
                file.filename=rn
                i.save(os.path.join(app.config['UPLOAD'], rn+'.jpeg'))

                que = request.values.get('que')
                q_type = request.values.get('toggler')
                if q_type == '1':
                    op1 = request.values.get('op1')
                    op2 = request.values.get('op2')
                    op3 = request.values.get('op3')
                    op4 = request.values.get('op4')
                    ans = request.values.get('optradio')
                    db.questions.insert_one({'img':'images/uploads/'+rn+'.jpeg', 'img_name':rn+'.jpeg' ,'que':que,'ans':ans,'options':[op1,op2,op3,op4],'type':'mcq','id':db.questions.find().count()+1})
                else:
                    ans = request.values.get('ans')
                    db.questions.insert_one({'img': 'images/uploads/' + rn+'.jpeg', 'img_name': rn+'.jpeg', 'que': que, 'ans': ans, 'type':'caption','id':db.questions.find().count()+1})

                flash('Question added successfully', 'success')
                return redirect(url_for('meme_questions', ques=ques))
            flash('No file selected', 'danger')
            return redirect(url_for('meme_questions', ques=ques))
    return redirect(url_for('index'))

@app.route('/delete_que/<que_id>')
@is_logged_in
def delete_que(que_id):
    if session['user_type'] == 'admin':
        ques = db.questions.find()
        id = db.questions.find_one({'_id':ObjectId(que_id)})
        img_id = id['img_name']
        os.remove(os.path.join(app.config['UPLOAD'], img_id))
        db.questions.remove({'_id':ObjectId(que_id)})
        flash('Question deleted successfully', 'success')
        return redirect(url_for('meme_questions', ques=ques))
    return redirect(url_for('index'))

@app.route('/response/<que_id>', methods=['POST'])
@is_logged_in
def response(que_id):
    ans = request.values.get('ans')
    db.users.update({'email': session['username'], "Response.q_id": {'$ne': que_id}},{'$addToSet': {"Response": {'q_id': que_id, 'ans': ans}}});
    db.users.update({'email': session['username'], "Response.q_id": que_id},{'$set': {"Response.$.ans":ans}});
    flash('Response recorded successfully','success')
    return redirect(url_for('meme',que_id=que_id))


@app.route('/submit')
@is_logged_in
def submit():
    response = db.users.find_one({'email':session['username']},{'Response.q_id':1,'Response.ans':1,'_id':0})
    print(response)
    score = 0
    try:
        for d in response['Response']:
            try:
                q = db.questions.find_one({'_id':ObjectId(d['q_id'])},{'_id':0,'ans':1,'type':1})
                if q['type'] == 'mcq':
                    if q['ans'] == d['ans']:
                        score = score+1
                else:
                    ans1 = q['ans'].translate({ord(c): None for c in string.whitespace})
                    ans2 = d['ans'].translate({ord(c): None for c in string.whitespace})
                    print(ans1,'  ',ans2)
                    ratio = difflib.SequenceMatcher(None, ans1.lower(), ans2.lower()).ratio()
                    print(ratio)
                    if ratio>0.5:
                        score=score+ratio
            except KeyError:
                pass
    except:
        pass
    print('Score : ',score)
    db.users.update({'email':session['username']},{'$set':{'score':score}})
    flash('Thank you, Your test was submitted successfully','success')
    return redirect(url_for('logout'))

@app.route('/results')
@is_logged_in
def results():
    if session['user_type'] == 'admin':
        result=db.users.find({'type':'participant','score':{'$exists':True}},{'_id':0,'name':1,'college':1,'score':1,'contact':1,'promoted':1,'email':1}).sort('score',-1)
        count = db.users.find({'type': 'participant', 'score': {'$exists': True}},
                               {'_id': 0, 'name': 1, 'college': 1, 'score': 1}).sort('score', -1).count()
        return render_template('assets/results.html',result=result,count=count)
    return redirect(url_for('index'))

@app.route('/validate/<email>')
@is_logged_in
def validate(email):
    if session['user_type']=='admin':
        db.users.update_one({'email':email},{'$set':{'validated':1}})
        data = db.users.find({'type': 'participant'})
        count = db.users.find({'type': 'participant'}).count()
        return redirect(url_for('list', data=data, count=count))
    return redirect(url_for('index'))

# @app.route('/upload')
# #@is_already_logged_in
# def upload():
#     data = db.users.find_one({'email': session['username']})
#     return render_template('assets/upload.html',data=data)

#
# @app.route('/upload_img', methods=['GET','POST'])
# #@is_logged_in
# def upload_img():
#     if request.method == 'POST':
#         data = db.users.find_one({'email': session['username']})
#         rn = str(random.randint(1000000, 900000000))
#         file = request.files['image']
#         if file:
#             filename = secure_filename(file.filename)
#             i = Image.open(file)
#             i.thumbnail(SIZE_1500)
#             file.filename = rn
#             i.save(os.path.join(app.config['UPLOAD'], rn+filename))
#             db.users.insert_one({'email':session['email']},{'$set':{'round2':'images/uploads/'+rn+filename}})
#             flash('uploaded successfully','success')
#             return redirect(url_for('upload',data=data))
#         flash('Somethis went wrong', 'danger')
#         return redirect(url_for('upload', data=data))
#     return redirect(url_for('index'))

@app.route('/delete/<email>')
def delete_user(email):
    if session['user_type']=='admin':
        db.users.remove({'email':email})
        data = db.users.find({'type': 'participant'})
        count = db.users.find({'type': 'participant'}).count()
        return redirect(url_for('list', data=data, count=count))
    return redirect(url_for('index'))

@app.route('/promote/<email>')
def promote(email):
    if session['user_type']=='admin':
        db.users.update_one({'email':email},{'$set':{'promoted':1}})
        result = db.users.find({'type': 'participant', 'score': {'$exists': True}},
                               {'_id': 0, 'name': 1, 'college': 1, 'score': 1, 'contact': 1,'promoted':1,'email':1}).sort('score', -1)
        count = db.users.find({'type': 'participant', 'score': {'$exists': True}},
                              {'_id': 0, 'name': 1, 'college': 1, 'score': 1}).sort('score', -1).count()
        return render_template('assets/results.html', result=result, count=count)
    return redirect(url_for('index'))


# @app.route('/hello/mrnk/')
# def hello_mrnk():
#     pw_hash = bcrypt.generate_password_hash('immrnk')
#     db.users.insert({"fname": 'Admin', "email": 'mrnk', "pass": pw_hash, "type": "admin"})
#     return "success"




if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=80)
    app.jinja_env.cache = {}
    app.run(debug=True)



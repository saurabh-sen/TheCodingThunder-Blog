from flask import Flask, flash, render_template, request, redirect, url_for, session
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine
from flask_mail import Mail
import json
import math
import os
import socket

socket.getaddrinfo('localhost', 8080)
with open("./config.json", 'r') as c:
    params = json.load(c)['params']
local_server = True


app = Flask(__name__)
app.secret_key = 'super-secret-key'
ALLOWED_EXTENTION = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)
mail = Mail(app)
if (local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)
engine = create_engine("mysql://root:@host/db", pool_size=10, max_overflow=20)


class Contacts(db.Model):
    S_no = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_num = db.Column(db.Integer, unique=True, nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    date = db.Column(db.String(12), unique=True)


class Posts(db.Model):
    s_no = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    tagline = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), unique=True, nullable=False)
    content = db.Column(db.Text, unique=True, nullable=False)
    img_file = db.Column(db.String(12), unique=True)
    date = db.Column(db.DateTime)

    def __init__(self, title, tagline, slug, content, img_file, date):
        self.title = title
        self.tagline = tagline
        self.slug = slug
        self.content = content
        self.img_file = img_file
        self.date = date


# ENDPOINTS
@app.route("/")
def home():
    posts = Posts.query.order_by(Posts.date.desc()).all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page=int(page)

    posts = posts[(page-1)*int(params['no_of_posts']): (page-1)*(int(params['no_of_posts']))+ int(params['no_of_posts'])]
    # pagination logic
    # first
    if (page==1):
        prev = "#"
        next = "/?page="+ str(page+1)
    elif (page==last):
        prev = "/?page="+ str(page-1)
        next = "#"
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)

    return render_template("index.html", params=params, posts=posts, prev=prev, next=next)


@app.route("/about/")
def about():
    return render_template("about.html", params=params)


@app.route("/dashboard/", methods=['GET', 'POST'])
def dashboard():
    if ('user' in session and session['user'] == params['admin_user']):
        posts = Posts.query.all()
        return render_template('dashboard.html', params=params, posts=posts)
    if (request.method == 'POST'):
        # redirect him/her to admin panel
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if (username == params['admin_user'] and userpass == params['admin_password']):
            # set the session variable
            session['user'] = username
            post = Posts.query.all()
            # return redirect('/dashboard.html/')

    post = Posts.query.all()
    return render_template("loginpage.html", params=params, post=post, date=datetime.now().strftime('%B %d %Y'))


@app.route("/edit/<string:s_no>", methods=['GET', 'POST'])
def edit(s_no):
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == 'POST':
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()
            if s_no == '0':
                posts = Posts(title=box_title, tagline=tline, slug=slug, content=content, img_file=img_file, date=date)
                db.session.add(posts)
                db.session.commit()
                return render_template('edit.html', params=params, s_no=s_no, posts=posts)
            else:
                post = Posts.query.filter_by(s_no=s_no).first()
                post.title = box_title
                post.tagline = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+s_no)
        posts = Posts.query.filter_by(s_no=s_no).first()
        return render_template('edit.html', params=params, s_no=s_no, posts=posts)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENTION


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if ('user' in session and session['user'] == params['admin_user']):
        if (request.method == 'POST'):
            f = request.files['file']
            f.save(os.path.join(
                app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "File uploaded successfully!"


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/delete/<s_no>", methods=['GET', 'POST'])
def delete(s_no):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(s_no=s_no).one()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route("/contact/", methods=['GET', 'POST'])
def contact():

    if (request.method == 'POST'):
        name1 = request.form.get('name')
        email1 = request.form.get('email')
        phone1 = request.form.get('phone')
        message1 = request.form.get('message')

        entry = Contacts(name=name1, phone_num=phone1, msg=message1, email=email1, date=datetime.now().strftime('%B %d, %Y'))
        db.session.add(entry)
        db.session.commit()
        # mail.send_message(f"New message by {name1}",
        #                   sender=email1,
        #                   recipients=[params['gmail-user']],
        #                   body=f"{message1} \n {phone1}")
        # flash('Your details are successfully submitted. We will get back to you soon', "success")
        return render_template('contact.html')
    return render_template('contact.html')


@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).one()
    return render_template("post_page.html", params=params, post=post)


if __name__ == "__main__":
    # db.create_all()
    db.init_app(app)
    app.run(debug=True)

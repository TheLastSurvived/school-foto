from flask import Flask, render_template, request, url_for, flash, redirect, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_ckeditor import CKEditor
from flask_admin import Admin, BaseView, AdminIndexView, expose
from flask_admin.contrib.sqlamodel import ModelView
import os
from sqlalchemy.sql.expression import func
import json
import uuid
from hashlib import md5
from cloudipsp import Api, Checkout



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'Aewqewqdsfdafeavevre24314#$$#!#$!34T'
app.config['UPLOAD_FOLDER'] = 'static/images/blog'
ckeditor = CKEditor(app)
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def logged_in():
    return session.get('logged')

class MyView(BaseView):
    def is_accessible(self):
        return logged_in()

    def _handle_view(self, name, **kwargs):
        if not logged_in():
            return self.render('admin/login.html')


class AdminIndex(AdminIndexView):
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if 'name' in session:
            user = User.query.filter_by(email=session['name']).first()
            if user.root!=1:
                abort(403)
            else:
                return self.render('admin/dashboard_index.html')
        else:
            abort(401)      

admin = Admin(app, name='DATABASE', template_mode='bootstrap3', index_view = AdminIndex())


class User(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    phone_number = db.Column(db.Integer)
    password = db.Column(db.String(100), unique=True)
    root = db.Column(db.Integer, default=0)
    order_id = db.relationship('Orders', backref='user', lazy='dynamic')

    def __repr__(self):
        return 'User %r' % self.id 


class Articles(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.now)
    category = db.Column(db.String(100))
    text = db.Column(db.Text)
    image_name = db.Column(db.String(100))
    comment = db.relationship('Comments', backref='articles', lazy=True, cascade='all, delete-orphan', passive_deletes = True)

    def __repr__(self):
        return 'Article %r' % self.id 


class Images(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    image_name = db.Column(db.String(500))

    def __repr__(self):
        return 'Image %r' % self.id 
    

class Servises(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(500))
    category = db.Column(db.String(100))
    text = db.Column(db.Text)
    image_name = db.Column(db.String(500))

    def __repr__(self):
        return 'Image %r' % self.id 


class Comments(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(100))
    message = db.Column(db.Text)
    date = db.Column(db.DateTime, default=datetime.now)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))

    def __repr__(self):
        return 'Comment %r' % self.id 


class Orders(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    id_servises = db.Column(db.Integer, db.ForeignKey('servises.id'))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(100))
    date = db.Column(db.DateTime, unique=True)
    id_users = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.Integer, default=0)
    tarif = db.Column(db.String(100))

    def __repr__(self):
        return 'Orders %r' % self.id 

class CommentsView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id','name','message','date','article_id']

class OrdersView(ModelView):
    column_display_pk = True 
    column_hide_backrefs = False
    column_list = ['id','id_servises','name','phone','id_users']


admin.add_view(ModelView(Articles, db.session))
admin.add_view(ModelView(Images, db.session))
admin.add_view(CommentsView(Comments, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Servises, db.session))
admin.add_view(OrdersView(Orders, db.session))

@app.route('/')
def index():
    articles = Articles.query.order_by(func.random()).limit(5).all()
    return render_template("index.html", articles=articles)



@app.route('/initiate_payment/<int:id>')
def initiate_payment(id):
    order = Orders.query.get(id)
    order.status = 1
    db.session.commit()
    api = Api(merchant_id=1396424,
          secret_key='test')
    checkout = Checkout(api=api)
    data = {
        "currency": "KRW",
        "amount": int(order.tarif + "00")
    }
    url = checkout.url(data).get('checkout_url')
    return redirect(url)


@app.route('/blog')
def blog():
    articles = Articles.query.order_by(Articles.date.desc()).all()
    if request.method == 'GET':
        seach = request.args.get('seach')
        if seach:
            seach= seach.capitalize()
            seach = "%{}%".format(seach)
            articles = Articles.query.filter(Articles.category.like(seach)).all()
    return render_template("blog.html" ,articles=articles)

@app.route('/blog/<int:id>',methods=['GET','POST'])
def blog_single(id):
    article = Articles.query.get(id)
    if not article:
        abort(404)
    count_comments = len(article.comment)
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            message = request.form.get('message')
            comment = Comments(name=name, message=message, article_id=id)
            db.session.add(comment)
            db.session.commit()
            flash("Сообщение отправлено!", category="ok")
            return redirect(url_for("blog_single", id=id))
        except:
            flash("Произошла ошибка!", category="bad")
            return redirect(url_for("blog_single", id=id))
    return render_template("single.html", article=article, count_comments=count_comments)

@app.route('/services', methods=['GET', 'POST'])
def services():
    services = Servises.query.all()
    orders = Orders.query.all()
    today = datetime.now()
    if request.method == 'POST':
        try:
            today = datetime.now()
            id = request.form.get('id')
            name = request.form.get('name')
            phone = request.form.get('phone')
            date = request.form.get('date')
            time = request.form.get('time')
            tarif = request.form.get('tarif')
            full = date + "-" + time
            datetime_object = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            result = (today - datetime.strptime(date, '%Y-%m-%d')).total_seconds()
            if datetime_object < today:
                flash("Дата ("+full+") выбрана неправильно, так как этот день уже прошел!", category="bad")
                return redirect(url_for("services"))
            datetime_object = datetime.strptime(full, '%Y-%m-%d-%H:%M')
            total_user = User.query.filter_by(email=session['name']).first()
            order = Orders(id_servises=id,id_users = total_user.id,tarif=tarif, name=total_user.email,phone=total_user.phone_number,date=datetime_object)
            db.session.add(order)
            db.session.commit()
            flash("Вы записались! Ожидайте ответ оператора.", category="ok")
            return redirect(url_for("services"))
        except:
            flash("Запись на это время невозможна!", category="bad")
            db.session.rollback()
            return redirect(url_for("services"))
    return render_template("services.html",services=services,orders=orders)


@app.route('/add-blog',methods=['GET','POST'])
def add_blog():
    user = User.query.filter_by(email=session['name']).first()
    if user.root!=1:
        abort(403)
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            category = request.form.get('category')
            image = request.files['image']
            text = request.form.get('ckeditor')
            filename = secure_filename(image.filename)
            pic_name = str(uuid.uuid4()) + "_" + filename
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
            
            article = Articles(title=title,category=category,text=text,image_name=pic_name)
            db.session.add(article)
            db.session.commit()
            flash("Запись добавлена!", category="ok")
            return redirect(url_for("add_blog"))
        except:
            flash("Произошла ошибка!", category="bad")
            return redirect(url_for("add_blog"))
    return render_template("add-blog.html")


@app.route('/edit-article/<int:id>',methods=['GET','POST'])
def edit_article(id):
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            category = request.form.get('category')
            text = request.form.get('ckeditor')
            image = request.files['image']
            article = Articles.query.filter_by(id=id).first()
            article.title = title
            article.category = category
            article.text = text
            if image:
                filename = secure_filename(image.filename)
                pic_name = str(uuid.uuid4()) + "_" + filename
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
                article.image_name = pic_name
            db.session.commit()
            flash("Запись обновлена!", category="ok")
            return redirect(url_for("blog_single",id=id))
        except:
            flash("Произошла ошибка!", category="bad")
            return redirect(url_for("blog_single",id=id))

@app.route('/delete-article/<int:id>')
def delete_article(id):
    obj = Articles.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    return redirect('/blog')

@app.route('/delete-comment/<int:id>/<int:article_id>')
def delete_comment(id, article_id):
    obj = Comments.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    return redirect(url_for("blog_single",id=article_id))

@app.route('/add-img',methods=['GET','POST'])
def add_img():
    user = User.query.filter_by(email=session['name']).first()
    if user.root!=1:
        abort(403)
    image_from_page = Images.query.order_by(Images.id.desc()).all()
    if request.method == 'POST':
        try:
            image = request.files['image']
            filename = secure_filename(image.filename)
            pic_name = str(uuid.uuid4()) + "_" + filename
            images = Images(image_name=pic_name)
            db.session.add(images)
            db.session.commit()
            
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
            flash("Изображение загружено!", category="ok")
            return redirect(url_for("add_img"))
        except:
            flash("Произошла ошибка!", category="bad")
            return redirect(url_for("add_img"))
    return render_template("add-img.html",images=image_from_page)


@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        try:
            name = request.form.get('FullName')
            phone = request.form.get('PhoneNumber')
            email = request.form.get('Email')
            password = request.form.get('password')
            user = User(name=name,email=email,phone_number=phone,password=md5(password.encode()).hexdigest())
            db.session.add(user)
            db.session.commit()
            flash("Регистрация прошла успешно!", category="ok")
            return redirect(url_for("reg"))
        except:
            flash("Произошла ошибка! Проверьте введенные данные!", category="bad")
            db.session.rollback()
            return redirect(url_for("reg"))
    return render_template("reg.html")


@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        email = request.form.get('Email')
        password = md5(request.form.get('password').encode()).hexdigest()
        user = User.query.filter_by(email=email,password=password).first()
        if user:
            session['name'] = User.query.filter_by(email=email).first().email
            return redirect(url_for("index"))
        else:
            flash("Неправильная почта или пароль!", category="bad")
            return redirect(url_for("auth"))
    return render_template("auth.html")


@app.route('/contacts', methods=['GET', 'POST'])
def contacts():
    return render_template("contact.html")


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    id_total_user = User.query.filter_by(email=session['name']).first().id
    order_user  = Orders.query.filter_by(id_users=id_total_user).all()
    order_servises_list = []
    for el in order_user:
        order_servises_list.append(Servises.query.filter_by(id=el.id_servises).first())
    return render_template("profile.html",zip=zip, order_user= order_user,order_prices_list=order_servises_list)

@app.route('/admin_list', methods=['GET', 'POST'])
def admin_list():
    root = User.query.filter_by(email=session['name']).first().root
    if root!=1:
        abort(403)
    order_user  = Orders.query.all()
    order_user_list = []
    order_prices_list = []

    for el in order_user:
        order_user_list.append(User.query.filter_by(id=el.id_users).first())

    for el in order_user:
        order_prices_list.append(Servises.query.filter_by(id=el.id_servises).first())

    return render_template("admin.html",order_user=order_user,order_user_list=order_user_list,order_prices_list=order_prices_list,zip=zip)

@app.route('/delete_order/<int:id>')
def delete_order(id):
    obj = Orders.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    return redirect('/profile')


@app.route('/delete_order_admin/<int:id>')
def delete_order_admin(id):
    obj = Orders.query.filter_by(id=id).first()
    db.session.delete(obj)
    db.session.commit()
    return redirect('/admin_list')

@app.route('/logout-admin')
def logout_admin():
    session.pop('logged', None)
    return redirect('/')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(403)
def forbidded(e):
    return render_template('403.html'), 403

@app.errorhandler(401)
def forbidded(e):
    return render_template('401.html'), 401

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.context_processor
def inject_user():
    return dict(
    category=db.session.query(Articles.category).distinct().all(),
    )

@app.context_processor
def inject_user():
    def get_user_name():
        if 'name' in session:
            return User.query.filter_by(email=session['name']).first()
    return dict(active_user=get_user_name())


@app.route('/logout')
def logout():
    session.pop('name', None)
    return redirect('/')


@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')
    # Проверка расширения файла
    extension = f.filename.split('.')[-1].lower()
    if extension not in ['jpg', 'gif', 'png', 'jpeg']:
        return upload_fail(message='Только изображения!')
    
    # Сохранение файла
    filename = secure_filename(f.filename)
    pic_name = str(uuid.uuid4()) + "_" + filename
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
    
    # Возвращаем URL изображения
    url = url_for('static', filename='images/blog/' + pic_name, _external=True)
    return upload_success(url=url)

def upload_success(url, message=''):
    return json.dumps({
        'uploaded': 1,
        'fileName': url.split('/')[-1],
        'url': url
    })

def upload_fail(message=''):
    return json.dumps({
        'uploaded': 0,
        'error': {'message': message}
    })

if __name__ == '__main__':
    app.run(debug=True)
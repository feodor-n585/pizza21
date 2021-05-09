from flask import Flask, render_template, request, redirect, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_login import UserMixin
import time
import math
#from UserLogin import UserLogin
import os
import sys
from flask_sqlalchemy import SQLAlchemy
from ya_map import map
from geocoder import geocoder_get_address
from sqlalchemy import orm
import datetime
from sqlalchemy import join


#= sys.argv[0]
ABS_PATH  = os.path.abspath(os.path.dirname(sys.argv[0]))
UPLOAD_FOLDER = 'static/img/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)

app.secret_key = '1258fd890fsdfs123456fl789'
DEBUG = True
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#app.config['MAX_CONTENT_LENGTH'] = 16 * 255 * 255


basket_count = 0

app.add_template_global(name='basket_count', f=basket_count)

db = SQLAlchemy(app)
from db_def import *

login_manager = LoginManager(app)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    image = db.Column(db.Text, default="jpg.jpg")
    price = db.Column(db.Integer, nullable=False)
    about = db.Column(db.Text)
    recept_id = db.Column(db.Integer, default=0)
    isActive = db.Column(db.Boolean, default=True)
    #  recept_id = db.Column(db.Integer, nullable=False)
    #recept = db.relationship('recept', backref='Item', lazy='dynamic')  # 1:1 Item <-> Recept
    # text = db.Column(db.Text, nullable=False)         uselist=False
    def __repr__(self):
        return self.title


class Recept(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer) #, db.ForeignKey('item.id'))
    about = db.Column(db.Text)
    recept = db.Column(db.Text)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default='client')
    tm = db.Column(db.Integer, nullable=False)
    ban = db.Column(db.Boolean, nullable=False, default=False)
    isActive = db.Column(db.Boolean, default=True)


    #    role = db.Column(db.Text, db.ForeignKey('Role.role'))
    #    role = db.relationship('Role', backref='role', lazy='dynamic')
    #    rl = db.relationship('Role', backref='User')
#    def __repr__(self):
#        return self.name

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Text, default='some_role')
#    role = db.relationship('User', backref='role', lazy='dynamic')
#    role = db.Column(db.Text, db.ForeignKey('User.rl'))
#    user_id = db.Column(db.Integer, db.ForeignKey('User.id'))
    title = db.Column(db.Text, default='some_title')
    admin = db.Column(db.Boolean, default=False)
    creation = db.Column(db.Boolean, default=False)
    delivery = db.Column(db.Boolean, default=False)
    stock = db.Column(db.Boolean, default=False)
    order = db.Column(db.Boolean, default=False)
    history = db.Column(db.Boolean, default=False)
    isActive = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return self.role

class Basket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer)
    item_quantity = db.Column(db.Integer)
    item_price = db.Column(db.Integer)

    def __repr__(self):
        count = 0
        for elem in self:
            count = count + elem.item_quantity
        return count

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_time = db.Column(db.DateTime, default=datetime.datetime.now)
    user_id = db.Column(db.Integer, default=0)
    delivery_address_id = db.Column(db.Integer)
    phone = db.Column(db.Text)
    summ = db.Column(db.Integer)
    note = db.Column(db.Text)
    Table = orm.relation("Table", back_populates='order')
#    news = orm.relation("News", back_populates='user') #User -> Order

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer)
    item_quantity = db.Column(db.Integer)
    item_price = db.Column(db.Integer)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    order = orm.relation('Order')
#    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
#    user = orm.relation('User') #News -> Order_table

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coord = db.Column(db.Text)
    adr = db.Column(db.Text)
    note =  db.Column(db.Text)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def basket_erase():
    print("Очищаем корзину")
    basket = Basket.query.all()
    try:
        for i in basket:
            db.session.delete(i)
        db.session.commit()
        return
    except:
        return "Произошла ошибка очистки корзины"


basket = Basket()

@app.context_processor
def inject_user():
    return dict(basket_count=basket_count)

@login_manager.user_loader
def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))


@app.route('/', methods=['POST', 'GET'])
def index():
    global basket
    if request.method == "POST":
        id = request.form['id']
        item = Item.query.get(id)

        if request.form["btn"] == "Редактировать":
            if item.recept_id > 0:
                recept = Recept.query.get(item.recept_id)
            else:
                recept = Recept.query.get(999999)
            return render_template("edit_item.html", item=item, recept=recept)

        if request.form["btn"] == "Заказать":
            print("Кладем в корзину товар ", item)
            basket = Basket.query.filter_by(item_id=id).first()
            if not basket: # такого товара еще нет в корзине
                basket = Basket(item_id=item.id, item_quantity=1, item_price=item.price)
            else:   # такой товар уже есть в корзине
                basket.item_quantity += 1
                try:
                    #db.session.add(basket)
                    db.session.commit()
                except:
                    return "Произошла ошибка добавления имеющегося товара в корзину"
                return redirect('/')
            #return render_template("edit_item.html", item=item)
            try:
                db.session.add(basket)
                db.session.commit()
                return redirect('/')
            except:
                return "Произошла ошибка добавления нового товара в корзину"


        if request.form["btn"] == "Убрать":
            item.isActive = False
        if request.form["btn"] == "Продавать":
            item.isActive = True

        print("Меняем активность товара id=", id)
        try:
#            db.session.delete(item)
            db.session.commit()
            return redirect('/')
        except:
            return "Произошла ошибка удаления товара"

    else:
        items = Item.query.order_by(-Item.isActive, Item.title).all()   #, Item.price
        basket = Basket.query.all()
        count = 0
        for elem in basket:
            count = count + elem.item_quantity
        global basket_count
        basket_count = count
        return render_template("index.html", items=items, recept=Recept.query.all(), basket=basket_count)


@app.route('/basket', methods=['POST', 'GET'])
def basket():
    global basket
    global basket_count
    if request.method == "POST":
        basket = Basket.query.all()
        l = len(basket)+3
        for i in range(1, len(basket)+3):
            s = 'btn'+str(i)
            d = 'del'+str(i)
            r = request.form.get(s)
            if r == '+':
                # basket_id = request.form['basket_id']
                basket = Basket.query.get(i)
                basket.item_quantity += 1
            elif r == '-':
                # basket_id = request.form['basket_id']
                basket = Basket.query.get(i)
                if basket.item_quantity > 1:
                    basket.item_quantity -= 1
            else:
                r = request.form.get(d)
                if r == 'x':
                    basket = Basket.query.get(i)
                    db.session.delete(basket)
        try:

            db.session.commit()
                # return redirect('/')
        except:
            return "Произошла ошибка инкримента товара"
        #return redirect('/basket')
#        if request.form["btn"] == "Очистить корзину":
        if  request.form.get("btn") == "Очистить корзину":
            basket_erase()
        elif request.form.get("btn") == "Оформить заказ":
            return redirect('/delivery')

        return redirect('/basket')
    else:
        basket = Basket.query.order_by(Basket.id).all()
        items = Item.query.all()
        #basket = Basket.query.all()
        summ = 0
        basket_count = 0
        for elem in basket:
            item = Item.query.get(elem.item_id)
            summ = summ + item.price * elem.item_quantity
            basket_count = basket_count +  elem.item_quantity
        return render_template('basket.html', bsk=basket, item=items, summ=summ)

@app.route('/delivery', methods=['POST', 'GET'])
def delivery():
    return render_template("deliveryCalculaor.html")

@app.route('/edit_delivery', methods=['POST', 'GET'])
def edit_delivery():
    global basket
    if request.method == "POST":

        if request.form.get("btn") == "Оформить заказ":
            address_id = request.form['address_id']
            adr = Address.query.get(address_id)
            adr.adr = request.form['address']
            adr.note = request.form['note']
            # Создадим новый заказ
            user = current_user
            if not current_user.is_anonymous:
                usr = current_user.id
            else:
                usr = 0
            ord = Order(delivery_address_id=address_id, user_id=usr, note=adr.note)
            print("Записываем новый заказ")
            try:
                db.session.add(ord)
                db.session.commit()
            except Exception as e:
                print("Произошла ошибка записи нового заказа ", e)
            # Запишем в табличную часть содержитое корзины и очистим корзину
            tbl = Table()
            bsk = Basket.query.all()
            for el in bsk:
                tbl = Table(order_id=ord.id, item_id=el.item_id, item_quantity=el.item_quantity, item_price=el.item_price)

                print("Формируем табличную часть заказа")
                try:
                    db.session.add(tbl)
                    db.session.delete(el)
                    db.session.commit()
                except Exception as e:
                    print("Произошла ошибка записи таблицы заказа ", e)

                c = tbl.order.date_time
#                d = ord.table
#                s = orm.Session(bind=e)
#                f = db.session.query(Table).join(Order).filter(id=ord.id)

            tbl = Table.query.filter_by(order_id=ord.id).all()

            return render_template("order.html", order=ord, table=tbl)

        else: # мы пришли сюда с друной страницы
            d_cost = request.form['d_cost']
            d_coord = request.form['d_coord']
            #d_note = request.form['d_note']
            #d_long = d_coord.split(",")[1]
            #d_lat = d_coord.split(",")[0]
            #d_coord =  d_long + "," + d_lat

            if d_coord:
                d_coord = d_coord.partition(",")[2] + d_coord.partition(",")[1] + d_coord.partition(",")[0]
                d_adr = geocoder_get_address(d_coord)
            else:
                d_coord = ""
                d_adr=""
    #        adr = Address.query.get(id)
            adr = Address(coord=d_coord, adr=d_adr)
            print("Введен новый адрес ")
        try:
            db.session.add(adr)
            db.session.commit()
        except Exception as e:
            print( "Произошла ошибка записи нового адреса ", e)

        filename = 'map_d.png'

        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), app.config['UPLOAD_FOLDER'], filename)
#        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        map(d_adr, path)

        return render_template("edit_delivery.html", address=adr)

@app.route('/orders', methods=['POST', 'GET'])
def orders():
    return render_template("order.html", order=0)


@app.route('/about', methods=['POST', 'GET'])
def about():
    address = "Павловск ул. Декабристов, 16"
    address = "Россия, Санкт - Петербург, Пушкинский\
    район, Павловск, улица\
    Декабристов, 16"
    path = 'static/img/'
    filename = 'map.png'


    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), app.config['UPLOAD_FOLDER'], filename)
#    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#    path=filename
    map(address, path)
    return render_template("about.html", address=address)


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        if len(request.form['email']) > 4 and len(request.form['password1']) > 4 and request.form['password1'] == request.form['password2']:
            email = request.form['email']
            if User.query.filter_by(email=email).first():
                flash("Пользователь с таким email уже существует")
                print("Пользователь с таким email уже существует")
                return redirect('/register')
            hash = generate_password_hash(request.form['password1'])
            name = email
            name = email.split('@')[0]
            tm = math.floor(time.time())
            user = User(name=name, email=email, password=hash, tm=tm)
            print("Введен новый пользователь ", name, " ", hash)
            try:
                db.session.add(user)
                db.session.commit()
                # return redirect('/')
            except:
                return "Произошла ошибка записи нового пользователя"

        else:
            flash("Неверно заполнены поля формы")
    users = User.query.order_by(User.name).all()
    return render_template("register.html", data=users)

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
#        user = User.getUserByEmail(request.form['email'])
        email = request.form['email']
        print(email)
        user = User.query.filter_by(email=email).first()
        print(user)
        if user and check_password_hash(user.password, request.form['password']):
            print("Вы авторизовались")
            flash("Вы авторизовались")
            rm = True if request.form.get('remainme') else False
#            userlogin = UserLogin().create(user)
#            login_user(user, remember=False)
            login_user(user, remember=rm)
            return redirect('/profile')
        flash("Неверная пара логин/пароль", "error")
        print("Неверная пара логин/пароль", "error")
    return render_template("login.html")


@app.route('/create', methods=['POST', 'GET'])
@login_required
def create():
    if request.method == "POST":
        title = request.form['title']
        price = request.form['price']
        item = Item(title=title, price=price)
        print("Введен новый товар ", title)
        try:
            db.session.add(item)
            db.session.commit()
            return redirect('/login')
        except:
            return "Произошла ошибка записи нового товара"
    else:
        print("Ничего не добавляем, request.method=", request.method)
        return render_template("create.html")

@app.route('/profile')
@login_required
def profile():
    return render_template("profile.html", data=current_user)

@app.route('/admin')
@login_required
def admin():
#    users = get_permission()
#    global users

#    roles = Role.query.all()
#    users = db.session.query(User, Role).join(User, User.role==Role.role).all()
#    pr = db.relationship('Role', backref=='User', uselist=False)
    users = User.query.all()
    roles = Role.query.all()
    return render_template("admin.html", data=users, roles=roles)

@app.route('/admin_user', methods=['POST', 'GET'])
@login_required
def admin_user():
    if request.method == "POST":
        id = request.form['id']
        user = User.query.filter_by(id=id).first()
    #    users = db.session.query(User, Role).join(User, User.role==Role.role).all()
    #    pr = db.relationship('Role', backref=='User', uselist=False)
    roles = Role.query.all()
    #return render_template("admin.html", data=User.query.all(),roles=Role.query.all())
    return render_template("admin_user.html", data=user, roles=roles)

@app.route('/admin_role', methods=['POST', 'GET'])
def admin_role():
    if request.method == "POST":
        id = request.form['id']
        role = Role.query.filter_by(id=id).first()
    return render_template("admin_role.html", role=role)

@app.route('/save_role', methods=['POST', 'GET'])
@login_required
def save_role():

    if request.method == "POST":
        id = request.form['id']
#        rl = Role.query.filter_by(id=id).first()
        rl = Role.query.get(id)
        rl.role = request.form['role']
        rl.title = request.form['title']

        if request.form.get('admin'):
            rl.admin = True
        else:
            rl.admin = False

        if request.form.get('creation'):
            rl.creation = True
        else:
            rl.creation = False

        if request.form.get('delivery'):
            rl.delivery = True
        else:
            rl.delivery = False

        if request.form.get('stock'):
            rl.stock = True
        else:
            rl.stock = False

        if request.form.get('order'):
            rl.order = True
        else:
            rl.order = False

        if request.form.get('history'):
            rl.history = True
        else:
            rl.history = False

        if request.form.get('isActive'):
            rl.isActive = True
        else:
            rl.isActive = False

        #user = User(name=name, email=email, role=role, tm=tm, ban=ban)
        print("Сохраняем отредактированную роль ", rl.role)
        try:
            db.session.commit()
            # return redirect('/')
        except:
            return "Произошла ошибка записи отредактированной роли"
        users = User.query.order_by(User.name).all()
#        return redirect('/admin_user')
        roles = Role.query.all()
        return render_template("admin.html", data=users, roles=roles)

    return redirect('/admin_user')
#    return render_template("admin_user.html", data=user, roles=roles)

@app.route('/new_role', methods=['POST', 'GET'])
@login_required
def new_role():
#    if request.method == "POST":
    if True:
        rl = Role()
        #print("Введена новая роль ", role)
        try:
            db.session.add(rl)
            db.session.commit()
#            users = User.query.order_by(User.name).all()
            #        return redirect('/admin_user')
        except:
            return "Произошла ошибка записи новой роли"
        #role = Role.query.all()
        return render_template("admin_role.html", role=rl)

    else:
        print("Ничего не добавляем, request.method=", request.method)
        return render_template("admin.html")

@app.route('/save_item', methods=['POST', 'GET'])
@login_required
def save_item():
    if request.method == "POST":
        print("Saving item")
        action = request.form['form_id']
        if action == "save":
            title = request.form['title']
            price = request.form['price']

            if request.form.get('isActive'):
                isActive = True
            else: isActive = False
            id = request.form['id']
            item = Item.query.get(id)
            if item.recept_id > 0:
                recept = Recept.query.get(item.recept_id)
                if recept == None:
                    item.recept_id = 999999
            item.title = title
            item.price = price
            item.image = request.form['image']
            image_select = request.form['image_select']
            if image_select:
                item.image = image_select
            item.about = request.form['item_about']
            item.isActive = isActive

            if request.form['btn'] == "Редактировать рецепт":
                return render_template("edit_recept.html", item=item, recept=Recept.query.get(id))
            elif request.form['btn'] == "Сохранить изменения":

                print("Сохраняем отредактированный товар", title)
                try:
                    db.session.commit()
                # return redirect('/')
                except:
                    return "Произошла ошибка записи отредактированного товара"
        else: # не save а upload, наверное
            print("Uploading item image")
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))  # +
            #return redirect('/save_item')
            id = request.form['id']
            item = Item.query.get(id)

            item.image = filename
            print("Сохраняем отредактированный товар", item.title)
            try:
                db.session.commit()
        # return redirect('/')
            except:
                return "Произошла ошибка записи отредактированного товара"

        return redirect('/')
#        render_template("index.html")

@app.route('/upload_item', methods=['POST', 'GET'])
@login_required
def upload_item():
    print("Uploading item image")
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))  # +
    return redirect('/save_item')


@app.route('/save_recept', methods=['POST', 'GET'])
@login_required
def save_recept():
    if request.method == "POST":
#        title = request.form['title']
#        price = request.form['price']

#        if request.form.get('isActive'):
#            isActive = True
#        else: isActive = False
        id = request.form['id']
        item = Item.query.get(id)
#        if item.recept_id > 0:
        r_id = item.recept_id
        rc = Recept.query.get(r_id)
        if rc == None:
            rc = Recept()

            rc.id = id
            db.session.add(rc)
#        recept.about = request.form['about']
        rc.recept = request.form['recept']
        item = Item.query.get(id)
        item.recept_id = id
#        item = Item.query.filter_by(id=id).first()
#        tm = math.floor(time.time())
        #user = User(name=name, email=email, role=role, tm=tm, ban=ban)
#        item.title = title
#        item.price = price
#        item.isActive = isActive

#        if request.form["btn"] == "Сохранить рецепт":
            #            return render_template("edit_item.html", item=item, recept=Recept.query.get(id))
#            return render_template("edit_recept.html", item=item, recept=Recept.query.get(id))

        print("Сохраняем отредактированный рецепт")
        try:
            db.session.commit()
            # return redirect('/')
        except:
                return "Произошла ошибка записи отредактированного рецепта"
#        users = User.query.order_by(User.name).all()
#        return redirect('/admin_user')
#        roles = Role.query.all()
        return redirect('/')
#        render_template("index.html")



@app.route('/save_user', methods=['POST', 'GET'])
@login_required
def save_user():
#    users = get_permission()
    user = current_user

    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        role = request.form['select_role']
        if request.form.get('ban'):
            ban = True
        else: ban = False
        if request.form.get('isActive'):
            isActive = True
        else:
            isActive = False

        id = request.form['id']
        user = User.query.get(id)
        #user = User.query.filter_by(id=id).first()
        user.name = name
        user.email = email
        user.phone = phone
        user.role = role
        user.ban = ban
        user.isActive = isActive
#        if request.form.get('delete'):
#            db.session.delete(user)

        print("Сохраняем отредактированного пользователя", name, " ", hash)
        try:
            #db.session.merge(user)
            db.session.commit()
            # return redirect('/')
        except:
            return "Произошла ошибка записи отредактированного пользователя"
        users = User.query.order_by(User.name).all()
#        return redirect('/admin_user')
        roles = Role.query.all()
        return render_template("admin.html", data=users, roles=roles)

#    roles = Role.query.all()
#    users = db.session.query(User, Role).join(User, User.role==Role.role).all()
#    pr = db.relationship('Role', backref=='User', uselist=False)

    return redirect('/admin_user')
#    return render_template("admin_user.html", data=user, roles=roles)

@app.route('/logout')
@login_required
def logout():
    logout_user()
#    return redirect(url_for('index'))
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)

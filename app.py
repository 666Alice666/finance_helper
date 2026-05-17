from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config
from extensions import db, login_manager

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'registr'


@app.route("/registration", methods=['GET', 'POST'])
def registr():
    if request.method == 'POST':
        action = request.form.get('action')

        email = request.form.get('email')
        password = request.form.get('password')

        name = request.form.get('name')

        if name:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Этот email уже зарегистрирован!')
                return redirect(url_for('registr'))

            new_user = User(name=name, email=email)
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            flash('Регистрация успешна! Теперь войдите.')
            return redirect(url_for('registr'))

        else:
            user = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                from flask_login import login_user
                login_user(user)
                flash('Вы успешно вошли!')
                return redirect(url_for('main'))
            else:
                flash('Неверный email или пароль')
                return redirect(url_for('registr'))

    return render_template('registr.html')


@app.route("/main")
def main():
    return render_template('main.html')


@app.route("/history")
def history():
    return render_template('history.html')


@app.route("/statistics")
def statistics():
    return render_template('statistics.html')


@app.route("/debts")
def debts():
    return render_template('debts.html')


from models import User


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


if __name__ == '__main__':
    app.run(debug=True)
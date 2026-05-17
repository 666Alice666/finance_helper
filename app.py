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
    from flask_login import current_user

    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    income_cats = Category.query.filter_by(user_id=current_user.id, type='income').all()
    expense_cats = Category.query.filter_by(user_id=current_user.id, type='expense').all()

    return render_template('main.html',
                           user_name=current_user.name,
                           income_cats=income_cats,
                           expense_cats=expense_cats)


@app.route("/history")
def history():
    return render_template('history.html')


@app.route("/statistics")
def statistics():
    return render_template('statistics.html')


@app.route("/debts")
def debts():
    return render_template('debts.html')


from models import User, Category, Transaction


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# === Маршрут для добавления транзакции ===
@app.route("/add_transaction", methods=['POST'])
def add_transaction():
    from flask_login import current_user, login_required
    from flask import flash, redirect, url_for

    # Защита: только для авторизованных
    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    # Получаем данные из формы
    trans_type = request.form.get('type')  # 'income' или 'expense'
    category_name = request.form.get('category')
    amount = request.form.get('amount')
    description = request.form.get('description', '')

    # Ищем или создаём категорию
    category = Category.query.filter_by(
        user_id=current_user.id,
        name=category_name,
        type=trans_type
    ).first()

    if not category:
        category = Category(
            user_id=current_user.id,
            name=category_name,
            type=trans_type
        )
        db.session.add(category)
        db.session.commit()

    # Создаём транзакцию
    new_transaction = Transaction(
        user_id=current_user.id,
        category_id=category.id,
        amount=float(amount),
        type=trans_type,
        description=description
    )

    db.session.add(new_transaction)
    db.session.commit()

    flash('Запись добавлена!')
    return redirect(url_for('main'))


@app.route("/add_category", methods=['POST'])
def add_category():
    from flask_login import current_user, login_required
    from flask import flash, redirect, url_for

    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    name = request.form.get('name')
    cat_type = request.form.get('type')

    existing = Category.query.filter_by(
        user_id=current_user.id,
        name=name,
        type=cat_type
    ).first()

    if existing:
        flash('Такая категория уже есть')
    else:
        new_category = Category(
            user_id=current_user.id,
            name=name,
            type=cat_type
        )
        db.session.add(new_category)
        db.session.commit()
        flash('Категория добавлена!')

    return redirect(url_for('main'))


if __name__ == '__main__':
    app.run(debug=True)
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
    from flask_login import current_user

    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    transactions = Transaction.query.filter_by(user_id=current_user.id) \
        .order_by(Transaction.created_at.desc()).all()

    return render_template('history.html', transactions=transactions)


@app.route("/statistics")
def statistics():
    from flask_login import current_user
    from sqlalchemy import func

    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    total_income = db.session.query(func.sum(Transaction.amount)) \
                       .filter_by(user_id=current_user.id, type='income').scalar() or 0
    total_expense = db.session.query(func.sum(Transaction.amount)) \
                        .filter_by(user_id=current_user.id, type='expense').scalar() or 0

    balance = total_income - total_expense
    difference = abs(total_income - total_expense)

    total = total_income + total_expense
    income_percent = round((total_income / total * 100), 1) if total > 0 else 0
    expense_percent = round((total_expense / total * 100), 1) if total > 0 else 0

    income_by_cat = db.session.query(Category.name, func.sum(Transaction.amount)) \
        .join(Transaction).filter_by(user_id=current_user.id, type='income') \
        .group_by(Category.name).all()

    expense_by_cat = db.session.query(Category.name, func.sum(Transaction.amount)) \
        .join(Transaction).filter_by(user_id=current_user.id, type='expense') \
        .group_by(Category.name).all()

    income_labels = [row[0] for row in income_by_cat]
    income_values = [float(row[1]) for row in income_by_cat]

    expense_labels = [row[0] for row in expense_by_cat]
    expense_values = [float(row[1]) for row in expense_by_cat]

    return render_template('statistics.html',
                           total_income=total_income,
                           total_expense=total_expense,
                           balance=balance,
                           difference=difference,
                           income_percent=income_percent,
                           expense_percent=expense_percent,
                           income_labels=income_labels,
                           income_values=income_values,
                           expense_labels=expense_labels,
                           expense_values=expense_values)


@app.route("/debts")
def debts():
    return render_template('debts.html')


from models import User, Category, Transaction


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/add_transaction", methods=['POST'])
def add_transaction():
    from flask_login import current_user, login_required
    from flask import flash, redirect, url_for

    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    trans_type = request.form.get('type')
    category_name = request.form.get('category')
    amount = request.form.get('amount')
    description = request.form.get('description', '')

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


@app.route("/delete_transaction/<int:transaction_id>", methods=['POST'])
def delete_transaction(transaction_id):
    from flask_login import current_user

    if not current_user.is_authenticated:
        return redirect(url_for('registr'))

    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()

    if transaction:
        db.session.delete(transaction)
        db.session.commit()
        flash('Запись удалена')
    else:
        flash('Ошибка: запись не найдена или нет прав')

    return redirect(url_for('history'))


if __name__ == '__main__':
    app.run(debug=True)
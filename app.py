from functools import wraps

from flask import Flask, abort, jsonify, render_template, request, redirect, url_for, flash
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError, generate_csrf
from sqlalchemy import func, inspect, text

from config import Config
from extensions import db, login_manager
from models import Category, Transaction, User

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'registr'
csrf = CSRFProtect(app)


def ensure_schema():
    db.create_all()
    inspector = inspect(db.engine)
    if 'users' in inspector.get_table_names():
        columns = {column['name'] for column in inspector.get_columns('users')}
        if 'role' not in columns:
            db.session.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            )
            db.session.commit()


with app.app_context():
    ensure_schema()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'CSRF token is missing or invalid'}), 400
    flash('Срок действия формы истек. Повторите действие.')
    return redirect(request.referrer or url_for('main'))


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def can_manage_resource(user_id):
    return current_user.role == 'admin' or current_user.id == user_id


def get_category_or_404(category_id):
    category = db.session.get(Category, category_id)
    if category is None:
        abort(404)
    if not can_manage_resource(category.user_id):
        abort(403)
    return category


def get_transaction_or_404(transaction_id):
    transaction = db.session.get(Transaction, transaction_id)
    if transaction is None:
        abort(404)
    if not can_manage_resource(transaction.user_id):
        abort(403)
    return transaction


def serialize_category(category):
    return {
        'id': category.id,
        'user_id': category.user_id,
        'name': category.name,
        'type': category.type,
        'color': category.color,
        'is_default': category.is_default,
    }


def serialize_transaction(transaction):
    return {
        'id': transaction.id,
        'user_id': transaction.user_id,
        'category_id': transaction.category_id,
        'category': transaction.category.name if transaction.category else None,
        'amount': float(transaction.amount),
        'type': transaction.type,
        'description': transaction.description,
        'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
        'created_at': transaction.created_at.isoformat() if transaction.created_at else None,
    }


def validate_type(value):
    if value not in ('income', 'expense'):
        abort(400, description='type must be income or expense')
    return value


@app.route("/")
def index():
    return redirect(url_for('registr'))


@app.route("/registration", methods=['GET', 'POST'])
def registr():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        if name:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Этот email уже зарегистрирован!')
                return redirect(url_for('registr'))

            role = 'admin' if User.query.count() == 0 else 'user'
            new_user = User(name=name, email=email, role=role)
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            flash('Регистрация успешна! Теперь войдите.')
            return redirect(url_for('registr'))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Вы успешно вошли!')
            return redirect(url_for('main'))

        flash('Неверный email или пароль')
        return redirect(url_for('registr'))

    return render_template('registr.html')


@app.route("/logout", methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Вы вышли из аккаунта')
    return redirect(url_for('registr'))


@app.route("/main")
@login_required
def main():
    income_cats = Category.query.filter_by(user_id=current_user.id, type='income').all()
    expense_cats = Category.query.filter_by(user_id=current_user.id, type='expense').all()

    return render_template(
        'main.html',
        user_name=current_user.name,
        user_role=current_user.role,
        income_cats=income_cats,
        expense_cats=expense_cats,
    )


@app.route("/history")
@login_required
def history():
    transactions = Transaction.query.filter_by(user_id=current_user.id) \
        .order_by(Transaction.created_at.desc()).all()
    income_cats = Category.query.filter_by(user_id=current_user.id, type='income').all()
    expense_cats = Category.query.filter_by(user_id=current_user.id, type='expense').all()

    return render_template(
        'history.html',
        transactions=transactions,
        income_cats=income_cats,
        expense_cats=expense_cats,
    )


@app.route("/statistics")
@login_required
def statistics():
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

    return render_template(
        'statistics.html',
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        difference=difference,
        income_percent=income_percent,
        expense_percent=expense_percent,
        income_labels=income_labels,
        income_values=income_values,
        expense_labels=expense_labels,
        expense_values=expense_values,
    )


@app.route("/debts", methods=['GET', 'POST'])
@login_required
def debts():
    result = None
    form_data = {}

    if request.method == 'POST':
        form_data = {
            'type': request.form.get('type', 'credit'),
            'amount': request.form.get('amount'),
            'term': request.form.get('term'),
            'rate': request.form.get('rate'),
            'rate_type': request.form.get('rate_type', 'annual'),
        }

        amount = float(form_data['amount'])
        term = int(form_data['term'])
        rate = float(form_data['rate'])
        rate_type = form_data['rate_type']
        loan_type = form_data['type']

        monthly_rate = rate / 100 / 12 if rate_type == 'annual' else rate / 100

        if loan_type == 'credit':
            monthly_payment = (amount / term) * (1 + monthly_rate)
            total_payment = monthly_payment * term
            overpayment = total_payment - amount

            result = {
                'type': 'credit',
                'monthly_payment': monthly_payment,
                'total_payment': total_payment,
                'overpayment': overpayment,
            }
        else:
            monthly_payment = amount * monthly_rate
            total_payments = monthly_payment * term
            total_amount = amount + total_payments

            result = {
                'type': 'loan',
                'monthly_payment': monthly_payment,
                'total_payments': total_payments,
                'total_amount': total_amount,
            }

    return render_template('debts.html', result=result, form_data=form_data)


@app.route("/add_transaction", methods=['POST'])
@login_required
def add_transaction():
    trans_type = validate_type(request.form.get('type'))
    category_name = request.form.get('category')
    amount = float(request.form.get('amount'))
    description = request.form.get('description', '')

    category = Category.query.filter_by(
        user_id=current_user.id,
        name=category_name,
        type=trans_type,
    ).first()

    if not category:
        category = Category(
            user_id=current_user.id,
            name=category_name,
            type=trans_type,
        )
        db.session.add(category)
        db.session.commit()

    new_transaction = Transaction(
        user_id=current_user.id,
        category_id=category.id,
        amount=amount,
        type=trans_type,
        description=description,
    )

    db.session.add(new_transaction)
    db.session.commit()

    flash('Запись добавлена!')
    return redirect(url_for('main'))


@app.route("/add_category", methods=['POST'])
@login_required
def add_category():
    name = request.form.get('name')
    cat_type = validate_type(request.form.get('type'))

    existing = Category.query.filter_by(
        user_id=current_user.id,
        name=name,
        type=cat_type,
    ).first()

    if existing:
        flash('Такая категория уже есть')
    else:
        new_category = Category(
            user_id=current_user.id,
            name=name,
            type=cat_type,
        )
        db.session.add(new_category)
        db.session.commit()
        flash('Категория добавлена!')

    return redirect(url_for('main'))


@app.route("/delete_category/<int:category_id>", methods=['DELETE'])
@login_required
def delete_category(category_id):
    category = get_category_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'message': 'Категория удалена'})


@app.route("/delete_transaction/<int:transaction_id>", methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    transaction = get_transaction_or_404(transaction_id)
    db.session.delete(transaction)
    db.session.commit()
    return jsonify({'message': 'Запись удалена'})


@app.get("/api/csrf-token")
def api_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})


@app.get("/api/admin/users")
@role_required('admin')
def api_admin_users():
    users = User.query.order_by(User.id).all()
    return jsonify([
        {'id': user.id, 'name': user.name, 'email': user.email, 'role': user.role}
        for user in users
    ])


@app.route("/api/categories", methods=['GET', 'POST'])
@login_required
def api_categories():
    if request.method == 'GET':
        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.id).all()
        return jsonify([serialize_category(category) for category in categories])

    data = request.get_json(silent=True) or {}
    name = data.get('name')
    cat_type = validate_type(data.get('type'))
    if not name:
        abort(400, description='name is required')

    category = Category(user_id=current_user.id, name=name, type=cat_type)
    db.session.add(category)
    db.session.commit()
    return jsonify(serialize_category(category)), 201


@app.route("/api/categories/<int:category_id>", methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_category_detail(category_id):
    category = get_category_or_404(category_id)

    if request.method == 'GET':
        return jsonify(serialize_category(category))

    if request.method in ('PUT', 'PATCH'):
        data = request.get_json(silent=True) or {}
        category.name = data.get('name', category.name)
        if 'type' in data:
            category.type = validate_type(data['type'])
        if 'color' in data:
            category.color = data['color']
        db.session.commit()
        return jsonify(serialize_category(category))

    db.session.delete(category)
    db.session.commit()
    return jsonify({'message': 'Категория удалена'})


@app.route("/api/transactions", methods=['GET', 'POST'])
@login_required
def api_transactions():
    if request.method == 'GET':
        transactions = Transaction.query.filter_by(user_id=current_user.id) \
            .order_by(Transaction.created_at.desc()).all()
        return jsonify([serialize_transaction(transaction) for transaction in transactions])

    data = request.get_json(silent=True) or {}
    trans_type = validate_type(data.get('type'))
    category_id = data.get('category_id')
    amount = data.get('amount')
    if amount is None:
        abort(400, description='amount is required')

    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id,
        type=trans_type,
    ).first()
    if not category:
        abort(400, description='category_id is invalid')

    transaction = Transaction(
        user_id=current_user.id,
        category_id=category.id,
        amount=float(amount),
        type=trans_type,
        description=data.get('description', ''),
    )
    db.session.add(transaction)
    db.session.commit()
    return jsonify(serialize_transaction(transaction)), 201


@app.route("/api/transactions/<int:transaction_id>", methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def api_transaction_detail(transaction_id):
    transaction = get_transaction_or_404(transaction_id)

    if request.method == 'GET':
        return jsonify(serialize_transaction(transaction))

    if request.method in ('PUT', 'PATCH'):
        data = request.get_json(silent=True) or {}
        if 'type' in data:
            transaction.type = validate_type(data['type'])
        if 'amount' in data:
            transaction.amount = float(data['amount'])
        if 'description' in data:
            transaction.description = data['description']
        if 'category_id' in data:
            category = Category.query.filter_by(
                id=data['category_id'],
                user_id=transaction.user_id,
                type=transaction.type,
            ).first()
            if not category:
                abort(400, description='category_id is invalid')
            transaction.category_id = category.id
        db.session.commit()
        return jsonify(serialize_transaction(transaction))

    db.session.delete(transaction)
    db.session.commit()
    return jsonify({'message': 'Запись удалена'})


if __name__ == '__main__':
    app.run(debug=True)

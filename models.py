from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# === Модель категории ===
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' или 'expense'
    color = db.Column(db.String(7), default='#614e48')
    is_default = db.Column(db.Boolean, default=False)

    transactions = db.relationship('Transaction', backref='category', lazy=True)


# === Модель транзакции ===
class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' или 'expense'
    description = db.Column(db.Text)
    transaction_date = db.Column(db.Date, default=db.func.current_date())
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
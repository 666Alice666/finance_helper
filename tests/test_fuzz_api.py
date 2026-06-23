import importlib
import os

from hypothesis import given, settings, strategies as st

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key'

finance_app = importlib.import_module('app')
app = finance_app.app
db = finance_app.db
Category = finance_app.Category
Transaction = finance_app.Transaction
User = finance_app.User


@st.composite
def category_names(draw):
    value = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters=' _-'),
        min_size=1,
        max_size=30,
    ))
    return value.strip() or 'category'


def prepare_user(client):
    with app.app_context():
        db.drop_all()
        db.create_all()
        user = User(
            name='Test User',
            email='test@example.com',
            password_hash='not-used-in-this-test',
            role='user',
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True


@given(
    category_name=category_names(),
    updated_name=category_names(),
    amount=st.decimals(min_value='1', max_value='1000000', places=2),
    description=st.text(max_size=120),
)
@settings(max_examples=20)
def test_fuzz_api_category_and_transaction_crud(category_name, updated_name, amount, description):
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.test_client() as client:
        prepare_user(client)

        category_response = client.post('/api/categories', json={
            'name': category_name,
            'type': 'expense',
        })
        assert category_response.status_code == 201
        category_id = category_response.get_json()['id']

        update_category_response = client.patch(f'/api/categories/{category_id}', json={
            'name': updated_name,
            'type': 'expense',
        })
        assert update_category_response.status_code == 200
        assert update_category_response.get_json()['name'] == updated_name

        transaction_response = client.post('/api/transactions', json={
            'category_id': category_id,
            'amount': str(amount),
            'type': 'expense',
            'description': description,
        })
        assert transaction_response.status_code == 201
        transaction_id = transaction_response.get_json()['id']

        update_transaction_response = client.patch(f'/api/transactions/{transaction_id}', json={
            'amount': str(amount),
            'description': description[:60],
        })
        assert update_transaction_response.status_code == 200

        delete_transaction_response = client.delete(f'/api/transactions/{transaction_id}')
        assert delete_transaction_response.status_code == 200

        delete_category_response = client.delete(f'/api/categories/{category_id}')
        assert delete_category_response.status_code == 200

        with app.app_context():
            assert Transaction.query.count() == 0
            assert Category.query.count() == 0
            assert User.query.count() == 1

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin'))
);

-- Таблица категорий
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(10) CHECK (type IN ('income', 'expense')),
    color VARCHAR(7) DEFAULT '#614e48',
    is_default BOOLEAN DEFAULT FALSE
);

-- Таблица транзакций
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    amount DECIMAL(10, 2) NOT NULL CHECK (amount > 0),
    type VARCHAR(10) CHECK (type IN ('income', 'expense')),
    description TEXT,
    transaction_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- Даём права (на всякий случай)
GRANT ALL PRIVILEGES ON TABLE users TO finance_user;
GRANT ALL PRIVILEGES ON TABLE categories TO finance_user;
GRANT ALL PRIVILEGES ON TABLE transactions TO finance_user;
GRANT ALL PRIVILEGES ON SEQUENCE users_id_seq TO finance_user;
GRANT ALL PRIVILEGES ON SEQUENCE categories_id_seq TO finance_user;
GRANT ALL PRIVILEGES ON SEQUENCE transactions_id_seq TO finance_user;
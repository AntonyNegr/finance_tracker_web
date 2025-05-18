from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DATABASE = 'finance.db'
USD_TO_RUB = 80

CATEGORIES = ['Зарплата', 'Еда', 'Развлечение', 'Транспорт', 'Шопинг', 'Другое']

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount_rub REAL NOT NULL,
            original_amount REAL NOT NULL,
            original_currency TEXT NOT NULL CHECK(original_currency IN ('RUB', 'USD')),
            category TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    db.commit()
    db.close()

def calculate_ndfl(income_rub):
    tax = 0
    if income_rub <= 2_400_000:
        tax = income_rub * 0.13
    elif income_rub <= 5_000_000:
        tax = 2_400_000 * 0.13 + (income_rub - 2_400_000) * 0.15
    elif income_rub <= 20_000_000:
        tax = 2_400_000 * 0.13 + 2_600_000 * 0.15 + (income_rub - 5_000_000) * 0.18
    elif income_rub <= 50_000_000:
        tax = 2_400_000 * 0.13 + 2_600_000 * 0.15 + 15_000_000 * 0.18 + (income_rub - 20_000_000) * 0.20
    else:
        tax = (
            2_400_000 * 0.13 +
            2_600_000 * 0.15 +
            15_000_000 * 0.18 +
            30_000_000 * 0.20 +
            (income_rub - 50_000_000) * 0.22
        )
    return tax

INDEX_HTML = ''' 
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Финансы</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px auto;
            max-width: 600px;
            padding: 0 15px;
            background-color: #f9f9f9;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 {
            margin: 0;
        }
        .user-actions form, .user-actions button {
            margin-left: 10px;
            display: inline-block;
        }
        .finances {
            margin-top: 20px;
        }
        .finances table {
            width: 100%;
            border-collapse: collapse;
        }
        .finances th, .finances td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }
        .finances th {
            background-color: #eee;
        }
        .add-form, .login-register {
            margin-top: 20px;
            padding: 10px;
            background-color: #e8e8e8;
            border-radius: 5px;
        }
        .add-form input[type="text"], .add-form input[type="number"], .add-form select,
        .login-register input[type="text"], .login-register input[type="password"] {
            padding: 5px;
            margin-right: 10px;
            margin-bottom: 10px;
            width: calc(100% - 22px);
            max-width: 200px;
        }
        .add-form label {
            display: block;
            margin-bottom: 5px;
        }
        .add-form input[type="submit"], .login-register input[type="submit"] {
            padding: 8px 12px;
            cursor: pointer;
        }
        .currency-switch {
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <header>
        <h1>Финансы</h1>
        {% if user %}
        <div class="user-actions">
            <span>Привет, {{ user }}!</span>
            <form action="{{ url_for('logout') }}" method="get" style="display:inline;">
                <button type="submit">Выйти</button>
            </form>
        </div>
        {% endif %}
    </header>

    {% if not user %}
    <div class="login-register">
        <h2>Вход</h2>
        <form action="{{ url_for('login') }}" method="post">
            <input type="text" name="username" placeholder="Имя пользователя" required />
            <input type="password" name="password" placeholder="Пароль" required />
            <input type="submit" value="Войти" />
        </form>

        <h2>Регистрация</h2>
        <form action="{{ url_for('register') }}" method="post">
            <input type="text" name="username" placeholder="Имя пользователя" required />
            <input type="password" name="password" placeholder="Пароль" required />
            <input type="submit" value="Зарегистрироваться" />
        </form>
    </div>
    {% else %}
    <div class="currency-switch">
        <form method="get" action="{{ url_for('index') }}">
            <label for="currency">Валюта:</label>
            <select id="currency" name="currency" onchange="this.form.submit()">
                <option value="RUB" {% if currency == 'RUB' %}selected{% endif %}>RUB</option>
                <option value="USD" {% if currency == 'USD' %}selected{% endif %}>USD</option>
            </select>
        </form>
    </div>

    <div class="finances">
        <table>
            <thead>
                <tr>
                    <th>Тип</th>
                    <th>Описание</th>
                    <th>Категория</th>
                    <th>Сумма ({{ currency }})</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for item in finances %}
                <tr>
                    <td>{{ item.type }}</td>
                    <td>{{ item.description }}</td>
                    <td>{{ item.category }}</td>
                    <td>{{ "%.2f"|format(item.display_amount) }}</td>
                    <td>
                        <form action="{{ url_for('delete', id=item.id) }}" method="post" onsubmit="return confirm('Удалить эту запись?');">
                            <button type="submit">Удалить</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <p>Итого доходы: {{ "%.2f"|format(income_total) }} {{ currency }}</p>
        <p>Итого расходы: {{ "%.2f"|format(expense_total) }} {{ currency }}</p>
        <p>НДФЛ: {{ "%.2f"|format(tax) }} {{ currency }}</p>
    </div>

    <div class="add-form">
        <h2>Добавить запись</h2>
        <form action="{{ url_for('add') }}" method="post">
            <label>Тип:
                <select name="type" required>
                    <option value="income">Доход</option>
                    <option value="expense">Расход</option>
                </select>
            </label><br />
            <label>Описание:
                <input type="text" name="description" required />
            </label><br />
            <label>Категория:
                <select name="category" required>
                    {% for cat in categories %}
                    <option value="{{ cat }}">{{ cat }}</option>
                    {% endfor %}
                </select>
            </label><br />
            <label>Сумма:
                <input type="number" step="0.01" min="0" name="amount" required />
            </label><br />
            <label>Валюта:
                <select name="currency" required>
                    <option value="RUB">RUB</option>
                    <option value="USD">USD</option>
                </select>
            </label><br />
            <input type="submit" value="Добавить" />
        </form>
    </div>
    {% endif %}
</body>
</html>
'''

def to_display(rub_amount, currency):
    return rub_amount / USD_TO_RUB if currency == 'USD' else rub_amount

def get_user():
    user_id = session.get('user_id')
    if user_id is None:
        return None
    db = get_db()
    user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    return user['username'] if user else None

@app.route('/')
def index():
    user = get_user()
    if not user:
        return render_template_string(INDEX_HTML, user=None)

    currency = request.args.get('currency', 'RUB').upper()
    if currency not in ('RUB', 'USD'):
        currency = 'RUB'

    db = get_db()
    user_id = session['user_id']
    rows = db.execute("SELECT * FROM finances WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    db.close()

    finances = []
    income_rub = expense_rub = 0
    for row in rows:
        amt = row['amount_rub']
        if row['type'] == 'income': income_rub += amt
        else: expense_rub += amt
        finances.append({
            'id': row['id'],
            'type': row['type'],
            'description': row['description'],
            'category': row['category'],
            'display_amount': to_display(amt, currency)
        })

    income_total = to_display(income_rub, currency)
    expense_total = to_display(expense_rub, currency)
    ndfl_rub = calculate_ndfl(income_rub)
    tax = to_display(ndfl_rub, currency)

    return render_template_string(INDEX_HTML,
                                  finances=finances,
                                  currency=currency,
                                  income_total=income_total,
                                  expense_total=expense_total,
                                  tax=tax,
                                  user=user,
                                  categories=CATEGORIES)

@app.route('/add', methods=['POST'])
def add():
    user = get_user()
    if not user:
        return redirect(url_for('index'))

    type_ = request.form['type']
    desc = request.form['description']
    cat = request.form['category']
    if cat not in CATEGORIES:
        return redirect(url_for('index'))

    try:
        amount = float(request.form['amount'])
        if amount < 0:
            raise ValueError
    except:
        return redirect(url_for('index'))

    curr = request.form['currency'].upper()
    if curr not in ('RUB', 'USD'):
        curr = 'RUB'

    amount_rub = amount * USD_TO_RUB if curr == 'USD' else amount

    db = get_db()
    user_id = session['user_id']
    db.execute('''
        INSERT INTO finances (user_id, description, amount_rub, original_amount, original_currency, category, type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, desc, amount_rub, amount, curr, cat, type_))
    db.commit()
    db.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    user = get_user()
    if not user:
        return redirect(url_for('index'))

    db = get_db()
    user_id = session['user_id']
    row = db.execute('SELECT * FROM finances WHERE id = ? AND user_id = ?', (id, user_id)).fetchone()
    if row:
        db.execute('DELETE FROM finances WHERE id = ?', (id,))
        db.commit()
    db.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
    db.close()
    if user:
        session['user_id'] = user['id']
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    db = get_db()
    existing = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if existing:
        db.close()
        return redirect(url_for('index'))

    db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    db.commit()
    db.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

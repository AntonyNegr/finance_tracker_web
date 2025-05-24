from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import requests

app = Flask(__name__)
app.secret_key = '12345'
dbb = 'finance.db'

def get_current_usd_to_rub():
    url = 'https://open.er-api.com/v6/latest/USD'
    response = requests.get(url)
    data = response.json()
    return data['rates']['RUB']

USD_TO_RUB = get_current_usd_to_rub()


CATEGORIES = ['Зарплата', 'Еда', 'Развлечение', 'Транспорт', 'Шопинг', 'Другое']

def get_db():
    db = sqlite3.connect(dbb)
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
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            background-image: url('https://avatars.mds.yandex.net/i?id=a71280601e38e1d2cf1ed88f46a9fee2_l-5312571-images-thumbs&ref=rim&n=13&w=1800&h=972');
            background-size: cover;
            background-attachment: fixed;
            margin: 0;
            padding: 0;
            color: #333;
        }

        main {
            max-width: 800px;
            margin: 40px auto;
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        header h1 {
            margin: 0;
            font-size: 2rem;
            display: flex;
            align-items: center;
        }

        header h1::before {
            content: url('https://img.icons8.com/ios-filled/30/000000/money.png');
            margin-right: 10px;
        }

        .user-actions {
            display: flex;
            align-items: center;
        }

        .user-actions span {
            margin-right: 10px;
        }

        button {
            padding: 6px 12px;
            background-color: #007bff;
            border: none;
            border-radius: 5px;
            color: white;
            cursor: pointer;
        }

        button:hover {
            background-color: #0056b3;
        }

        .finances table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }

        .finances th, .finances td {
            border: 1px solid #ccc;
            padding: 10px;
        }

        .finances th {
            background-color: #f0f0f0;
        }

        .add-form, .login-register {
            background-color: #f9f9f9;
            border-left: 5px solid #007bff;
            padding: 20px;
            margin-top: 20px;
            border-radius: 8px;
        }

        .add-form input[type="text"],
        .add-form input[type="number"],
        .add-form select,
        .login-register input[type="text"],
        .login-register input[type="password"] {
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }

        input[type="submit"] {
            background-color: #28a745;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
        }

        input[type="submit"]:hover {
            background-color: #218838;
        }

        .currency-switch {
            margin: 10px 0 20px;
        }

        .currency-switch select {
            padding: 6px;
            border-radius: 4px;
        }

        h2 {
            margin-top: 0;
        }

        .flash-message {
            background-color: #f8d7da;
            color: #842029;
            border: 1px solid #f5c2c7;
            border-radius: 6px;
            padding: 10px;
            margin-bottom: 15px;
        }

        .category-summary {
            margin-bottom: 20px;
        }

        .category-summary h3 {
            margin-bottom: 10px;
        }

        .category-summary table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }

        .category-summary th, .category-summary td {
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }

        .category-summary th {
            background-color: #e9ecef;
        }
    </style>
</head>
<body>
<main>
    <header>
        <h1>Финансы</h1>
        {% if user %}
        <div class="user-actions">
            <span>Привет, {{ user }}!</span>
            <form action="{{ url_for('logout') }}" method="get">
                <button type="submit">Выйти</button>
            </form>
        </div>
        {% endif %}
    </header>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for msg in messages %}
          <div class="flash-message">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

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

        <p><strong>Итого доходы:</strong> {{ "%.2f"|format(income_total) }} {{ currency }}</p>
        <p><strong>Итого расходы:</strong> {{ "%.2f"|format(expense_total) }} {{ currency }}</p>
        <p><strong>НДФЛ:</strong> {{ "%.2f"|format(tax) }} {{ currency }}</p>
    </div>

    <div class="category-summary">
        <h3>Доходы по категориям (в {{ currency }})</h3>
        <table>
            <thead><tr><th>Категория</th><th>Сумма</th></tr></thead>
            <tbody>
            {% for cat, amount in income_by_cat.items() %}
                <tr><td>{{ cat }}</td><td>{{ "%.2f"|format(amount) }}</td></tr>
            {% endfor %}
            </tbody>
        </table>

        <h3>Расходы по категориям (в {{ currency }})</h3>
        <table>
            <thead><tr><th>Категория</th><th>Сумма</th></tr></thead>
            <tbody>
            {% for cat, amount in expense_by_cat.items() %}
                <tr><td>{{ cat }}</td><td>{{ "%.2f"|format(amount) }}</td></tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="add-form">
        <h2>Добавить запись</h2>
        <form action="{{ url_for('add') }}" method="post">
            <label>Тип:
                <select name="type" required>
                    <option value="income">Доход</option>
                    <option value="expense">Расход</option>
                </select>
            </label>
            <label>Описание:
                <input type="text" name="description" required />
            </label>
            <label>Категория:
                <select name="category" required>
                    {% for cat in categories %}
                    <option value="{{ cat }}">{{ cat }}</option>
                    {% endfor %}
                </select>
            </label>
            <label>Сумма:
                <input type="number" step="0.01" min="0" name="amount" required />
            </label>
            <label>Валюта:
                <select name="currency" required>
                    <option value="RUB">RUB</option>
                    <option value="USD">USD</option>
                </select>
            </label>
            <input type="submit" value="Добавить" />
        </form>
    </div>
    {% endif %}
</main>
</body>
</html>
'''

def to_display(rub_amount, currency):
    return rub_amount / USD_TO_RUB if currency == 'USD' else rub_amount

def to_rub(amount, currency):
    return amount * USD_TO_RUB if currency == 'USD' else amount

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

    income_cat_raw = get_total_income_by_category(user_id)
    expense_cat_raw = get_total_expense_by_category(user_id)
    income_by_cat = {cat: (amt / USD_TO_RUB if currency == 'USD' else amt) for cat, amt in income_cat_raw.items()}
    expense_by_cat = {cat: (amt / USD_TO_RUB if currency == 'USD' else amt) for cat, amt in expense_cat_raw.items()}

    finances = []
    income_total = 0
    expense_total = 0
    for row in rows:
        amount_rub = row['amount_rub']
        amount_display = to_display(amount_rub, currency)
        finances.append({
            'id': row['id'],
            'type': row['type'],
            'description': row['description'],
            'category': row['category'],
            'display_amount': amount_display,
        })
        if row['type'] == 'income':
            income_total += amount_rub
        else:
            expense_total += amount_rub

    tax = calculate_ndfl(income_total)

    income_total_display = to_display(income_total, currency)
    expense_total_display = to_display(expense_total, currency)
    tax_display = to_display(tax, currency)

    db.close()

    return render_template_string(INDEX_HTML,
                                  user=user,
                                  finances=finances,
                                  income_total=income_total_display,
                                  expense_total=expense_total_display,
                                  tax=tax_display,
                                  categories=CATEGORIES,
                                  currency=currency,
                                  income_by_cat=income_by_cat,
                                  expense_by_cat=expense_by_cat
                                  )

@app.route('/add', methods=['POST'])
def add():
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.")
        return redirect(url_for('index'))

    user_id = session['user_id']
    type_ = request.form['type']
    description = request.form['description']
    category = request.form['category']
    amount = float(request.form['amount'])
    currency = request.form['currency']

    amount_rub = to_rub(amount, currency)

    db = get_db()
    db.execute('INSERT INTO finances (user_id, description, amount_rub, original_amount, original_currency, category, type) VALUES (?, ?, ?, ?, ?, ?, ?)',
               (user_id, description, amount_rub, amount, currency, category, type_))
    db.commit()
    db.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if 'user_id' not in session:
        flash("Пожалуйста, войдите в систему.")
        return redirect(url_for('index'))

    db = get_db()
    user_id = session['user_id']
    db.execute('DELETE FROM finances WHERE id = ? AND user_id = ?', (id, user_id))
    db.commit()
    db.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if not user:
        db.close()
        flash('Пользователь не существует.')
        return redirect(url_for('index'))

    if user['password'] != password:
        db.close()
        flash('Неверный пароль.')
        return redirect(url_for('index'))

    session['user_id'] = user['id']
    db.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы.')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    db = get_db()
    exists = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if exists:
        db.close()
        flash('Пользователь с таким именем уже существует.')
        return redirect(url_for('index'))

    db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    db.commit()
    db.close()

    flash('Регистрация прошла успешно. Войдите в систему.')
    return redirect(url_for('index'))

def get_total_income_by_category(user_id):
    db = get_db()
    result = db.execute(
        "SELECT category, SUM(amount_rub) AS total_income "
        "FROM finances WHERE user_id = ? AND type = 'income' GROUP BY category",
        (user_id,)
    ).fetchall()
    db.close()
    return {row['category']: row['total_income'] for row in result}

def get_total_expense_by_category(user_id):
    db = get_db()
    result = db.execute(
        "SELECT category, SUM(amount_rub) AS total_expense "
        "FROM finances WHERE user_id = ? AND type = 'expense' GROUP BY category",
        (user_id,)
    ).fetchall()
    db.close()
    return {row['category']: row['total_expense'] for row in result}

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

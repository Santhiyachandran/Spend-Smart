from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, auth, firestore
from werkzeug.security import check_password_hash, generate_password_hash
import re  # Import regex module for password validation

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Firebase Initialization
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Homepage Route
@app.route('/')
def home():
    return render_template('index.html', page="home")

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        username = request.form['username']
        age = request.form['age']

        # Check password strength
        if not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or \
           not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password) or \
           len(password) < 8:
            flash("Password must contain at least 8 characters, including an uppercase letter, a lowercase letter, a number, and a special character.", "error")
            return redirect(url_for('register'))

        try:
            user = auth.create_user(email=email, password=password)
            db.collection('users').document(user.uid).set({
                'username': username,
                'age': age,
                'salary': 0,
                'password_hash': generate_password_hash(password)
            })
            return redirect(url_for('login'))
        except:
            flash("Registration Failed. Try again.", "error")
            return redirect(url_for('register'))
    return render_template('index.html', page="register")

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            user = auth.get_user_by_email(email)
            user_data = db.collection('users').document(user.uid).get().to_dict()

            if user_data and check_password_hash(user_data['password_hash'], password):
                session['user'] = user.uid
                return redirect(url_for('enter_salary'))
            else:
                flash("Invalid credentials. Please try again.", "error")
                return redirect(url_for('login'))
        except:
            flash("Login failed. Please check your credentials.", "error")
            return redirect(url_for('login'))
    return render_template('index.html', page="login")

# Route to enter salary after login
@app.route('/enter-salary', methods=['GET', 'POST'])
def enter_salary():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        salary = request.form['salary']
        user_ref = db.collection('users').document(session['user'])
        user_ref.update({'salary': salary})
        return redirect(url_for('dashboard'))
    return render_template('index.html', page="enter_salary")

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user_ref = db.collection('users').document(session['user']).get()
    user_data = user_ref.to_dict()
    
    return render_template('index.html', page="dashboard", user=user_data)

# Add Expense Route with Category Dropdown
@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    categories = ["Savings", "Electricity Bill", "Rent", "Health", "Groceries", "Other"]
    
    if request.method == 'POST':
        date = request.form['date']
        category = request.form['category']
        amount = request.form['amount']
        description = request.form['description']
        
        db.collection('expenses').add({
            'user_id': session['user'],
            'date': date,
            'category': category,
            'amount': amount,
            'description': description
        })
        
        return redirect(url_for('dashboard'))
    
    return render_template('index.html', page="add_expense", categories=categories)

# View All Expenses Route (separated by category)
@app.route('/view-expenses')
def view_expenses():
    if 'user' not in session:
        return redirect(url_for('login'))

    # Retrieve all expenses for the logged-in user
    expenses_ref = db.collection('expenses').where('user_id', '==', session['user']).get()
    expense_data = [expense.to_dict() for expense in expenses_ref]

    # Separate expenses into different categories
    savings_expenses = [expense for expense in expense_data if expense['category'] == "Savings"]
    other_expenses = [expense for expense in expense_data if expense['category'] == "Other"]
    general_expenses = [expense for expense in expense_data if expense['category'] not in ["Savings", "Other"]]

    return render_template('index.html', page="view_expenses", 
                           savings_expenses=savings_expenses, 
                           other_expenses=other_expenses, 
                           general_expenses=general_expenses)

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# Run the Flask App
if __name__ == '__main__':
    app.run(debug=True)

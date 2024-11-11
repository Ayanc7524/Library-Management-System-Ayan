from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/lms'
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

class BorrowedBooks(db.Model):
    __tablename__ = 'borrowedbooks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('register.sno'), nullable=False)  # Changed email to sno
    book_id = db.Column(db.Integer, db.ForeignKey('book.book_id'), nullable=False)  # Changed title to book_id
    borrowed_date = db.Column(db.DateTime, default=func.now(), server_default=func.now())
    
    user = db.relationship('Register', back_populates='borrowed_books')
    book = db.relationship('Book', back_populates='borrowed_books')

    def __repr__(self):
        return f'<BorrowedBook {self.book_id} by {self.user_id}>'

class Register(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(80), nullable=False)
    lname = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(15), nullable=False)
    borrowed_books = relationship('BorrowedBooks', back_populates='user')

    def __init__(self, fname, lname, email, password, contact):
        self.fname = fname
        self.lname = lname
        self.email = email
        self.password = password
        self.contact = contact

class Book(db.Model):
    book_id = db.Column(db.Integer, primary_key=True)  # Unique ID for each book
    title = db.Column(db.String(200), nullable=False)   # Title of the book
    author = db.Column(db.String(100), nullable=False)  # Author of the book
    quantity = db.Column(db.Integer, default=1)         # Number of copies available
    borrowed_books = relationship('BorrowedBooks', back_populates='book')

    def __init__(self, title, author, quantity):
        self.title = title
        self.author = author
        self.quantity = quantity

    def __repr__(self):
        return f"<Book {self.title} by {self.author}>"

# Add relationship to the 'Register' and 'Book' models:
Register.borrowed_books = db.relationship('BorrowedBooks', back_populates='user')
Book.borrowed_books = db.relationship('BorrowedBooks', back_populates='book')
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        print("Login Attempt: Email =", email)  # Debugging line

        user = Register.query.filter_by(email=email).first()

        if user and user.password == password:
            session['user_id'] = user.sno
            session['email'] = user.email
            session['fname'] = user.fname
            session['lname'] = user.lname

            print("Session after login:", session)  # Debug session content

            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_first_name = session.get('fname', None)
        user_last_name = session.get('lname', None)
        full_name = f"{user_first_name} {user_last_name}"

        return render_template("dashboard.html")
    
    flash("Please log in to access the dashboard", "danger")
    return redirect(url_for('login'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        password = request.form.get('password')
        cpassword = request.form.get('repassword')
        contact = request.form.get('mobile')

        if password != cpassword:
            flash("Passwords do not match", "danger")
            return render_template('register.html')

        new_user = Register(fname=fname, lname=lname, email=email, password=password, contact=contact)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/books')
def books():
    books = Book.query.all()  # Retrieve all books from the database
    return render_template('book_list.html', books=books)



@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        quantity = request.form['quantity']

        # Create a new book instance
        new_book = Book(
            title=title,
            author=author,
            quantity=quantity
        )

        # Add the book to the session and commit to the database
        db.session.add(new_book)
        db.session.commit()

        flash("Book added successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template("add_book.html")

@app.route('/borrowed_books')
def borrowed_books():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view borrowed books.", "warning")
        return redirect(url_for('login'))
    
    borrowed_books = BorrowedBooks.query.filter_by(user_id=user_id).all()
    
    # Handle invalid dates, setting them to None if needed
    for book in borrowed_books:
        if book.borrowed_date == '0000-00-00 00:00:00' or book.borrowed_date is None:
            book.borrowed_date = None  # Set invalid date to None

    return render_template("borrowed_books.html", borrowed_books=borrowed_books)

@app.route('/borrow_book/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    user_id = session.get('user_id')  # Retrieve logged-in user's ID from the session
    if not user_id:
        flash("Please log in to borrow books.", "danger")
        return redirect(url_for('login'))

    book = Book.query.get(book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for('books'))

    # Create a new borrowed book entry
    borrowed_book = BorrowedBooks(
        user_id=user_id,
        book_id=book.book_id,
        borrowed_date=datetime.utcnow()  # Using datetime.utcnow() here to ensure correct timestamp
    )
    db.session.add(borrowed_book)
    db.session.commit()

    flash("Book borrowed successfully!", "success")
    return redirect(url_for('borrowed_books'))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

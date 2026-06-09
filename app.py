from flask import Flask, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func
from database import init_db, session as db_session
from models import Car, Booking, Customer, Payment, User
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
app = Flask(__name__)
app.secret_key = "secret_key"

init_db()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect('/dashboard')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect('/register')

        existing = db_session.query(User).filter_by(username=username).first()
        if existing:
            flash("Username already exists. Please choose another.", "error")
            return redirect('/register')

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db_session.add(new_user)
        db_session.commit()
        flash("Account created! Please log in.", "success")
        return redirect('/login')

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = db_session.query(User).filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.", "error")
            return redirect('/login')

        session['username'] = user.username
        flash(f"Welcome back, {user.username}!", "success")
        return redirect('/dashboard')

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Logged out successfully.", "success")
    return redirect('/login')



# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    total_bookings = db_session.query(Booking).count()
    total_cars = db_session.query(Car).count()
    available_cars = db_session.query(Car).filter(Car.status == "Available").count()
    available_percent = round((available_cars / total_cars) * 100, 2) if total_cars else 0

    # ---------------- MOST RENTED CAR ----------------
    cars = db_session.query(Car).all()
    rented_car_names = []
    rented_car_counts = []
    most_rented_car = "No data"
    highest_count = 0
    for car in cars:
        count = db_session.query(Booking).filter(Booking.car_id == car.id).count()
        rented_car_names.append(car.name)
        rented_car_counts.append(count)
        if count > highest_count:
            highest_count = count
            most_rented_car = car.name

    # ---------------- REVENUE BREAKDOWN ----------------
    car_names = []
    revenue_data = []

    all_cars = db_session.query(Car).all()
    for car in all_cars:
        revenue = db_session.query(func.sum(Payment.amount)) \
            .join(Booking, Payment.booking_id == Booking.id) \
            .filter(Booking.car_id == car.id) \
            .scalar()
        if revenue:
            car_names.append(car.name)
            revenue_data.append(float(revenue))

    monthly_revenue = sum(revenue_data)

    # Placeholder daily booking data
   # Real daily booking data from database (last 10 days)
    from datetime import timedelta
    today = datetime.today().date()
    daily_labels = []
    daily_values = []
    for i in range(9, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        count = db_session.query(Booking).filter(Booking.start_date == day_str).count()
        daily_labels.append(day.strftime("%d"))
        daily_values.append(count)

    username = session.get('username', 'Guest')
    return render_template(
        "dashboard.html",
        total_bookings=total_bookings,
        daily_bookings=total_bookings,
        monthly_revenue=monthly_revenue,
        available_percent=available_percent,
        car_availability=available_percent,
        rented_car_names=rented_car_names,
        rented_car_counts=rented_car_counts,
        daily_labels=daily_labels,
        daily_values=daily_values,
        revenue_data=revenue_data,
        car_names=car_names,
        most_rented_car=most_rented_car,
        username=username
    )

# ---------------- CARS ----------------
@app.route('/cars')
def cars():
    cars = db_session.query(Car).all()
    username = session.get('username', 'Guest')
    return render_template("cars.html", cars=cars, username=username)

@app.route('/add_car', methods=['GET', 'POST'])
def add_car():
    if request.method == 'POST':
        new_car = Car(
            name=request.form['name'],
            brand=request.form['brand'],
            model=request.form['model'],
            number_plate=request.form['number_plate'],
            status="Available"
        )
        db_session.add(new_car)
        db_session.commit()
        return redirect('/cars')
    username = session.get('username', 'Guest')
    return render_template("add_car.html", username=username)

@app.route('/edit_car/<int:car_id>', methods=['GET', 'POST'])
def edit_car(car_id):
    car = db_session.query(Car).get(car_id)
    if not car:
        return "Car not found!"
    if request.method == 'POST':
        car.name = request.form['name']
        car.brand = request.form['brand']
        car.model = request.form['model']
        car.number_plate = request.form['number_plate']
        car.status = request.form['status']
        db_session.commit()
        return redirect('/cars')
    username = session.get('username', 'Guest')
    return render_template("edit_car.html", car=car, username=username)

@app.route('/delete_car/<int:car_id>')
def delete_car(car_id):
    car = db_session.query(Car).get(car_id)
    if car:
        db_session.delete(car)
        db_session.commit()
    return redirect('/cars')

# ---------------- BOOKINGS ----------------
@app.route('/book_car/<int:car_id>', methods=['GET', 'POST'])
def book_car(car_id):
    car = db_session.query(Car).get(car_id)
    if not car:
        return f"Car with ID {car_id} not found!"
    customers = db_session.query(Customer).all()
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id')
            new_customer_name = request.form.get('new_customer_name', '').strip()
            start_date = request.form['start_date']
            end_date = request.form['end_date']

            if new_customer_name:
                existing_customer = db_session.query(Customer).filter_by(name=new_customer_name).first()
                if existing_customer:
                    customer_id = existing_customer.id
                else:
                    new_customer = Customer(name=new_customer_name)
                    db_session.add(new_customer)
                    db_session.commit()
                    customer_id = new_customer.id

            if not customer_id:
                flash("Select customer or enter new name.", "error")
                return redirect(url_for('book_car', car_id=car_id))

            new_booking = Booking(
                customer_id=int(customer_id),
                car_id=car.id,
                start_date=start_date,
                end_date=end_date,
                status="Booked"
            )
            car.status = "Booked"
            db_session.add(new_booking)
            db_session.commit()
            flash("Car booked successfully!", "success")
            return redirect('/bookings')
        except Exception as e:
            db_session.rollback()
            flash(f"Error: {e}", "error")
            return redirect(url_for('book_car', car_id=car_id))
    username = session.get('username', 'Guest')
    return render_template("book_car.html", car=car, customers=customers, username=username)

@app.route('/bookings')
def bookings():
    bookings = db_session.query(Booking).all()
    username = session.get('username', 'Guest')
    return render_template("bookings.html", bookings=bookings, username=username)

@app.route('/return_car/<int:booking_id>')
def return_car(booking_id):
    booking = db_session.query(Booking).get(booking_id)
    if booking:
        car = db_session.query(Car).get(booking.car_id)
        booking.status = "Returned"
        if car:
            car.status = "Available"
        db_session.commit()
    return redirect('/bookings')

# ---------------- CUSTOMERS ----------------
@app.route('/customers')
def customers():
    all_customers = db_session.query(Customer).all()
    username = session.get('username', 'Guest')
    return render_template("customers.html", customers=all_customers, username=username)

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        new_c = Customer(
            name=request.form['name'],
            email=request.form['email'],
            phone=request.form['phone']
        )
        db_session.add(new_c)
        db_session.commit()
        return redirect('/customers')
    username = session.get('username', 'Guest')
    return render_template("add_customer.html", username=username)

# ---------------- PAYMENTS ----------------
@app.route('/payments')
def payments():
    all_payments = db_session.query(Payment).all()
    for p in all_payments:
        if isinstance(p.payment_date, str):
            try:
                p.payment_date = datetime.strptime(p.payment_date, '%Y-%m-%d')
            except:
                p.payment_date = None
    total_revenue = sum([p.amount for p in all_payments if p.amount])
    username = session.get('username', 'Guest')
    return render_template("payments.html", payments=all_payments, total_revenue=total_revenue, username=username)

@app.route('/add_payment', methods=['GET', 'POST'])
def add_payment():
    bookings = db_session.query(Booking).all()
    username = session.get('username', 'Guest')
    if request.method == 'POST':
        try:
            amount = request.form.get('amount')
            status = request.form.get('status')
            payment_date = request.form.get('payment_date')
            booking_id = request.form.get('booking_id')

            if not booking_id or not amount or not payment_date:
                flash("All fields are required!", "error")
                return redirect('/add_payment')

            new_payment = Payment(
                booking_id=int(booking_id),
                amount=float(amount),
                status=status.strip(),
                payment_date=datetime.strptime(payment_date, '%Y-%m-%d')
            )
            db_session.add(new_payment)
            db_session.commit()
            flash("Payment added successfully!", "success")
            return redirect('/payments')
        except Exception as e:
            db_session.rollback()
            flash(f"Error adding payment: {e}", "error")
            return redirect('/add_payment')
    return render_template("add_payment.html", bookings=bookings, username=username)

@app.route('/edit_payment/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(payment_id):
    payment = db_session.query(Payment).get(payment_id)
    if not payment:
        flash("Payment not found!", "error")
        return redirect('/payments')
    bookings = db_session.query(Booking).all()
    username = session.get('username', 'Guest')

    if request.method == 'POST':
        try:
            amount = request.form.get('amount')
            status = request.form.get('status')
            payment_date = request.form.get('payment_date')

            if not amount or not payment_date:
                flash("Amount and Payment Date are required!", "error")
                return redirect(url_for('edit_payment', payment_id=payment_id))

            payment.amount = float(amount)
            payment.status = status.strip()
            payment.payment_date = datetime.strptime(payment_date, '%Y-%m-%d')

            db_session.commit()
            flash("Payment updated successfully!", "success")
            return redirect('/payments')
        except Exception as e:
            db_session.rollback()
            flash(f"Error updating payment: {e}", "error")
            return redirect(url_for('edit_payment', payment_id=payment_id))

    if isinstance(payment.payment_date, datetime):
        payment_date_value = payment.payment_date.strftime('%Y-%m-%d')
    else:
        payment_date_value = payment.payment_date

    return render_template(
        "edit_payment.html",
        payment=payment,
        bookings=bookings,
        payment_date_value=payment_date_value,
        username=username
    )

@app.route('/delete_payment/<int:payment_id>')
def delete_payment(payment_id):
    payment = db_session.query(Payment).get(payment_id)
    if payment:
        db_session.delete(payment)
        db_session.commit()
    return redirect('/payments')

# ---------------- RETURNS ----------------
@app.route('/returns')
def returns():
    returned_bookings = db_session.query(Booking).filter(Booking.status == "Returned").all()
    username = session.get('username', 'Guest')
    return render_template("returns.html", returned=returned_bookings, username=username)

# ---------------- RUN APP ----------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# ------------------ CAR ------------------
class Car(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    brand = Column(String)
    model = Column(String)
    number_plate = Column(String)
    status = Column(String)

    # Relationship → Cars have many bookings
    bookings = relationship("Booking", back_populates="car")


# ------------------ CUSTOMER ------------------
class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)
    phone = Column(String)

    # Relationship → Customer has many bookings
    bookings = relationship("Booking", back_populates="customer")


# ------------------ BOOKING ------------------
class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True)

    # link customer
    customer_id = Column(Integer, ForeignKey("customers.id"))
    customer = relationship("Customer", back_populates="bookings")

    # link car
    car_id = Column(Integer, ForeignKey("cars.id"))
    car = relationship("Car", back_populates="bookings")

    start_date = Column(String)
    end_date = Column(String)
    status = Column(String)

    # Payments linked to booking
    payments = relationship("Payment", back_populates="booking")


# ------------------ PAYMENT ------------------
class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)

    booking_id = Column(Integer, ForeignKey("bookings.id"))
    booking = relationship("Booking", back_populates="payments")

    amount = Column(Integer)
    status = Column(String)
    payment_date = Column(String)
# ------------------ USER ------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
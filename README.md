

A full-featured e-commerce web application built with **Django 6**, **MySQL**, **Redis**, and **Celery**.

The project is designed as a modular online shopping platform with separate applications for user accounts, products, categories, cart management, wishlists, orders, payments, reviews, dashboards, and notifications.

It also includes integrations for **M-Pesa Daraja**, **Africa's Talking**, and **SMTP email**, making the application suitable for a Kenya-focused e-commerce environment.

---

## Overview

The Online Store is built around a simple goal: provide a complete shopping experience from browsing products to placing an order and making a payment.

The application is divided into multiple Django apps rather than putting everything into one large application. Each app has a specific responsibility, which makes the project easier to maintain and extend.

The main application areas are:

* Customer accounts and authentication
* Product management
* Product categories
* Shopping cart
* Wishlist
* Checkout and orders
* M-Pesa payments
* Product reviews
* Dashboard functionality
* Notifications
* Email communication
* SMS communication
* Background processing with Celery
* Redis caching/task brokering
* Request rate limiting

The application also uses Django's timezone support with:

```python
TIME_ZONE = "Africa/Nairobi"
USE_TZ = True
```

which is appropriate for an application operating in the Kenyan market.

---

# Main Features

## Customer Accounts

The project uses a custom user model rather than Django's default user model.

```python
AUTH_USER_MODEL = "accounts.CustomUser"
```

The `accounts` application is responsible for user-related functionality.

This allows the project to extend Django's authentication system and keep customer-specific information separate from the rest of the store.

The application uses Django's built-in password validation framework, including:

* User attribute similarity validation
* Minimum password length validation
* Common password detection
* Numeric password detection

This provides a stronger authentication foundation than accepting arbitrary passwords.

---

## Product Management

Products are managed through the dedicated `products` application.

The product system forms the core of the store because it provides the items customers browse and purchase.

The project separates product management from categories, allowing products to be organized into a structured catalog.

Typical product information includes the information required by the storefront and purchasing system, such as product details, pricing, availability, and associated media.

Uploaded product or other user-generated media is handled through Django's media configuration:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

---

## Product Categories

The `categories` application is responsible for organizing products into categories.

Keeping categories in their own Django application makes it easier to expand the catalog without tightly coupling category logic to product logic.

A category-based structure also makes it possible to build storefront navigation around groups of related products.

---

## Shopping Cart

The `cart` application manages the customer's shopping cart.

The cart sits between browsing and checkout:

```text
Product
   ↓
Add to Cart
   ↓
Shopping Cart
   ↓
Checkout
   ↓
Order
   ↓
Payment
```

The cart system is responsible for keeping track of products selected by a customer before the final order is placed.

---

## Wishlist

The `wishlist` application provides customers with a separate place to keep products they are interested in.

Unlike the shopping cart, a wishlist represents products that the customer may want to purchase later.

This keeps the two concepts separate:

```text
Wishlist
    = Products I am interested in

Cart
    = Products I intend to purchase
```

---

# Orders and Checkout

The `orders` application handles the order side of the shopping process.

Once a customer is ready to purchase, the selected products move from the shopping process into an order.

The order system provides a place to maintain information such as:

* Customer
* Products
* Quantities
* Prices
* Total amount
* Order status
* Payment information
* Timestamps

The general flow is:

```text
Customer
   │
   ▼
Browse Products
   │
   ▼
Add Products to Cart
   │
   ▼
Review Cart
   │
   ▼
Checkout
   │
   ▼
Create Order
   │
   ▼
Initiate Payment
   │
   ▼
Payment Callback
   │
   ▼
Update Payment / Order
```

Keeping orders in their own application allows order-related business logic to remain independent from the product catalog and shopping cart.

---

# M-Pesa Payments

One of the key integrations in the project is **M-Pesa Daraja**.

The project includes configuration for the credentials and information required to communicate with the M-Pesa API:

```text
MPESA_CONSUMER_KEY
MPESA_CONSUMER_SECRET
MPESA_SHORTCODE
MPESA_PASSKEY
MPESA_CALLBACK_URL
MPESA_CALLBACK_SECRET
MPESA_ENV
```

The payment environment is controlled through:

```env
MPESA_ENV=sandbox
```

for development/testing, or:

```env
MPESA_ENV=production
```

when using the production environment.

## Payment flow

The payment architecture is designed around the following flow:

```text
Customer
    │
    ▼
Checkout
    │
    ▼
Create Order
    │
    ▼
Initiate M-Pesa Payment
    │
    ▼
Customer Completes Payment
    │
    ▼
M-Pesa Processes Transaction
    │
    ▼
Callback Sent to Application
    │
    ▼
Payment Verified
    │
    ▼
Order Updated
```

The callback endpoint is particularly important because M-Pesa communicates the final transaction result back to the application.

The project also has a dedicated:

```env
MPESA_CALLBACK_SECRET
```

which can be used as part of callback validation.

### Important security rule

M-Pesa credentials should **never** be placed directly into source code or committed to Git.

Use the `.env` file or another secure secrets-management mechanism.

For example:

```env
MPESA_CONSUMER_KEY=your-consumer-key
MPESA_CONSUMER_SECRET=your-consumer-secret
MPESA_SHORTCODE=your-shortcode
MPESA_PASSKEY=your-passkey
MPESA_CALLBACK_URL=https://your-domain.com/payments/callback/
MPESA_CALLBACK_SECRET=your-callback-secret
MPESA_ENV=sandbox
```

For production, the callback endpoint should be publicly accessible through HTTPS.

---

# Reviews

The `reviews` application handles product reviews.

Reviews provide customers with a way to share their experience with products and give future customers additional information before making a purchase.

A review system is also useful to the store because it provides feedback about products and customer satisfaction.

The review functionality is kept separate from the product application so that review-specific logic does not unnecessarily complicate the product catalog.

---

# Dashboard

The `dashboard` application provides the application's dashboard functionality.

The dashboard is intended to give the appropriate users a centralized view of important store information.

Depending on the user's permissions, dashboard information can include areas such as:

* Products
* Orders
* Customers
* Payments
* Reviews
* Store activity
* Sales information

Keeping dashboard functionality in its own application allows it to evolve independently from the customer-facing storefront.

---

# Notifications

The `notifications` application handles notifications within the platform.

Notifications are useful for keeping customers informed about important events.

Examples include:

* Order updates
* Payment updates
* Account-related events
* System notifications
* Other important store activity

The notification system works alongside the project's email and SMS integrations, allowing communication functionality to remain separate from the individual applications generating the events.

---

# Email

The application is configured to send email through SMTP.

The current configuration uses Gmail's SMTP server:

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
```

The email credentials are loaded from environment variables:

```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

The default sender is taken from:

```python
DEFAULT_FROM_EMAIL = os.environ.get("EMAIL_HOST_USER")
```

For Gmail, an App Password should be used where required rather than storing a normal account password in the application.

---

# Africa's Talking

The project also contains configuration for **Africa's Talking**.

The credentials are loaded through environment variables:

```env
AFRICASTALKING_USERNAME=your-username
AFRICASTALKING_API_KEY=your-api-key
```

This integration provides the application with a way to communicate with customers through SMS and related Africa's Talking services.

It can be useful for events such as:

* Order notifications
* Payment notifications
* Customer updates
* Account-related messages

The exact messages and triggers are controlled by the application's notification/business logic.

---

# Background Tasks with Celery

Some operations are better handled outside the normal Django request/response cycle.

The project uses **Celery** for background processing.

The Celery broker is configured through:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
```

The result backend can be configured separately:

```env
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

This architecture allows time-consuming work to be moved into background workers.

For example:

```text
Django
  │
  ├── Customer Request
  │
  └── Background Task
          │
          ▼
        Redis
          │
          ▼
     Celery Worker
          │
          ▼
    Task Processing
```

This becomes particularly useful for operations such as sending notifications or communicating with external services.

---

# Redis

Redis is used by the project as the Celery broker and can also be used as a shared cache in production.

The default development connection is:

```text
redis://localhost:6379/0
```

To check whether Redis is running:

```bash
redis-cli ping
```

A working Redis installation should return:

```text
PONG
```

---

# Rate Limiting

The application uses `django-ratelimit` to protect selected parts of the application from excessive requests.

The current development cache configuration is:

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

RATELIMIT_USE_CACHE = "default"
```

`LocMemCache` is suitable for local development, particularly when the application is running as a single process.

For production, a shared Redis cache is recommended when multiple Django workers are running.

This is important because rate-limit information needs to be shared between workers.

---

# Django Applications

The project is split into the following Django applications:

```text
accounts
core
common
products
categories
cart
wishlist
orders
payments
reviews
dashboard
notifications
```

Each application has a specific responsibility.

### `accounts`

Custom user model and account-related functionality.

### `core`

Core/shared functionality used across the project.

The settings file currently includes:

```python
"core.context_processors.global_context"
```

which means the core application also provides global template context.

### `common`

Shared functionality used across different parts of the project.

### `products`

Product catalog and product-related functionality.

### `categories`

Product category management.

### `cart`

Shopping cart functionality.

### `wishlist`

Wishlist functionality.

### `orders`

Order creation and order management.

### `payments`

Payment-related functionality, including the M-Pesa integration.

### `reviews`

Product reviews and ratings.

### `dashboard`

Dashboard functionality.

### `notifications`

Notifications and customer communication functionality.

---

# Technology Stack

## Backend

* **Python**
* **Django 6**
* **Django ORM**
* **MySQL**
* **Celery**
* **Redis**
* **django-ratelimit**

## Payment

* **M-Pesa Daraja API**

## Communication

* **Africa's Talking**
* **SMTP / Gmail**

## Frontend

The application uses Django's template system together with static assets.

The project contains:

```text
templates/
static/
media/
```

for templates, frontend assets, and uploaded files.

---

# Project Structure

The project follows a standard Django structure with multiple applications:

```text
project-root/
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── accounts/
├── core/
├── common/
├── products/
├── categories/
├── cart/
├── wishlist/
├── orders/
├── payments/
├── reviews/
├── dashboard/
├── notifications/
│
├── templates/
├── static/
├── media/
│
├── manage.py
├── requirements.txt
├── .env
└── README.md
```

The exact contents of each application may include additional files such as:

```text
models.py
views.py
urls.py
forms.py
admin.py
apps.py
tasks.py
```

depending on the functionality implemented in that application.

---

# Requirements

Before running the project locally, make sure the following are available:

* Python 3
* pip
* MySQL
* Redis
* Git
* A Python virtual environment

For the external services, you will need the appropriate credentials if you want to use their functionality:

* M-Pesa Daraja credentials
* Africa's Talking credentials
* SMTP credentials

---

# Getting Started

## 1. Clone the project

```bash
git clone <repository-url>
cd <project-directory>
```

Replace `<repository-url>` and `<project-directory>` with the actual repository information.

---

## 2. Create a virtual environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` does not exist yet, it can be generated from the active environment with:

```bash
pip freeze > requirements.txt
```

---

# Environment Variables

The application uses `python-dotenv` to load environment variables from a `.env` file.

The important detail is that `BASE_DIR` must be defined before loading the environment file:

```python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)
```

The `.env` file should be located in the project root:

```text
project-root/
├── .env
├── manage.py
├── config/
└── ...
```

---

# Example `.env`

A local development environment can look similar to:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Database
DB_NAME=onlinestore
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306

# M-Pesa
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=
MPESA_PASSKEY=
MPESA_CALLBACK_URL=
MPESA_CALLBACK_SECRET=
MPESA_ENV=sandbox

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Africa's Talking
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=

# Email
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

Do not copy real production credentials into a public README or commit them to Git.

---

# Database Setup

The project uses MySQL.

The database currently configured by the project is:

```text
Database: onlinestore
Host: localhost
Port: 3306
User: root
```

Create the database before running Django migrations.

For example:

```sql
CREATE DATABASE onlinestore
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

The project uses `utf8mb4`, which provides proper support for a wide range of Unicode characters.

---

# Recommended Database Configuration

Database credentials should ideally come from environment variables instead of being hard-coded in `settings.py`.

For example:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "onlinestore"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": (
                "SET sql_mode='STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'"
            ),
        },
    }
}
```

This keeps the database configuration portable between development and production.

---

# Migrations

After creating the database, apply the Django migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

To see the migration status:

```bash
python manage.py showmigrations
```

For normal development, remember to create migrations whenever you change Django models:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

# Create an Administrator

Create a Django superuser:

```bash
python manage.py createsuperuser
```

Follow the prompts and provide the requested username, email, and password.

After starting the application, the Django administration area will normally be available at:

```text
/admin/
```

---

# Running the Application

Start the Django development server:

```bash
python manage.py runserver
```

By default, Django will make the application available at:

```text
http://127.0.0.1:8000/
```

---

# Running Redis

Make sure Redis is running before starting Celery.

Verify it with:

```bash
redis-cli ping
```

Expected result:

```text
PONG
```

---

# Running Celery

With Redis running, start the Celery worker.

On Windows:

```bash
celery -A config worker --loglevel=info --pool=solo
```

On Linux/macOS:

```bash
celery -A config worker --loglevel=info
```

The `--pool=solo` option is commonly useful when running Celery locally on Windows.

The Celery application configuration may vary depending on the project's Celery setup.

---

# Static Files

Static files are configured using:

```python
STATIC_URL = "static/"
```

The project uses a dedicated static directory:

```text
static/
```

This is where application frontend assets such as CSS, JavaScript, images, and other static resources can be stored.

In a production environment, collect the static files with:

```bash
python manage.py collectstatic
```

---

# Media Files

Uploaded files are stored under:

```text
media/
```

with the following Django configuration:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

During development, Django can be configured to serve these files through the project's URL configuration.

For production, uploaded media should normally be handled by the production web server or a dedicated object-storage service.

---

# Authentication

The project uses:

```python
AUTH_USER_MODEL = "accounts.CustomUser"
```

This means Django's standard user model has been replaced by the application's custom user model.

This setting should not be changed casually after the project has accumulated production data and migrations.

The custom user model should remain consistent throughout the application's lifecycle.

---

# Security

Security is an important part of the project because the application handles customer accounts, orders, and payments.

The project already includes several Django security settings that are enabled when `DEBUG=False`.

These include:

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

These settings help enforce secure communication and protect cookies when the application is running over HTTPS.

---

# Development vs Production

Development and production should be treated as separate environments.

## Development

A typical local setup uses:

```text
Django
   │
   ├── MySQL
   │
   ├── Redis
   │
   └── Celery
```

M-Pesa should normally use:

```env
MPESA_ENV=sandbox
```

during development and testing.

## Production

A production environment should use:

```text
Internet
   │
   ▼
HTTPS
   │
   ▼
Web Server / Reverse Proxy
   │
   ▼
Django
   │
   ├── MySQL
   ├── Redis
   └── Celery
```

Production should use:

```env
DEBUG=False
```

and valid production credentials.

---

# Production Security Checklist

Before deploying the application:

* [ ] Set `DEBUG=False`
* [ ] Use a strong production `SECRET_KEY`
* [ ] Configure `ALLOWED_HOSTS`
* [ ] Use HTTPS
* [ ] Configure production database credentials
* [ ] Keep `.env` out of Git
* [ ] Use production M-Pesa credentials
* [ ] Use an HTTPS M-Pesa callback URL
* [ ] Protect and validate payment callbacks
* [ ] Use a shared Redis cache for multiple workers
* [ ] Configure Celery workers
* [ ] Configure email credentials securely
* [ ] Configure Africa's Talking credentials securely
* [ ] Run `python manage.py check --deploy`
* [ ] Run database migrations
* [ ] Run `collectstatic`
* [ ] Configure media storage
* [ ] Test authentication
* [ ] Test checkout and orders
* [ ] Test payment callbacks
* [ ] Test notifications
* [ ] Set up database backups
* [ ] Set up application logging

---

# Important Payment Considerations

Payment handling should be treated as one of the most sensitive parts of the application.

A payment callback should not simply be trusted because it reaches the callback URL.

The payment logic should ensure that:

* The callback corresponds to an existing order.
* The transaction reference is valid.
* The amount matches the expected order amount.
* The payment status is handled correctly.
* Duplicate callbacks do not create duplicate payment records or orders.
* Failed transactions do not accidentally mark orders as paid.
* Production callback endpoints are protected with HTTPS and appropriate validation.

The application should also maintain a clear distinction between:

```text
Order Created
      ↓
Payment Pending
      ↓
Payment Successful
      ↓
Order Paid
```

and failed/cancelled payment states.

---

# Useful Management Commands

## Start development server

```bash
python manage.py runserver
```

## Check the project

```bash
python manage.py check
```

## Run deployment checks

```bash
python manage.py check --deploy
```

## Create migrations

```bash
python manage.py makemigrations
```

## Apply migrations

```bash
python manage.py migrate
```

## View migration status

```bash
python manage.py showmigrations
```

## Create administrator

```bash
python manage.py createsuperuser
```

## Open Django shell

```bash
python manage.py shell
```

## Run tests

```bash
python manage.py test
```

## Collect static files

```bash
python manage.py collectstatic
```

---

# Testing

The application should be tested at both the individual app level and as a complete shopping workflow.

Important areas to test include:

### Accounts

* Registration
* Login
* Logout
* Password validation
* Authentication permissions

### Products

* Product listing
* Product details
* Category filtering
* Product availability

### Cart

* Adding products
* Removing products
* Updating quantities
* Calculating totals

### Wishlist

* Adding products
* Removing products
* Viewing wishlist

### Orders

* Creating orders
* Correct totals
* Order ownership
* Order status changes

### Payments

* Payment initiation
* Successful payments
* Failed payments
* Cancelled payments
* Invalid callbacks
* Duplicate callbacks

### Reviews

* Creating reviews
* Editing reviews where supported
* Deleting reviews where supported
* Preventing unauthorized review changes

### Notifications

* Creating notifications
* Marking notifications as read
* Sending email/SMS where configured

Run the test suite with:

```bash
python manage.py test
```

---

# Environment Variables and Secrets

The following values should be treated as sensitive:

```text
SECRET_KEY

MPESA_CONSUMER_KEY
MPESA_CONSUMER_SECRET
MPESA_PASSKEY
MPESA_CALLBACK_SECRET

AFRICASTALKING_API_KEY

EMAIL_HOST_PASSWORD

Database passwords
```

Do not commit these values to GitHub or another public repository.

The `.env` file should be ignored:

```gitignore
.env
.env.*
```

For production deployments, a proper secrets manager is preferable to storing credentials directly on the server in plain text.

---

# Recommended `.gitignore`

A typical `.gitignore` for the project is:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo

# Virtual environments
venv/
.venv/
env/

# Environment variables
.env
.env.*

# Django
*.log
db.sqlite3

# Collected static files
staticfiles/

# Uploaded media
media/

# IDEs
.vscode/
.idea/

# Operating system files
.DS_Store
Thumbs.db
```

If MySQL is the only production/development database, `db.sqlite3` may not be relevant to the project, but leaving it ignored prevents an accidental local SQLite database from being committed.

---

# Development Workflow

A normal development session looks something like this:

### Terminal 1 — MySQL

Start MySQL and make sure the `onlinestore` database is available.

### Terminal 2 — Redis

Start Redis.

Verify:

```bash
redis-cli ping
```

### Terminal 3 — Celery

Activate the virtual environment and start Celery:

```bash
celery -A config worker --loglevel=info --pool=solo
```

### Terminal 4 — Django

Activate the virtual environment and start Django:

```bash
python manage.py runserver
```

The complete local environment then looks like:

```text
                  Django
                    │
          ┌─────────┼─────────┐
          │         │         │
          ▼         ▼         ▼
        MySQL     Redis     External APIs
                    │
                    ▼
                  Celery
```

---

# Application Flow

The main customer journey can be represented as:

```text
                    Customer
                       │
                       ▼
                Browse Products
                       │
                       ▼
                  Categories
                       │
                       ▼
                Product Details
                  │         │
                  │         └──────────► Wishlist
                  │
                  ▼
                Add to Cart
                       │
                       ▼
                  View Cart
                       │
                       ▼
                   Checkout
                       │
                       ▼
                  Create Order
                       │
                       ▼
                M-Pesa Payment
                       │
                       ▼
              Payment Callback
                       │
                       ▼
                Update Payment
                       │
                       ▼
                Update Order
                       │
                       ▼
              Customer Notification
```

This separation allows each part of the application to handle its own responsibilities while still working together as one store.

---

# Project Architecture

The project follows a modular architecture.

Instead of building the entire store inside one Django application, functionality is separated into individual apps:

```text
                        Online Store
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
       Accounts            Catalog           Commerce
          │                  │                  │
          ▼                  ▼                  ▼
      accounts        products/categories     cart
                                                │
                                                ▼
                                            wishlist
                                                │
                                                ▼
                                              orders
                                                │
                                                ▼
                                             payments
                                                │
                                                ▼
                                             reviews
```

Supporting functionality sits alongside the main commerce flow:

```text
core
common
dashboard
notifications
```

This structure makes it easier to locate code and work on individual areas without unnecessarily affecting the rest of the system.

---

# Why the Project Uses Celery and Redis

Not every operation needs to happen while a customer is waiting for an HTTP response.

For example, sending an external notification can take longer than a normal database operation.

With Celery, the application can hand a task to a background worker:

```text
Django Request
     │
     ▼
Create Task
     │
     ▼
Redis
     │
     ▼
Celery Worker
     │
     ▼
Perform Task
```

This keeps the main application responsive and gives the project a foundation for scheduled and asynchronous processing.

---

# Time Zone

The application uses the Nairobi timezone:

```python
TIME_ZONE = "Africa/Nairobi"
```

with timezone-aware datetimes:

```python
USE_TZ = True
```

This is important for an application where orders, payments, notifications, and other events need meaningful timestamps.

---

# Troubleshooting

## `BASE_DIR is not defined`

If Pylance reports:

```text
"BASE_DIR" is not defined
```

make sure the path is declared before it is used.

Correct:

```python
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)
```

Incorrect:

```python
load_dotenv(BASE_DIR / ".env", override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
```

---

## MySQL connection problems

Check:

* MySQL is running.
* The `onlinestore` database exists.
* The username is correct.
* The password is correct.
* MySQL is listening on port `3306`.
* The MySQL user has permission to access the database.

---

## Redis connection problems

Check Redis:

```bash
redis-cli ping
```

If Redis is running, the result should be:

```text
PONG
```

Also check:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
```

---

## Celery worker does not start

Check that:

1. The virtual environment is activated.
2. Celery is installed.
3. Redis is running.
4. The Django project can start without errors.
5. The `config` package contains the Celery configuration expected by the project.

Then try:

```bash
celery -A config worker --loglevel=info --pool=solo
```

---

## `.env` values are not loading

Make sure the `.env` file is in the project root:

```text
project-root/
├── .env
├── manage.py
└── config/
```

Also make sure `BASE_DIR` is defined before `load_dotenv()`:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)
```

---

## Static files are not loading

Check:

```python
STATIC_URL = "static/"
```

and make sure the `static/` directory exists.

For production, run:

```bash
python manage.py collectstatic
```

Also check that your templates correctly load static files.

---

## Migration problems

First inspect the migration state:

```bash
python manage.py showmigrations
```

Then:

```bash
python manage.py makemigrations
python manage.py migrate
```

Do not delete migration files from a production project simply to resolve a migration error. Investigate the actual migration dependency or database-state problem first.

---

# Production Deployment

The application is configured with several production security settings, but deployment still requires proper server infrastructure.

A typical production architecture would look like:

```text
                         Internet
                            │
                            ▼
                       HTTPS Domain
                            │
                            ▼
                    Reverse Proxy
                            │
                            ▼
                    Django / WSGI
                       │       │
              ┌────────┘       └────────┐
              ▼                         ▼
            MySQL                     Redis
                                        │
                                        ▼
                                      Celery
                                        │
                                        ▼
                               Background Tasks
```

Static and media files should normally be handled separately from Django application requests.

---

# Production Checklist

Before going live:

* [ ] Set `DEBUG=False`
* [ ] Set a strong `SECRET_KEY`
* [ ] Configure production `ALLOWED_HOSTS`
* [ ] Enable HTTPS
* [ ] Configure the production database
* [ ] Configure Redis
* [ ] Configure Celery workers
* [ ] Configure production M-Pesa credentials
* [ ] Configure the production M-Pesa callback URL
* [ ] Verify payment callback validation
* [ ] Configure SMTP
* [ ] Configure Africa's Talking
* [ ] Replace local-memory caching with shared production caching
* [ ] Run database migrations
* [ ] Run `collectstatic`
* [ ] Configure media storage
* [ ] Run `python manage.py check --deploy`
* [ ] Run automated tests
* [ ] Test registration and login
* [ ] Test product browsing
* [ ] Test cart and wishlist
* [ ] Test checkout
* [ ] Test successful and failed payments
* [ ] Test notifications
* [ ] Configure database backups
* [ ] Configure application logging
* [ ] Monitor Celery workers
* [ ] Monitor Redis
* [ ] Monitor the production database

---

# Current Configuration Summary

The project currently brings together the following components:

| Component         | Purpose                 |
| ----------------- | ----------------------- |
| Django 6          | Main web framework      |
| MySQL             | Primary database        |
| Custom User Model | Customer authentication |
| Products          | Product catalog         |
| Categories        | Product organization    |
| Cart              | Shopping cart           |
| Wishlist          | Saved products          |
| Orders            | Order management        |
| Payments          | Payment processing      |
| M-Pesa Daraja     | M-Pesa payments         |
| Reviews           | Product reviews         |
| Dashboard         | Store dashboard         |
| Notifications     | Customer notifications  |
| Redis             | Message broker/cache    |
| Celery            | Background tasks        |
| django-ratelimit  | Request protection      |
| Africa's Talking  | SMS/communication       |
| SMTP/Gmail        | Email delivery          |

---

# Future Development

Because the application is already separated into multiple Django apps, additional functionality can be added without turning the project into one large codebase.

Possible future additions include:

* Advanced product search
* Product filtering and sorting
* Product variants
* Inventory tracking
* Discount and coupon management
* Promotions
* Delivery and shipping management
* Order tracking
* Refund management
* Multiple payment providers
* Sales analytics
* Customer analytics
* REST API
* Mobile application
* Automated scheduled tasks
* Cloud media storage
* Automated deployment
* Error monitoring
* More extensive automated testing

These are areas for continued development rather than requirements for the current application.

---

# Contributing

If this project is being developed by multiple people, keep changes organized by feature.

A typical workflow is:

```bash
git checkout -b feature/feature-name
```

Make the changes, then check the project:

```bash
python manage.py check
python manage.py test
```

If models were changed:

```bash
python manage.py makemigrations
python manage.py migrate
```

Then commit the changes:

```bash
git add .
git commit -m "Add feature"
git push origin feature/feature-name
```

Before opening a pull request, make sure no `.env` files, API keys, passwords, or other secrets are included.

---

# License

Add the project's actual license here.

For a private/proprietary application, this section can state that the source code is proprietary and may not be redistributed without permission.

If the project is open source, replace this section with the appropriate license, such as MIT, Apache 2.0, or GPL.

---

# Author

**Online Store**

Built with Django and designed as a modular e-commerce platform.

---

# Final Notes

This project is structured as a complete Django e-commerce application rather than a single-purpose demo.

The separation between accounts, products, categories, cart, wishlist, orders, payments, reviews, dashboard, and notifications provides a clean foundation for continued development.

The external integrations are also separated from the core shopping experience:

```text
                    Online Store
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
     Store             Payments        Communication
       │                 │                 │
       ▼                 ▼                 ▼
 Django Apps          M-Pesa        Email / SMS
       │
       ▼
    MySQL
       │
       ▼
   Redis / Celery
```

For local development, the main services are Django, MySQL, and Redis, with Celery running as a background worker.

For production, the application should run with `DEBUG=False`, HTTPS, a properly configured database, shared caching, secure credentials, protected payment callbacks, background workers, backups, and appropriate monitoring.

The `.env` file should always remain private, and production credentials should never be committed to the repository.

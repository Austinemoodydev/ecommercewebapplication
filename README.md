# Online Shop — Django E-Commerce Platform

A full-featured, modular e-commerce platform built with **Django 6**, **MySQL**, **Redis**, **Celery**, and a server-rendered Bootstrap-based frontend.

The application is designed for real online retail operations, with particular support for the Kenyan market through **M-Pesa Daraja**, **Africa's Talking**, Kenyan Shilling pricing, delivery management, inventory control, customer management, refunds, returns, reporting, and role-based store administration.

> **Current status:** The application is being completed and hardened on localhost before production deployment. Localhost is treated as the staging environment. Production credentials and infrastructure must be configured separately before launch.

---

# Table of Contents

* [Overview](#overview)
* [Major Features](#major-features)
* [Customer Experience](#customer-experience)
* [Authentication and Accounts](#authentication-and-accounts)
* [Store Staff and Permissions](#store-staff-and-permissions)
* [Product Catalog](#product-catalog)
* [Pricing](#pricing)
* [Inventory Management](#inventory-management)
* [Shopping Cart](#shopping-cart)
* [Wishlist](#wishlist)
* [Checkout](#checkout)
* [Guest Checkout](#guest-checkout)
* [Orders](#orders)
* [M-Pesa Payments](#m-pesa-payments)
* [Returns and Refunds](#returns-and-refunds)
* [Delivery Management](#delivery-management)
* [Invoices, Receipts and Credit Notes](#invoices-receipts-and-credit-notes)
* [Reviews](#reviews)
* [CRM](#crm)
* [Notifications](#notifications)
* [Abandoned Carts](#abandoned-carts)
* [Analytics and Reports](#analytics-and-reports)
* [Store Settings](#store-settings)
* [SEO](#seo)
* [Security](#security)
* [Background Processing](#background-processing)
* [Technology Stack](#technology-stack)
* [Project Architecture](#project-architecture)
* [Project Structure](#project-structure)
* [Local Development Setup](#local-development-setup)
* [Environment Variables](#environment-variables)
* [Database Setup](#database-setup)
* [Redis and Celery](#redis-and-celery)
* [Testing](#testing)
* [Development vs Production](#development-vs-production)
* [Production Checklist](#production-checklist)
* [Remaining Work](#remaining-work)
* [Author](#author)

---

# Overview

Online Shop is not a basic product-listing website. It is a multi-module commerce application covering the main operational areas required to run an online retail business.

The system supports the complete flow from:

```text
Customer
   │
   ▼
Browse Products
   │
   ▼
Product Details
   │
   ├────────────► Wishlist
   │
   ▼
Shopping Cart
   │
   ▼
Checkout
   │
   ▼
Inventory Reservation
   │
   ▼
Order Creation
   │
   ▼
M-Pesa Payment
   │
   ▼
Payment Callback
   │
   ▼
Payment Verification
   │
   ▼
Inventory Consumption
   │
   ▼
Order Processing
   │
   ▼
Delivery
   │
   ▼
Invoice / Receipt
   │
   ▼
Customer Notification
```

The project is separated into Django applications and service modules so that accounts, products, inventory, orders, payments, delivery, CRM, notifications and administration do not have to live inside one large application.

---

# Major Features

The application currently includes:

* Customer registration and authentication
* Email verification
* Password reset
* Google customer authentication
* Customer profiles and avatars
* Saved customer addresses
* Guest checkout
* Guest order access
* Separate customer, store-staff and system-admin authentication
* Store staff management
* Role-based access control
* Product management
* Product categories
* Brands
* Product images and galleries
* Product variants
* Product pricing and sale pricing
* Cost-price tracking
* Inventory management
* Reserved inventory
* Inventory movement history
* Low-stock monitoring
* Shopping cart
* Wishlist
* Coupons and promotions infrastructure
* Checkout
* Server-authoritative pricing
* Configurable tax
* Minimum-order rules
* M-Pesa STK Push
* M-Pesa callback processing
* Payment transaction tracking
* Orders and order statuses
* Delivery management
* Delivery providers
* Delivery events and attempts
* Parcel/tracking references
* Customer order tracking
* Returns
* Refund requests
* Partial and full refund status handling
* Credit notes
* Invoices
* Receipts
* Product reviews
* Verified-purchase review restrictions
* CRM/customer notes
* Customer notifications
* Email communication
* SMS integration
* Abandoned-cart tracking
* Store analytics and reports
* Store settings
* SEO sitemap
* robots.txt
* Product structured data
* Rate limiting
* Upload security
* Custom DEBUG=False error pages
* Automated regression tests
* Redis integration
* Celery background processing

---

# Customer Experience

Customers can browse the storefront without accessing store-management functionality.

The customer-facing system provides:

* Store homepage
* Product catalog
* Product search
* Category browsing
* Product filtering and sorting
* Product detail pages
* Sale/offer products
* Featured products
* Product images
* Product ratings and reviews
* Wishlist
* Shopping cart
* Checkout
* Delivery selection
* M-Pesa payment
* Order confirmation
* Order details
* Order tracking
* Invoices and receipts
* Return/refund requests
* Customer notifications
* Profile management
* Address management

The storefront and administration interfaces are intentionally separated.

---

# Authentication and Accounts

The application uses a custom Django user model:

```python
AUTH_USER_MODEL = "accounts.CustomUser"
```

Authentication functionality includes:

* Customer registration
* Unique email validation
* Customer login
* Logout
* Password validation
* Password reset
* Email verification
* Customer profile
* Avatar upload
* Saved addresses
* Default delivery address
* Google authentication
* Login rate limiting

## Authentication separation

The application separates three authentication contexts.

### Customer authentication

Customer login:

```text
/accounts/login/
```

Customers can use normal account credentials and supported Google authentication.

Successful customer authentication returns the user to the shopping experience rather than the management dashboard.

### Store staff authentication

Store-management users authenticate through:

```text
/staff/login/
```

This interface is intended only for authorized store employees.

There is no public staff registration process.

### System administration

Django system administration remains separate:

```text
/admin/
```

System administration is restricted to Django superusers.

A normal store employee should not gain system-administrator access simply because they have store-management permissions.

---

# Store Staff and Permissions

The application includes role-based store administration.

Current store roles include:

| Role            | Purpose                                   |
| --------------- | ----------------------------------------- |
| Store Owner     | Highest store-management authority        |
| Store Manager   | Broad operational management              |
| Orders Staff    | Order and delivery operations             |
| Inventory Staff | Product and inventory operations          |
| Finance Staff   | Payments, refunds and financial reporting |
| Support Staff   | Customer support, CRM and notifications   |

Permissions are enforced server-side rather than relying only on hidden navigation links.

Users can hold multiple authorized store roles where required.

Store-management functionality includes staff creation, editing, role assignment and account activation/deactivation.

---

# Product Catalog

Products are managed through the product and dashboard modules.

Product information can include:

* Product name
* SKU
* Category
* Brand
* Description
* Regular selling price
* Discount/sale price
* Cost price
* Low-stock threshold
* Primary image
* Product gallery
* Featured status
* Active/inactive status

## Categories

Products can be organized into categories for storefront navigation and filtering.

## Brands

Products can be associated with brands, including brand imagery where configured.

## Product gallery

Products can have a primary image and additional gallery images.

## Product variants

The data model includes product variants with support for fields such as:

* Variant SKU
* Variant selling price
* Variant cost price
* Stock
* Reserved stock
* Low-stock threshold

Variant functionality provides a foundation for products that differ by attributes such as size, configuration or other options.

---

# Pricing

Money is stored using decimal values rather than floating-point values.

This is important for financial correctness.

Retail prices support:

* Regular price
* Discount price
* Variant price
* Cost price
* Order-item price snapshots
* Tax
* Delivery charges
* Discounts
* Refund calculations

The current retail-price policy normalizes retail catalog prices to whole Kenyan Shillings while retaining decimal storage internally.

For example:

```text
Internal value
75000.00

Customer display
KES 75,000
```

Money presentation uses thousands separators:

```text
KES 2,500
KES 45,500
KES 75,000
KES 1,250,000
```

Historical order and payment amounts remain financial records and should not be rewritten merely because catalog pricing changes later.

---

# Inventory Management

Inventory is integrated with checkout and orders.

The system distinguishes between:

```text
Physical Stock
      │
      ├── Reserved Stock
      │
      └── Available Stock
```

Available inventory can therefore be calculated from stock that has not already been reserved for another checkout/order.

Inventory functionality includes:

* Product stock
* Variant stock
* Reserved stock
* Available stock
* Low-stock thresholds
* Inventory movements
* Inventory reservation
* Inventory release
* Inventory consumption

Critical inventory operations use database locking where appropriate to reduce the risk of overselling during concurrent checkout/payment activity.

The general lifecycle is:

```text
Customer Checkout
       │
       ▼
Reserve Inventory
       │
       ├──── Payment fails/cancels ───► Release Inventory
       │
       ▼
Payment succeeds
       │
       ▼
Consume Reserved Inventory
```

---

# Shopping Cart

The cart supports the customer's pre-checkout shopping session.

Cart functionality includes:

* Add to cart
* Update quantity
* Increase quantity
* Decrease quantity
* Remove item
* Cart totals
* Guest cart handling
* Customer cart handling

State-changing cart operations use POST requests rather than mutation through GET URLs.

This improves both HTTP correctness and CSRF protection.

---

# Wishlist

Customers can save products separately from the shopping cart.

```text
Wishlist
   = products the customer may purchase later

Cart
   = products currently intended for checkout
```

Wishlist mutations also use protected state-changing requests.

---

# Checkout

Checkout is server-authoritative.

The browser is not trusted to determine the final amount that should be charged.

The server recalculates:

* Product prices
* Quantities
* Discounts
* Coupons
* Tax
* Delivery charges
* Final order total

This helps prevent customers from manipulating browser-side prices.

The general checkout flow is:

```text
Cart
  │
  ▼
Validate Products
  │
  ▼
Recalculate Prices
  │
  ▼
Apply Coupon
  │
  ▼
Calculate Tax
  │
  ▼
Calculate Delivery
  │
  ▼
Validate Minimum Order
  │
  ▼
Reserve Inventory
  │
  ▼
Create Order
```

---

# Guest Checkout

Customers are not required to create a permanent account before purchasing where guest checkout is enabled.

Guest checkout supports:

* Guest customer information
* Guest delivery information
* Guest order creation
* Guest payment
* Guest order confirmation
* Guest order details
* Guest tracking
* Guest invoice access
* Guest receipt access
* Guest return/refund access

Guest-access tokens are treated as capability credentials.

Only a hash of the guest token is stored in the database rather than storing the raw capability token directly.

Guest orders can later be associated with a customer account through the supported account/order-claim flow.

---

# Orders

Orders maintain snapshots of important purchase information.

Typical order information includes:

* Order number
* Customer or guest information
* Order items
* Quantity
* Item price
* Discounts
* Tax
* Delivery amount
* Total amount
* Payment status
* Order status
* Inventory state
* Delivery information
* Creation/update timestamps

## Order statuses

The application supports states including:

```text
Pending
Confirmed
Processing
Shipped
Delivered
Cancelled
```

## Payment statuses

Payment status is tracked separately from operational order status.

Examples include:

```text
Pending
Paid
Failed
Partially Refunded
Refunded
```

## Inventory states

Inventory reservation state is also tracked independently.

Examples include:

```text
Reserved
Released
Consumed
```

Keeping these states separate prevents one field from trying to represent the entire lifecycle of an order.

---

# M-Pesa Payments

The application integrates with **Safaricom M-Pesa Daraja**.

Supported payment functionality includes:

* STK Push initiation
* Checkout request tracking
* Merchant request tracking
* Payment status tracking
* M-Pesa receipt storage
* Customer phone storage
* Callback processing
* Payment amount verification
* Duplicate callback handling
* Failed-payment handling
* Cancelled-payment handling
* Inventory release
* Successful-payment inventory consumption

Important environment variables include:

```env
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=
MPESA_PASSKEY=
MPESA_CALLBACK_URL=
MPESA_CALLBACK_SECRET=
MPESA_ENV=sandbox
```

Real credentials must never be committed to Git.

## Payment security

Payment handling includes safeguards such as:

* Server-side order amount
* Callback validation
* Atomic database transactions
* Row locking
* Duplicate callback detection
* Unknown callback rejection
* Expected-amount verification
* Idempotent payment processing
* Inventory coordination
* Late-payment review handling

The payment flow is approximately:

```text
Order
  │
  ▼
STK Push
  │
  ▼
Customer authorizes payment
  │
  ▼
Safaricom
  │
  ▼
Callback
  │
  ▼
Validate callback
  │
  ▼
Lock payment/order
  │
  ▼
Verify amount/reference
  │
  ├──── Failure ───► Release reservation
  │
  ▼
Mark successful
  │
  ▼
Consume inventory
  │
  ▼
Confirm order
```

Local development should use M-Pesa sandbox credentials.

Production credentials must not be introduced until an actual production environment is being prepared.

---

# Returns and Refunds

The application contains customer and staff workflows for returns and refunds.

Refund states include:

```text
Requested
Approved
Processed
Rejected
```

Return workflows include states for requested, approved, completed/rejected operations as appropriate.

The system also supports return/refund history and item-level information.

Refund processing is designed to preserve financial history rather than rewriting the original order.

Partial refunds can move an order into:

```text
partially_refunded
```

while a complete refund can use:

```text
refunded
```

Provider-side reversal/refund operations should be verified before staff mark the corresponding application request as processed.

---

# Delivery Management

Delivery is managed as its own operational area.

The system supports:

* Delivery records
* Shop-managed delivery
* External delivery providers
* Delivery assignment
* Delivery status
* Delivery events
* Delivery attempts
* Parcel references
* Courier information
* Tracking numbers
* Tracking URLs
* Delivery destinations
* Customer order tracking

Delivery states can represent stages such as:

```text
Pending
Assigned
In Transit
Ready for Collection
Completed
```

depending on the delivery method and workflow.

---

# Invoices, Receipts and Credit Notes

The application generates commerce documents from order/payment information.

Supported documents include:

* Invoice
* Receipt
* Credit note

Documents use snapshots where appropriate so that historical documents do not unexpectedly change simply because the underlying catalog product is edited later.

Document numbering/prefixes can be controlled through store settings.

The application also supports printing/saving documents through the browser and relevant email workflows.

---

# Reviews

Customers can review products.

Review functionality includes:

* Product ratings
* Written reviews
* Average product rating
* Review count
* Customer ownership checks
* Verified-purchase restrictions

The verified-purchase policy prevents arbitrary users who have never purchased a product from being treated as verified buyers.

---

# CRM

The project includes customer-management functionality.

CRM features include customer information and customer notes that can assist staff with support and customer relationships.

This gives authorized staff additional operational context without placing CRM logic directly inside the storefront.

---

# Notifications

The application includes an internal notification system.

Notifications can be used for events such as:

* Order updates
* Payment updates
* Delivery events
* Account events
* Store/customer communication

Customers also have notification preferences where supported.

---

# Email

Email is delivered through Django's SMTP backend.

Example development configuration:

```env
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

Email credentials must remain outside source control.

External email delivery should be tested separately when preparing the production environment.

---

# SMS — Africa's Talking

The project includes **Africa's Talking** integration for SMS/communication.

Environment variables include:

```env
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=
```

The integration can be used by notification/business workflows for events such as order and customer updates.

---

# Abandoned Carts

The system tracks cart activity for abandoned-cart analysis.

Cart metadata can include information such as:

* Last activity
* Checkout started
* Conversion time

A cart can be considered abandoned when it:

* Contains items
* Has been inactive long enough
* Has not converted into an order

Authorized staff can inspect abandoned carts through store-management functionality.

---

# Analytics and Reports

The administration system contains reporting and analytics functionality.

Available reporting foundations include information around:

* Orders
* Revenue
* Payments
* Refunds
* Customers
* Products
* Inventory
* Abandoned carts
* Cost
* Profit
* Margin
* Store performance

Financial calculations should always use server-side/database values rather than values supplied by the browser.

---

# Store Settings

The application contains centralized store settings.

Configurable business information includes areas such as:

* Store name
* Support/contact information
* Business address
* Currency
* Tax configuration
* Order availability
* Minimum order amount
* Document prefixes

The project is primarily configured for:

```text
Currency: KES
Market: Kenya
Timezone: Africa/Nairobi
```

Django timezone configuration uses:

```python
TIME_ZONE = "Africa/Nairobi"
USE_TZ = True
```

---

# SEO

The storefront includes SEO foundations such as:

* `sitemap.xml`
* `robots.txt`
* Canonical/public URL support
* Product structured data
* Search-engine verification configuration

Example production configuration:

```env
SITE_URL=https://your-store-domain.com
GOOGLE_SITE_VERIFICATION=
```

Private customer, account and payment routes should not be treated as public search-engine content.

---

# Security

Security is treated as part of application architecture rather than only a deployment concern.

Implemented security measures include:

## CSRF protection

Django CSRF middleware is enabled.

State-changing actions use POST requests where appropriate.

## Authentication separation

Customer, store-staff and Django system-administrator authentication are separated.

## Role-based authorization

Management endpoints are protected by server-side permission checks.

## Login rate limiting

Sensitive authentication operations are rate limited.

## Server-authoritative pricing

Checkout does not trust prices submitted by the browser.

## Database locking

Important inventory and payment operations use row locking/transactions where appropriate.

## Payment idempotency

Duplicate M-Pesa callbacks should not produce duplicate successful payment processing.

## Guest capability tokens

Guest order access uses capability tokens with hashed token storage.

## Upload security

Uploaded images are validated before being accepted.

Supported image policy includes controlled formats such as:

```text
JPEG
PNG
WebP
```

Validation includes checks around:

* File size
* Declared content type
* Actual image format
* Image integrity
* Dimensions
* Pixel count

Upload policies are applied to surfaces such as:

* Customer avatars
* Product images
* Product galleries
* Brand logos
* Category images

## Browser security

The project configures security-related behavior including:

```python
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
```

Additional HTTPS/security settings apply when `DEBUG=False`.

## Custom error handling

Custom error pages exist for:

```text
400 Bad Request
403 Forbidden
404 Not Found
500 Server Error
```

Error pages are designed not to expose application tracebacks or sensitive settings when DEBUG is disabled.

Sensitive error responses are also configured to avoid unnecessary caching/indexing.

---

# Background Processing

The project uses **Celery** for asynchronous/background work.

Redis is used as the task broker.

Example configuration:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

Architecture:

```text
Django
  │
  ├──── Normal HTTP request
  │
  └──── Background task
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

Background processing is particularly useful for external communications and other work that should not unnecessarily delay a customer HTTP response.

---

# Technology Stack

## Backend

* Python
* Django 6
* Django ORM
* MySQL

## Authentication

* Django authentication
* Custom user model
* django-allauth
* Google authentication

## Frontend

* Django Templates
* HTML5
* CSS3
* JavaScript
* Bootstrap

## Payments

* Safaricom M-Pesa Daraja

## Background processing

* Celery
* Redis

## Communication

* SMTP email
* Africa's Talking

## Security/supporting packages

* django-ratelimit
* Pillow/image validation
* Django CSRF/security middleware

---

# Project Architecture

The system follows a modular architecture.

```text
                         ONLINE SHOP
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
     CUSTOMER              COMMERCE              MANAGEMENT
        │                     │                     │
   accounts               products               dashboard
   wishlist               categories              staff
   reviews                cart                    analytics
   profile                orders                  CRM
                          payments                inventory
                          delivery                refunds
                              │
                 ┌────────────┼────────────┐
                 │            │            │
                 ▼            ▼            ▼
               MySQL        Redis      External APIs
                              │            │
                              ▼            ├── M-Pesa
                            Celery          ├── SMTP
                                            └── Africa's Talking
```

---

# Django Applications

The project contains dedicated applications for major responsibilities, including:

```text
accounts/
cart/
categories/
core/
crm/
dashboard/
delivery/
inventory/
notifications/
orders/
payments/
products/
reviews/
wishlist/
```

## `accounts`

Authentication, customer accounts, staff authentication, staff roles and access control.

## `cart`

Shopping-cart state and cart operations.

## `categories`

Product-category functionality.

## `core`

Shared store functionality, global configuration, security helpers, store settings and common context.

## `crm`

Customer relationship/customer-note functionality.

## `dashboard`

Store-management interface, administration workflows, reports and analytics.

## `delivery`

Delivery records, providers, events, attempts and tracking.

## `inventory`

Inventory-related functionality and stock operations.

## `notifications`

Internal/customer notification functionality and communication support.

## `orders`

Checkout, orders, order items, guest order access and commerce documents.

## `payments`

M-Pesa payments, callbacks, refunds and return-related financial workflows.

## `products`

Catalog, products, brands, variants, images and product selection logic.

## `reviews`

Product reviews and ratings.

## `wishlist`

Customer wishlist functionality.

---

# Project Structure

A simplified project structure is:

```text
Onlineshop/
│
├── accounts/
├── cart/
├── categories/
├── core/
├── crm/
├── dashboard/
├── delivery/
├── inventory/
├── notifications/
├── orders/
├── payments/
├── products/
├── reviews/
├── wishlist/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── templates/
├── static/
├── media/
│
├── manage.py
├── requirements.txt
├── .env.example
├── DEVELOPMENT.md
└── README.md
```

Local `.env`, virtual environments, generated static files, caches, database dumps and temporary development/patch artifacts should not be committed to the public repository.

---

# Local Development Setup

## Requirements

Install/configure:

* Python 3
* pip
* MySQL
* Redis
* Git
* Python virtual environment

Optional external functionality requires credentials for:

* M-Pesa Daraja
* Google OAuth
* Africa's Talking
* SMTP email

---

## 1. Clone the repository

```bash
git clone <repository-url>
cd <project-directory>
```

---

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
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

---

# Environment Variables

Create a local:

```text
.env
```

in the project root.

Do not commit it.

Example:

```env
# Django
SECRET_KEY=replace-with-local-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
SITE_URL=http://localhost:8000

# MySQL
DB_NAME=onlinestore
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306

# M-Pesa — local/sandbox only
MPESA_CONSUMER_KEY=
MPESA_CONSUMER_SECRET=
MPESA_SHORTCODE=
MPESA_PASSKEY=
MPESA_CALLBACK_URL=
MPESA_CALLBACK_SECRET=
MPESA_ENV=sandbox

# Redis / Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Africa's Talking
AFRICASTALKING_USERNAME=
AFRICASTALKING_API_KEY=

# SMTP
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Variable names should match the actual local configuration used by `config/settings.py`.

Never place real credentials in this README.

---

# Database Setup

The project uses **MySQL**.

Example local database:

```sql
CREATE DATABASE onlinestore
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

Database settings are read from environment variables.

Typical local configuration:

```env
DB_NAME=onlinestore
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
```

Apply migrations:

```powershell
python manage.py migrate
```

Check migration state:

```powershell
python manage.py showmigrations
```

Check whether model changes are missing migrations:

```powershell
python manage.py makemigrations --check --dry-run
```

---

# Store Roles Setup

After migrations, initialize the supported store-management roles using the project's management command:

```powershell
python manage.py setup_store_roles
```

Store staff should then be assigned only the roles required for their responsibilities.

---

# Create System Administrator

Create a Django superuser:

```powershell
python manage.py createsuperuser
```

The system administrator uses:

```text
/admin/
```

This account is different from ordinary store-management staff.

---

# Run the Development Server

```powershell
python manage.py runserver
```

Default local URL:

```text
http://127.0.0.1:8000/
```

Localhost is currently treated as the project's staging/testing environment.

---

# Redis and Celery

Redis must be running for Redis-dependent background functionality.

Test Redis:

```bash
redis-cli ping
```

Expected:

```text
PONG
```

On Windows, a local Celery worker can be started with:

```powershell
celery -A config worker --loglevel=info --pool=solo
```

On Linux:

```bash
celery -A config worker --loglevel=info
```

---

# Static Files

Source static assets are stored under:

```text
static/
```

Production collection uses:

```powershell
python manage.py collectstatic
```

Collected `staticfiles/` output should not normally be committed to Git.

---

# Media Files

Uploaded media uses Django's configured media storage.

Typical local configuration:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Production media storage must be configured as part of deployment planning.

---

# Testing

The project has an extensive automated regression suite covering the major commerce and administration workflows.

Run all tests with:

```powershell
python manage.py test -v 1
```

Check Django configuration:

```powershell
python manage.py check
```

Check for missing migrations:

```powershell
python manage.py makemigrations --check --dry-run
```

Important automated test areas include:

* Authentication
* Authentication separation
* Staff management
* Store roles and permissions
* Products
* Upload security
* Cart
* Wishlist
* Checkout
* Guest checkout
* Inventory
* Orders
* Delivery
* M-Pesa payments
* Callback behavior
* Returns
* Refunds
* Partial refunds
* Invoices
* Receipts
* Credit notes
* CRM
* Abandoned carts
* Reports
* Analytics
* Store settings
* DEBUG=False error handling
* State-changing request protection
* Money formatting

A green automated suite is required before a development phase is considered complete.

---

# Development vs Production

## Local development / staging

Current development uses localhost.

Typical architecture:

```text
Django Development Server
          │
    ┌─────┼─────┐
    │     │     │
    ▼     ▼     ▼
 MySQL  Redis  Sandbox APIs
          │
          ▼
        Celery
```

Development should use:

```env
DEBUG=True
MPESA_ENV=sandbox
```

Production credentials should not be used simply to make localhost testing easier.

---

# Production

Production does not mean changing one setting and running the development server publicly.

A production architecture should use infrastructure similar to:

```text
Internet
   │
   ▼
HTTPS
   │
   ▼
Reverse Proxy / Web Server
   │
   ▼
Production Django Server
   │
   ├────────► MySQL
   │
   ├────────► Redis
   │             │
   │             ▼
   │           Celery
   │
   ├────────► M-Pesa
   ├────────► SMTP
   └────────► SMS Provider
```

Production requires its own:

* Domain
* HTTPS certificate
* Secrets
* Database credentials
* M-Pesa production credentials
* Callback URL
* Redis configuration
* Celery workers
* Email configuration
* SMS configuration
* Static/media strategy
* Logging
* Monitoring
* Backup strategy

---

# Production Checklist

## Already completed locally

The application has local implementations/foundations for:

* [x] Customer authentication
* [x] Custom user model
* [x] Email verification
* [x] Password reset
* [x] Customer/staff/admin authentication separation
* [x] Store staff roles
* [x] Role-based access control
* [x] Product management
* [x] Categories
* [x] Brands
* [x] Product gallery
* [x] Product variants/data model
* [x] Inventory tracking
* [x] Inventory reservation
* [x] Inventory locking
* [x] Cart
* [x] Wishlist
* [x] Server-side checkout pricing
* [x] Coupons
* [x] Tax configuration
* [x] Minimum-order configuration
* [x] Guest checkout
* [x] Orders
* [x] M-Pesa sandbox integration
* [x] Payment callback processing
* [x] Payment idempotency safeguards
* [x] Delivery management
* [x] Order tracking
* [x] Returns
* [x] Refund requests
* [x] Partial-refund status handling
* [x] Invoices
* [x] Receipts
* [x] Credit notes
* [x] Reviews
* [x] Verified-purchase review restrictions
* [x] CRM foundations
* [x] Notifications
* [x] Abandoned-cart tracking
* [x] Analytics/reporting
* [x] Store settings
* [x] Upload security
* [x] POST-only protection for important state changes
* [x] Login rate limiting
* [x] Custom DEBUG=False error pages
* [x] SEO sitemap/robots foundations
* [x] Automated regression testing

## Must be configured/verified before going live

* [ ] Provision production server/infrastructure
* [ ] Configure production domain
* [ ] Configure HTTPS
* [ ] Set `DEBUG=False`
* [ ] Generate/use a production `SECRET_KEY`
* [ ] Configure production `ALLOWED_HOSTS`
* [ ] Configure CSRF trusted origins where required
* [ ] Configure production MySQL
* [ ] Configure production Redis
* [ ] Configure production Celery workers
* [ ] Configure production M-Pesa credentials
* [ ] Configure public HTTPS M-Pesa callback URL
* [ ] Verify M-Pesa callback security in deployed environment
* [ ] Configure Google OAuth production redirect URIs
* [ ] Verify Google OAuth end-to-end
* [ ] Configure production SMTP
* [ ] Configure production Africa's Talking credentials
* [ ] Configure static-file serving
* [ ] Configure production media storage
* [ ] Configure reverse-proxy/access logging
* [ ] Prevent sensitive capability tokens from being unnecessarily logged
* [ ] Configure application logging
* [ ] Configure monitoring
* [ ] Establish database backups
* [ ] Perform an actual backup restore test
* [ ] Run `python manage.py check --deploy`
* [ ] Run migrations
* [ ] Run `collectstatic`
* [ ] Run complete automated test suite
* [ ] Perform browser/mobile QA
* [ ] Test customer registration
* [ ] Test customer login/logout
* [ ] Test staff permissions role by role
* [ ] Test system-administrator separation
* [ ] Test complete checkout
* [ ] Test real production payment flow before public launch
* [ ] Test successful/failed/cancelled payment handling
* [ ] Test delivery workflow
* [ ] Test returns/refunds
* [ ] Test email/SMS delivery
* [ ] Test error pages with `DEBUG=False`
* [ ] Verify `.env` and secrets are not tracked by Git
* [ ] Verify SQL/database dumps are not tracked
* [ ] Document rollback/recovery procedure

---

# Secret Management

Sensitive information includes:

```text
SECRET_KEY
DB_PASSWORD
MPESA_CONSUMER_KEY
MPESA_CONSUMER_SECRET
MPESA_PASSKEY
MPESA_CALLBACK_SECRET
GOOGLE_CLIENT_SECRET
AFRICASTALKING_API_KEY
EMAIL_HOST_PASSWORD
```

Never commit these values.

Useful Git check:

```powershell
git ls-files |
    Select-String -Pattern '\.env$|\.sql$|db\.sqlite3$'
```

A release repository should not expose secrets or development database dumps.

---

# `.gitignore`

At minimum, the repository should ignore:

```gitignore
# Python
__pycache__/
*.py[cod]

# Virtual environments
venv/
.venv/
env/

# Environment/secrets
.env
.env.*

# Local databases/dumps
db.sqlite3
*.sql

# Django generated files
staticfiles/

# Logs
*.log

# IDE
.vscode/
.idea/

# Operating system
.DS_Store
Thumbs.db
```

Project-specific temporary patch scripts and backup artifacts should also remain outside the final repository.

---

# Development Workflow

A safe development workflow is:

```text
Inspect
   ↓
Make smallest change
   ↓
python manage.py check
   ↓
Migration dry-run
   ↓
Targeted tests
   ↓
Related application tests
   ↓
Full regression suite
   ↓
Git review
   ↓
Commit
```

Commands:

```powershell
python manage.py check

python manage.py makemigrations --check --dry-run

python manage.py test <app-or-test> -v 2

python manage.py test -v 1

git status --short
```

Do not weaken payment, authorization, inventory or security behavior merely to make an outdated test pass.

If application behavior intentionally changes, update the stale test only after confirming the new behavior is correct.

---

# Important Financial Rules

Financial data should remain precise internally.

Do not use binary floating-point values for authoritative money calculations.

Do not rewrite historical order/payment records simply because:

* A product price changes
* Display formatting changes
* A product is renamed
* A sale ends

Order documents and payment history are business records.

The application therefore separates current catalog state from historical order/payment information where appropriate.

---

# Important Inventory Rules

Inventory must not be reduced merely because a customer opened a product page.

Stock transitions should correspond to real commerce events.

The application uses concepts such as:

```text
AVAILABLE
   ↓
RESERVED
   │
   ├──── Failed/cancelled ───► RELEASED
   │
   └──── Paid ───────────────► CONSUMED
```

Concurrency-sensitive operations should continue to use database transactions/locking.

---

# Important Payment Rules

Never trust:

* Browser-submitted totals
* Browser-submitted product prices
* A callback merely because it reached the server
* Duplicate callbacks as separate payments

Always verify payment state against authoritative server/database information.

Payment and inventory code is considered high-risk application code and should receive targeted tests after any modification.

---

# Remaining Work

The application is feature-rich, but several items remain before it should be described as fully production-ready.

Current remaining work includes:

* Final codebase cleanup
* Removal of obsolete development/patch artifacts
* Further dead-code/duplicate-code review
* Final JavaScript/browser QA
* Mobile/responsive QA
* Accessibility review
* Final dashboard permission/privacy review
* Last-active Store Owner protection
* Review-moderation polish
* Promotions/coupon-management UI polish
* Google OAuth end-to-end verification
* External notification-provider outage/retry testing
* Database backup and restore verification
* Production infrastructure
* Production logging and monitoring
* Deployment documentation
* Final secrets/repository audit
* Final go-live regression gate

Possible future product expansion includes:

* Additional payment providers
* REST API
* Mobile application
* Advanced external integrations
* Cloud object storage
* Automated deployment pipeline
* Advanced observability/error monitoring
* Additional marketing automation
* Additional courier integrations
* Additional accounting/ERP integrations

These are enhancements rather than substitutes for completing the current production-hardening work.

---

# Final Go-Live Gate

The application should only be declared ready for public production when the final audit confirms:

```text
Critical security issues          0
High security issues              0
Critical functional bugs         0

Authentication                   VERIFIED
Admin permissions                VERIFIED
Order flow                       VERIFIED
Payment flow                     VERIFIED
Database operations              VERIFIED
Upload security                  VERIFIED
Error handling                   VERIFIED
Secrets separation               VERIFIED
Backup + restore                 VERIFIED
Production configuration         PREPARED
Deployment procedure             DOCUMENTED
```

Passing automated tests on localhost is necessary, but it is not by itself proof that external production infrastructure has been configured correctly.

---

# License

Choose the license appropriate for the way the application will be distributed.

If the system is being sold as proprietary commercial software, do not add an open-source license unless you actually intend to grant those rights.

A proprietary notice can be used instead where appropriate.

---

# Author

**Moody Austine**

Django / Information Systems Developer

GitHub: `Austinemoodydev`

---

# Final Notes

Online Shop has evolved from a basic Django storefront into a broader commerce-management platform.

Its current architecture covers:

```text
CUSTOMER EXPERIENCE
        +
PRODUCT CATALOG
        +
CART & CHECKOUT
        +
INVENTORY
        +
ORDERS
        +
M-PESA PAYMENTS
        +
DELIVERY
        +
RETURNS & REFUNDS
        +
DOCUMENTS
        +
CRM
        +
STAFF MANAGEMENT
        +
ROLE-BASED ACCESS
        +
ANALYTICS
        +
NOTIFICATIONS
        +
SECURITY
```

The current development priority is not to keep adding random features. The priority is to finish codebase cleanup, verify backup/recovery, complete external-service and browser testing, prepare production configuration, and pass the final go-live gate.

Production secrets must remain separate from source code, and localhost must continue using development/sandbox configuration until a real production environment is deliberately provisioned.

<!-- HEADER BANNER -->
<p align="center">
  <img src="static/images/branding/provia-banner.png" width="450" alt="Provia Banner - Book • Connect • Trust" style="border-radius: 20px;" />
</p>

<div align="center">

[![Django](https://img.shields.io/badge/Django-5.0+-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Daphne%20%2F%20Channels-0284c7?style=for-the-badge&logo=socketdotio&logoColor=white)]()
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.0+-38BDF8?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Status](https://img.shields.io/badge/Status-Active_Development-10B981?style=for-the-badge)]()

</div>

---

## 📌 Overview

**Provia** is a production-minded, full-stack on-demand service marketplace designed to connect customers with verified service providers across multiple categories (home repairs, cleaning, electrical, plumbing, and professional consulting). 

Built with **Django**, **Daphne/ASGI**, **Django Channels**, **MySQL**, and **Tailwind CSS**, Provia provides a seamless booking lifecycle, real-time customer-provider messaging, automated scheduling, and multi-role dashboards.

---

## ✨ Key Features

### 🔐 1. Multi-Role Authentication & Security
- **Custom User Roles:** Dedicated capabilities for **Customers**, **Providers**, and **Administrators**.
- **Email Verification & Reset:** Secure registration flows with email verification tokens and password reset confirmation.
- **Role-Based Access Control:** Custom decorators (`@customer_required`, `@provider_required`) guarding view endpoints.

### 🛠️ 2. Service Catalog & Discovery
- **Categorized Services:** Browse services by category, pricing model (flat rate vs. hourly), and availability.
- **Geospatial & Location Search:** Filter services by coverage location and active provider regions.
- **Detailed Provider Profiles:** View provider bios, ratings, review history, and service portfolios.

### 📅 3. Stateful Booking Engine
- **Transactional State Machine:** Manages booking transitions through defined states:  
  `Pending` ➔ `Confirmed` ➔ `Completed` / `Cancelled`
- **Slot Generation & Availability:** Dynamic time slot availability matching provider working hours.
- **Price Calculation:** Dynamic total calculation considering service duration, rates, and booking options.

### 💬 4. Real-Time Customer-Provider Chat (WebSockets)
- **Live ASGI Messaging:** Powered by **Daphne** and **Django Channels** over persistent WebSocket connections.
- **Conversation Tracking:** One-on-one message history tied directly to customer-provider booking contexts.
- **Unread Counters & Timestamps:** Real-time updates without page refreshes.

### 🔔 5. Notifications & Review System
- **In-App Notification Dispatcher:** Real-time alert feed for booking requests, status changes, and message notifications.
- **Review Ratings:** Post-service rating and feedback workflow updating aggregate provider score.

### 🎨 6. Responsive UI & Components
- **Tailwind CSS Design System:** Modern, accessible visual design with custom UI components (modals, breadcrumbs, status badges, navbar, pagination).
- **Responsive Dashboards:** Tailored dashboard interfaces for both Customers and Providers.

---

## 🏗️ System Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Client Browser / Frontend                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (HTTP & WebSockets)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Daphne ASGI Server                             │
├───────────────────────────────────┬────────────────────────────────────┤
│  Standard HTTP Requests (WSGI)    │  Real-Time WebSockets (ASGI)       │
│  - Authentication & Dashboards    │  - Chat Consumer (chat.consumers)  │
│  - Booking Engine & Services      │  - Channels Consumer Routing       │
└─────────────────┬─────────────────┴─────────────────┬──────────────────┘
                  │                                   │
                  ▼                                   ▼
┌──────────────────────────────────┐┌────────────────────────────────────┐
│      Django Service Layer        ││         Django Channels            │
│  (accounts, bookings, services,  ││         (In-Memory / Redis)         │
│   payments, notifications)       │└─────────────────┬──────────────────┘
└─────────────────┬────────────────┘                  │
                  │                                   │
                  └─────────────────┬─────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           MySQL Database Engine                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```text
Provia/
├── config/                  # Django project configuration (settings, urls, asgi, wsgi)
├── accounts/                # User authentication, registration, profiles, email verification
├── bookings/                # Booking engine, state transitions, slot booking
├── services/                # Service catalog, categories, location availability
├── providers/               # Provider profiles, schedules, ratings
├── chat/                    # Real-time WebSocket chat consumers, routing, history
├── notifications/           # In-app notification dispatcher & email utilities
├── payments/                # Checkout workflows & payment records
├── reviews/                 # Post-service reviews & ratings
├── dashboard/               # Customer & Provider portal dashboards
├── analytics/               # System metrics & booking analytics
├── api/                     # Internal REST/JSON endpoints
├── static/                  # Compiled Tailwind output (css/output.css) & JavaScript (js/chat.js)
├── templates/               # Global templates, layout components, navigation partials
├── src/                     # Tailwind CSS source files (input.css)
├── manage.py                # Django CLI entrypoint
├── package.json             # Tailwind CSS & Node build tools
└── tailwind.config.js       # Tailwind CSS design system configuration
```

---

## 🛠️ Tech Stack & Dependencies

| Layer | Technology | Usage |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core application logic |
| **Framework** | Django 5.0+ | Web framework, ORM, Admin, Authentication |
| **ASGI / Realtime** | Daphne & Django Channels | Async WebSocket handling for live chat |
| **Database** | MySQL 8.0+ | Relational database storage |
| **Frontend** | Tailwind CSS & JavaScript (ES6) | Responsive styling & client DOM/WebSocket handling |
| **Email** | SMTP / Django Email Backend | Verification and transaction emails |
| **Build Tools** | Node.js & npm | Tailwind CSS compiler |

---

## 🚀 Getting Started

### Prerequisites

Ensure you have the following installed on your system:
- **Python 3.10+**
- **MySQL 8.0+**
- **Node.js (v18+) & npm**
- **Git**

---

### 📥 1. Clone the Repository

```bash
git clone https://github.com/your-username/Provia.git
cd Provia
```

---

### 🐍 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv env

# Activate virtual environment
# Windows (PowerShell):
.\env\Scripts\Activate.ps1
# Linux/macOS:
source env/bin/activate
```

---

### 📦 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### ⚙️ 4. Configure Environment Variables

Create a `.env` file in the project root directory (refer to `.env.example`):

```ini
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database Configuration
DB_NAME=provia_db
DB_USER=provia_user
DB_PASSWORD=your_db_password
DB_HOST=127.0.0.1
DB_PORT=3306

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Provia <your-email@example.com>
```

---

### 🗄️ 5. Run Database Migrations

Ensure your MySQL service is running and the database specified in `DB_NAME` exists, then run:

```bash
python manage.py migrate
```

---

### 🎨 6. Build Tailwind CSS Assets

```bash
# Install Node dependencies
npm install

# Build CSS for production or run watch mode for development
npm run build
# Or for watch mode:
npm run dev
```

---

### 👤 7. Create Superuser / Dev Users

```bash
# Create admin superuser
python manage.py createsuperuser

# (Optional) Seed development users
python manage.py setup_dev_users
```

---

### 🖥️ 8. Run the Development Server (Daphne / ASGI)

To support WebSockets for live chat alongside standard HTTP views, run using Daphne:

```bash
python manage.py runserver
```
*(Or invoke Daphne directly for production/ASGI testing)*:
```bash
daphne -b 127.0.0.1 -p 8000 config.asgi:application
```

Visit **http://127.0.0.1:8000/** in your browser.

---

## 🧪 Testing

Run the automated Django unit test suite across all apps:

```bash
python manage.py test
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.

# Fake News Verification App

A simple Django web application to check if news queries are True or False.

## Features

- User sign-up and login
- Submit news queries to verify their accuracy
- Clear display of results (True or False)

## Requirements

- Django
- MySQL
- Python 3.8+

## Quick Setup

### Step 1: Create Database

```sql
CREATE DATABASE fakenews_db;
```

### Step 2: Create Database User

```sql
CREATE USER 'fakenews_user' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON fakenews_db.* TO 'fakenews_user';
FLUSH PRIVILEGES;
```

*Replace `fakenews_db`, `fakenews_user`, and `your_password` as needed.*

### Step 3: Configure Django Settings

Edit the file `user_query_app/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "fakenews_db",
        "USER": "fakenews_user",
        "PASSWORD": "your_password",
    }
}
```

### Step 4: Install Dependencies

```bash
pip install django mysqlclient
```

### Step 5: Set Up Database

```bash
python manage.py migrate
```

## Running the Application

Start the Django development server:

```bash
python manage.py runserver
```

Access the application in your browser at: [http://localhost:8000](http://localhost:8000)

## How to Use

- **Sign up** using a username, email, and password
- **Log in** with your credentials
- **Submit a query** to check if it's True or False

## Note

Currently, this application provides basic results. A more advanced, machine learning-driven backend is under development.


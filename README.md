# Traffic Violation System

## Description
This project is a web application built with Django that manages traffic violations. It allows users to report violations, view records, and manage user accounts.

## Installation
To set up the project, follow these steps:

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   - Ensure you have MySQL installed and running.
   - Create a database named `capstone` and update the database settings in `settings.py` if necessary.

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Start the development server:

5. Start the development server:
   ```bash
   python manage.py runserver
   ```

## Usage
- Access the application at `http://127.0.0.1:8000/`.
- Use the admin interface to manage users and violations.

## License
This project is licensed under the MIT License.

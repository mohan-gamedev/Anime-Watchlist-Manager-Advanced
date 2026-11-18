# Anime Watchlist Manager Pro

A responsive local web application using HTML, CSS, JavaScript, Python/Flask and MySQL.

## Features
- Dashboard statistics for total titles, watching, completed and favourites
- Add, view, edit and delete anime records
- Episode progress increase/decrease controls
- Status, rating, favourites and notes
- Search by title or genre; filter by status; sort by update, title, rating or progress
- Poster upload (PNG/JPG/JPEG/WEBP/GIF, 5 MB request limit) or HTTP(S) image URL
- Responsive dark interface with animated visual elements
- Parameterised SQL and local health check at `/health`

## Windows + XAMPP setup
1. Extract this folder.
2. Start **MySQL** in XAMPP. Apache is not needed because Flask serves the application.
3. Open `http://localhost/phpmyadmin`, select **Import**, and import `schema.sql`.
4. Open a terminal in this project folder.
5. Run `python -m venv .venv`
6. Activate it: `.venv\\Scripts\\activate`
7. Install: `pip install -r requirements.txt`
8. Copy `.env.example` to `.env`; set the database username/password to match XAMPP.
9. Run `python app.py`
10. Open `http://127.0.0.1:5000`

## Linux/macOS
Install Python 3 and MySQL/MariaDB, import `schema.sql`, then run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

## Configuration
`.env` values: `SECRET_KEY`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `PORT`.

## Important notes
- This is a single-user local training project; it does not include accounts or login.
- The app binds to `127.0.0.1` and uses Flask's development server. Do not expose it publicly.
- Set a strong random `SECRET_KEY`; keep `.env` private.
- Upload checks include extension and request size. Production systems should additionally inspect file contents and consider malware scanning.
- Before public deployment add authentication, CSRF protection, HTTPS, secure cookie settings, a least-privilege DB account, backups and a production WSGI server.

## Troubleshooting
- **Database unavailable:** confirm XAMPP MySQL is running and `.env` credentials/port are correct.
- **Unknown database:** import `schema.sql` through phpMyAdmin.
- **Module not found:** activate `.venv` and install `requirements.txt`.
- **Port in use:** set a different `PORT` in `.env` and restart.

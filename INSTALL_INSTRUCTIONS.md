# Installation Instructions

Complete step-by-step guide to install and deploy the Equipment Management System locally and to production.

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Database Setup](#database-setup)
3. [NFC Hardware Setup](#nfc-hardware-setup)
4. [Running Locally](#running-locally)
5. [Production Deployment](#production-deployment)
6. [Docker Deployment](#docker-deployment)
7. [Troubleshooting](#troubleshooting)

---

## Local Development Setup

### Prerequisites

Before starting, ensure you have:

- **Python 3.9 or higher** - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **PostgreSQL** (optional, SQLite works for development) - [Download PostgreSQL](https://www.postgresql.org/download/)
- **Text Editor/IDE** - VS Code, PyCharm, or similar
- **NFC Reader** (optional, for NFC features) - USB NFC Reader or smartphone with NFC

### Step 1: Clone the Repository

Open terminal/command prompt and run:

```bash
# Navigate to where you want to store the project
cd ~/projects
# Or on Windows: cd C:\Users\YourUsername\projects

# Clone the repository
git clone https://github.com/whcbusi/equipment-management-system.git
cd equipment-management-system
```

### Step 2: Create Virtual Environment

A virtual environment keeps Python packages isolated for this project.

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (Command Prompt):**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Windows (PowerShell):**
```bash
python -m venv venv
venv\Scripts\Activate.ps1
```

✅ **Success indicator:** Your terminal prompt should show `(venv)` at the beginning.

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- SQLAlchemy (database ORM)
- Flask-JWT-Extended (authentication)
- PostgreSQL driver
- QR code library
- NFC library (nfcpy)
- And other dependencies

### Step 4: Set Up Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` file in your favorite text editor. For **local development**, you can keep these defaults:

```ini
FLASK_ENV=development
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET=dev-jwt-secret-change-in-production
DATABASE_URL=sqlite:///equipment.db
```

For **production**, change:
- `FLASK_ENV=production`
- `DEBUG=False`
- `SECRET_KEY=<strong-random-string>`
- `JWT_SECRET=<strong-random-string>`
- `DATABASE_URL=postgresql://user:password@host:5432/db_name`

---

## Database Setup

### Option A: SQLite (Development - Easiest)

SQLite is built into Python, so it works out-of-the-box.

```bash
# Initialize database
python init_db.py
```

You should see:
```
✓ Database initialized!
✓ Admin user: admin@example.com / admin123
```

A new file `equipment.db` will be created in your project root.

### Option B: PostgreSQL (Production - Recommended)

#### Install PostgreSQL

**On Mac (using Homebrew):**
```bash
brew install postgresql
brew services start postgresql
```

**On Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

**On Linux (Ubuntu/Debian):**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo service postgresql start
```

#### Create Database

**On Mac/Linux:**
```bash
# Connect to PostgreSQL
psql postgres

# In PostgreSQL shell, run:
CREATE DATABASE equipment_db;
CREATE USER equipment_user WITH PASSWORD 'your_secure_password';
ALTER ROLE equipment_user SET client_encoding TO 'utf8';
ALTER ROLE equipment_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE equipment_user SET default_transaction_deferrable TO on;
ALTER ROLE equipment_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE equipment_db TO equipment_user;
\q
```

**On Windows (using pgAdmin):**
1. Open pgAdmin
2. Right-click "Databases" → Create → Database
3. Name: `equipment_db`
4. Right-click "Roles/Login Roles" → Create
5. Name: `equipment_user`, Password: `your_secure_password`
6. Grant privileges to the user

#### Update .env

```ini
DATABASE_URL=postgresql://equipment_user:your_secure_password@localhost:5432/equipment_db
```

#### Initialize Database

```bash
python init_db.py
```

---

## NFC Hardware Setup

### Option A: USB NFC Reader (ACR122U)

**Hardware Cost:** $30-50  
**Best For:** Desktop kiosk, fixed terminal

#### Setup

1. **Purchase USB NFC Reader** - ACR122U from Amazon or electronics store

2. **Install drivers:**

**On Windows:**
- Download from [ACS Official Website](https://www.acs.com.hk/en/driver/3/acr122u-usb-nfc-reader)
- Run installer
- Restart computer

**On Mac:**
```bash
brew install libusb
```

**On Linux:**
```bash
sudo apt-get install libusb-1.0-0 libusb-1.0-0-dev
```

3. **Test connection:**

```bash
# Plug in USB NFC reader
python -c "import nfc.clf; clf = nfc.clf.ContactlessFrontend('usb'); print('✓ NFC reader connected!')"
```

### Option B: Mobile Phone NFC (Android/iOS)

**Hardware Cost:** Free (if you have a phone with NFC)  
**Best For:** Mobile scanning, flexible deployment

#### Requirements

- Android 11+ or iOS 15+
- NFC capability (most modern phones have it)
- Modern browser (Chrome 89+, Edge 89+, Safari 15+)
- HTTPS connection (required for Web NFC API)

#### Enable Web NFC

**On Android:**
1. Open Chrome
2. Go to `chrome://flags`
3. Search for "NFC"
4. Enable "NFC experimental features"
5. Restart Chrome

**On iOS:**
- iOS 15+ automatically enables NFC in Safari
- No flags needed

#### Test

```bash
# After deploying with HTTPS, visit:
https://your-domain.com/auth/nfc-login
```

### Option C: Raspberry Pi + NFC Hat (Advanced)

**Hardware Cost:** $50-100  
**Best For:** 24/7 kiosk, industrial setup

#### Hardware

- Raspberry Pi 4 (4GB RAM minimum)
- NFC HAT or USB NFC reader
- Power supply
- SD Card (32GB minimum)

#### Setup

1. **Install Raspberry Pi OS**

2. **Connect to Raspberry Pi:**

```bash
ssh pi@raspberry-pi-ip
```

3. **Install dependencies:**

```bash
sudo apt-get update
sudo apt-get install python3-pip python3-venv libusb-1.0-0 libusb-1.0-0-dev
```

4. **Clone and install application:**

```bash
git clone https://github.com/whcbusi/equipment-management-system.git
cd equipment-management-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py
```

5. **Run as service** (optional - for auto-start):

Create `/etc/systemd/system/equipment-mgmt.service`:

```ini
[Unit]
Description=Equipment Management System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/equipment-management-system
ExecStart=/home/pi/equipment-management-system/venv/bin/python run.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl enable equipment-mgmt
sudo systemctl start equipment-mgmt
```

---

## Running Locally

### Start the Application

Make sure your virtual environment is activated (you see `(venv)` in terminal):

```bash
python run.py
```

You should see:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Access the Application

Open your browser and go to:

```
http://localhost:5000
```

### Default Login Credentials

```
Email: admin@example.com
Password: admin123
```

### Create Additional Users

1. Login with admin account
2. Go to **Admin → Register User**
3. Fill in details
4. Click Register

### Link NFC Tags (Optional)

1. Login as user
2. Go to **Profile → Link NFC Tag**
3. Tap NFC reader or enter tag ID manually
4. Click "Link Tag"

### Create Equipment

1. Login as admin
2. Go to **Admin → Equipment** (or click + Equipment)
3. Fill in details:
   - Equipment Type
   - Name
   - Serial Number
   - Location
4. Click Add

5. Assign NFC tag to equipment:
   - Go to **Admin → Assign NFC Tags**
   - Select equipment
   - Tap NFC tag or enter ID
   - Click Assign

### Test Borrowing

1. Login as regular user
2. Go to **NFC Scanner**
3. Tap equipment NFC tag
4. Confirm borrow

### Verify Everything Works

Check that:
- ✅ Login works with email/password
- ✅ NFC login works (if hardware connected)
- ✅ Can view equipment list
- ✅ Can borrow/return equipment
- ✅ Admin panel accessible to admins only
- ✅ Reports show correct data

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Change `SECRET_KEY` and `JWT_SECRET` to random strings
- [ ] Set `FLASK_ENV=production`
- [ ] Set `DEBUG=False`
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set up HTTPS/SSL certificate
- [ ] Configure firewall/security groups
- [ ] Set up database backups
- [ ] Configure email for notifications (optional)

### Option A: Heroku Deployment (Easiest)

**Cost:** Free tier available, $7+/month for production  
**Time:** 10-15 minutes

#### Prerequisites

1. Create [Heroku account](https://www.heroku.com/signup)
2. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)

#### Deploy

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL database
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set DEBUG=False
heroku config:set SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
heroku config:set JWT_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')

# Deploy
git push heroku main

# Initialize database
heroku run python init_db.py

# View logs
heroku logs --tail
```

Your app is now live at: `https://your-app-name.herokuapp.com`

### Option B: AWS Elastic Beanstalk

**Cost:** $10-50/month  
**Time:** 20-30 minutes

#### Prerequisites

1. Create [AWS account](https://aws.amazon.com/)
2. Install [AWS CLI](https://aws.amazon.com/cli/)
3. Install [EB CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html)

#### Deploy

```bash
# Initialize Elastic Beanstalk app
eb init -p python-3.9 equipment-management-system --region us-east-1

# Create environment
eb create equipment-mgmt-prod

# Set environment variables
eb setenv FLASK_ENV=production DEBUG=False

# Initialize database
eb ssh
python init_db.py
exit

# Deploy updates
git push
eb deploy

# Monitor
eb open
```

### Option C: DigitalOcean App Platform

**Cost:** $12/month (includes database)  
**Time:** 15-20 minutes

#### Prerequisites

1. Create [DigitalOcean account](https://www.digitalocean.com)
2. Have your GitHub repo connected

#### Deploy via UI

1. Go to DigitalOcean Dashboard
2. Click "Create" → "Apps"
3. Connect GitHub repository
4. Select `equipment-management-system`
5. Set build command: `pip install -r requirements.txt`
6. Set run command: `gunicorn --bind 0.0.0.0:8080 run:app`
7. Add PostgreSQL database
8. Set environment variables
9. Click "Deploy"

### Option D: Self-Hosted (VPS)

**Cost:** $5-20/month  
**Time:** 30-45 minutes  
**Providers:** DigitalOcean, Linode, AWS EC2, etc.

#### Setup on Ubuntu 20.04 VPS

```bash
# Connect to VPS
ssh root@your_vps_ip

# Update system
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y python3-pip python3-venv postgresql postgresql-contrib nginx git

# Clone repository
cd /home
git clone https://github.com/whcbusi/equipment-management-system.git
cd equipment-management-system

# Setup Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup PostgreSQL
sudo -u postgres psql
CREATE DATABASE equipment_db;
CREATE USER equipment_user WITH PASSWORD 'secure_password';
GRANT ALL ON DATABASE equipment_db TO equipment_user;
\q

# Initialize app
python init_db.py

# Setup Nginx reverse proxy
# Create /etc/nginx/sites-available/equipment-mgmt:
```

Create `/etc/nginx/sites-available/equipment-mgmt`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Continue setup:

```bash
# Enable site
ln -s /etc/nginx/sites-available/equipment-mgmt /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Setup SSL with Let's Encrypt
apt-get install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com -d www.your-domain.com

# Run app with Gunicorn
pip install gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 run:app &

# (Or setup as systemd service)
```

---

## Docker Deployment

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed

### Quick Start

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop containers
docker-compose down
```

Access at: `http://localhost:5000`

### Customization

Edit `docker-compose.yml`:

```yaml
version: '3.8'

services:
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: equipment_db
      POSTGRES_USER: equipment_user
      POSTGRES_PASSWORD: your_secure_password  # CHANGE THIS
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  app:
    build: .
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://equipment_user:your_secure_password@db:5432/equipment_db
      SECRET_KEY: your-secret-key  # CHANGE THIS
      JWT_SECRET: your-jwt-secret  # CHANGE THIS
    ports:
      - "5000:5000"
    depends_on:
      - db
    volumes:
      - ./app:/app/app

volumes:
  postgres_data:
```

### Deploy to Production with Docker

**On AWS using ECS:**

```bash
# Build image
docker build -t equipment-mgmt:latest .

# Tag for ECR
docker tag equipment-mgmt:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/equipment-mgmt:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/equipment-mgmt:latest
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'flask'"

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### "database is locked"

**Solution:** Only one instance of SQLite can write at a time. For production, use PostgreSQL.

```bash
# For development, close other instances and restart:
python run.py
```

### "Port 5000 already in use"

**Solution:** Use different port:
```bash
python run.py --port 5001
```

Or kill existing process:

**Mac/Linux:**
```bash
lsof -i :5000
kill -9 <PID>
```

**Windows:**
```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### NFC reader not detected

**Solution:**
```bash
# Check USB connection
python -c "import nfc.clf; print(nfc.clf.list_devices())"

# If empty, try:
# - Reinstall USB drivers
# - Use different USB cable
# - Try different USB port
# - Check USB permissions (Linux)
```

### PostgreSQL connection error

**Solution:**
```bash
# Check if PostgreSQL is running
# Mac: brew services list
# Linux: sudo service postgresql status
# Windows: Check Services → PostgreSQL

# Verify credentials in .env
# Test connection:
psql postgresql://user:password@localhost:5432/equipment_db
```

### Web NFC API not working

**Solution:**
1. Ensure HTTPS is enabled (required for Web NFC)
2. Use supported browser (Chrome 89+, Edge 89+, Safari 15+)
3. Check browser console for errors (F12)
4. Verify NFC permission granted

### Database migration issues

**Solution:**
```bash
# Reset database (development only!)
rm equipment.db
python init_db.py

# Or for PostgreSQL:
# DROP DATABASE equipment_db;
# CREATE DATABASE equipment_db;
# python init_db.py
```

### Static files not loading

**Solution:**
```bash
# Ensure CSS/JS files exist in app/static/
# Restart Flask server
# Check that Flask can find static files:
python -c "from flask import Flask, url_for; app = Flask(__name__); print(url_for('static', filename='css/style.css'))"
```

---

## Performance Optimization

### For Production

```bash
# Use Gunicorn with multiple workers
gunicorn --bind 0.0.0.0:8000 --workers 4 --worker-class sync run:app

# Or with async workers
pip install gevent
gunicorn --bind 0.0.0.0:8000 --worker-class gevent --worker-connections 1000 run:app
```

### Enable GZIP compression

Add to `app/__init__.py`:

```python
from flask_compress import Compress
Compress(app)
```

### Database query optimization

Add caching:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/equipment')
@cache.cached(timeout=300)
def get_equipment():
    # ...
```

---

## Security Checklist

- [ ] Change default admin password
- [ ] Update SECRET_KEY and JWT_SECRET
- [ ] Enable HTTPS/SSL
- [ ] Set secure database passwords
- [ ] Configure firewall rules
- [ ] Enable CORS only for trusted origins
- [ ] Set up database backups
- [ ] Enable authentication logging
- [ ] Update all dependencies regularly
- [ ] Use environment variables for secrets
- [ ] Disable debug mode in production
- [ ] Set secure session cookies

---

## Backup & Recovery

### Backup Database

**PostgreSQL:**
```bash
pg_dump equipment_db > backup_$(date +%Y%m%d).sql
```

**SQLite:**
```bash
cp equipment.db equipment_backup_$(date +%Y%m%d).db
```

### Restore Database

**PostgreSQL:**
```bash
psql equipment_db < backup_20240515.sql
```

**SQLite:**
```bash
cp equipment_backup_20240515.db equipment.db
```

### Backup Schedule

Set up automated backups (using cron on Linux/Mac):

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * pg_dump equipment_db > /backups/equipment_$(date +\%Y\%m\%d).sql
```

---

## Next Steps

After successful deployment:

1. ✅ Create user accounts for your organization (30 users)
2. ✅ Add your equipment with details
3. ✅ Generate and assign NFC tags
4. ✅ Train users on how to use the system
5. ✅ Set up automated backups
6. ✅ Configure email notifications (optional)
7. ✅ Monitor system performance
8. ✅ Collect user feedback and iterate

---

## Support & Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review logs:
   ```bash
   # Local development
   flask logs
   
   # Docker
   docker-compose logs app
   
   # Heroku
   heroku logs --tail
   ```

3. Check GitHub issues: https://github.com/whcbusi/equipment-management-system/issues

4. Review Flask documentation: https://flask.palletsprojects.com

---

**Version:** 1.0  
**Last Updated:** May 2024  
**Maintained By:** Equipment Management System Team

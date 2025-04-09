import os
from dotenv import load_dotenv
from flask_appbuilder.security.manager import (
    AUTH_OID,
    AUTH_REMOTE_USER,
    AUTH_DB,
    AUTH_LDAP,
    AUTH_OAUTH,
)

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
dotenv_path = os.path.join(basedir, '.env')
load_dotenv(dotenv_path)

# Your App secret key
SECRET_KEY = os.getenv("SECRET_KEY", "-0oi9u8ytfrdfcgdvbnjkmflda")

# The SQLAlchemy connection string.
db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
if db_uri and db_uri.startswith("sqlite:///") and not db_uri.startswith("sqlite:////"):
    # If it's a relative SQLite path, make it absolute
    db_path = db_uri.replace("sqlite:///", "")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, db_path)}"
else:
    SQLALCHEMY_DATABASE_URI = db_uri or "sqlite:///" + os.path.join(basedir, "app.db")

# Flask-WTF flag for CSRF
CSRF_ENABLED = os.getenv("CSRF_ENABLED", "True").lower() in ("true", "1", "t", "yes")

# SQLAlchemy track modifications
SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False").lower() in ("true", "1", "t", "yes")

# ------------------------------
# GLOBALS FOR APP Builder
# ------------------------------
# App name and icon
APP_NAME = os.getenv("APP_NAME", "Bandwidth Optimizer")
# APP_ICON = "static/img/bandwidth-icon.png"

# ----------------------------------------------------
# AUTHENTICATION CONFIG
# ----------------------------------------------------
# The authentication type
# AUTH_OID : Is for OpenID
# AUTH_DB : Is for database (username/password()
# AUTH_LDAP : Is for LDAP
# AUTH_REMOTE_USER : Is for using REMOTE_USER from web server
auth_type = os.getenv("AUTH_TYPE", "AUTH_DB")
AUTH_TYPE = globals().get(auth_type, AUTH_DB)  # Get the auth type from globals or default to AUTH_DB

# Uncomment to setup Full admin role name
# AUTH_ROLE_ADMIN = 'Admin'

# Uncomment to setup Public role name, no authentication needed
# AUTH_ROLE_PUBLIC = 'Public'

# Will allow user self registration
# AUTH_USER_REGISTRATION = True

# The default user self registration role
# AUTH_USER_REGISTRATION_ROLE = "Public"

# When using LDAP Auth, setup the ldap server
# AUTH_LDAP_SERVER = "ldap://ldapserver.new"

# Uncomment to setup OpenID providers example for OpenID authentication
# OPENID_PROVIDERS = [
#    { 'name': 'Yahoo', 'url': 'https://me.yahoo.com' },
#    { 'name': 'AOL', 'url': 'http://openid.aol.com/<username>' },
#    { 'name': 'Flickr', 'url': 'http://www.flickr.com/<username>' },
#    { 'name': 'MyOpenID', 'url': 'https://www.myopenid.com' }]
# ---------------------------------------------------
# Babel config for translations
# ---------------------------------------------------
# Setup default language
BABEL_DEFAULT_LOCALE = "en"
# Your application default translation path
BABEL_DEFAULT_FOLDER = "translations"
# The allowed translation for you app
LANGUAGES = {
    "en": {"flag": "gb", "name": "English"},
    "pt": {"flag": "pt", "name": "Portuguese"},
    "pt_BR": {"flag": "br", "name": "Pt Brazil"},
    "es": {"flag": "es", "name": "Spanish"},
    "de": {"flag": "de", "name": "German"},
    "zh": {"flag": "cn", "name": "Chinese"},
    "ru": {"flag": "ru", "name": "Russian"},
    "pl": {"flag": "pl", "name": "Polish"},
}
# ---------------------------------------------------
# Image and file configuration
# ---------------------------------------------------
# The file upload folder, when using models with files
UPLOAD_FOLDER = basedir + "/app/static/uploads/"

# The image upload folder, when using models with images
IMG_UPLOAD_FOLDER = basedir + "/app/static/uploads/"

# The image upload url, when using models with images
IMG_UPLOAD_URL = "/static/uploads/"
# Setup image size default is (300, 200, True)
# IMG_SIZE = (300, 200, True)

# Theme configuration
# these are located on static/appbuilder/css/themes
# you can create your own and easily use them placing them on the same dir structure to override
APP_THEME = "flatly.css"  # A clean, modern theme

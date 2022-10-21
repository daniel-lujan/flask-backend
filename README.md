# Backend
## Requirements
- **Python** v3.10.6
- **Flask** v2.2.2
- **Flask-Cors** v3.0.10
- **Flask PyMongo** v2.3.0
- **dnspython** (for `srv` Mongo connection modifier) v2.2.1
- **gunicorn** (for `Heroku Dyno` deployment) v20.1.0

## File Description
### Python modules
- **app.py:** Main `Flask` app.
- **auth.py:** `Flask Blueprint` for user authentication and permission processes.
- **constants.py:** App settings, enviroment variables loading, request templates, status codes, etc.
- **database.py:** Database initialization. Conection to collections and app settings loading.
- **models.py:** Classes used for `flask-login` and `auth.py` for user authentication and data loading.
- **mongo_collection.py:** Connection classes to `MongoDB ` database/collections.
- **static.py:** Other.
### Configuration files
- **Procfile:** `Heroku Dyno` process configuration.
- **requirements.txt:** All external Python modules used by the `Flask` application to be installed at `Heroku` hosted app.
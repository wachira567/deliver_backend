# ============================================
# Procfile for Render.com Deployment
# ============================================
# This file tells Render how to run your application
# ============================================

# Web service - uses gunicorn as the production WSGI server
# Render will automatically install dependencies from Pipfile if requirements.txt is not present
web: gunicorn --chdir /Users/andrewsigei/Development/phase_5/project/Deliveroo_backend app:app --preload --timeout 120 --workers 4 --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -

# Alternative command using pipenv:
# web: pipenv run gunicorn --chdir /Users/andrewsigei/Development/phase_5/project/Deliveroo_backend app:app --preload --timeout 120 --workers 4 --bind 0.0.0.0:$PORT

# ============================================
# Notes:
# - web: is the process type that Render looks for
# - $PORT is set automatically by Render
# - --preload loads the app before forking workers (faster startup)
# - --timeout 120 gives 2 minutes for slow database connections
# - --workers 4 runs 4 worker processes (adjust based on plan)
# - Render automatically detects Pipfile and installs dependencies
# ============================================


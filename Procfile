# ============================================
# Procfile for Render.com Deployment
# ============================================
# This file tells Render how to run your application
# ============================================

# Web service - uses gunicorn as the production WSGI server
web: gunicorn --chdir /Users/andrewsigei/Development/phase_5/project/Deliveroo_backend app:app --preload --timeout 120 --workers 4 --bind 0.0.0.0:$PORT --access-logfile - --error-logfile -

# Alternative command using the run.py file:
# web: gunicorn "run:app" --preload --timeout 120 --workers 4 --bind 0.0.0.0:$PORT

# For Debug mode (not recommended for production):
# web: flask --app app run --host 0.0.0.0 --port $PORT --debug=false

# ============================================
# Notes:
# - web: is the process type that Render looks for
# - $PORT is set automatically by Render
# - --preload loads the app before forking workers (faster startup)
# - --timeout 120 gives 2 minutes for slow database connections
# - --workers 4 runs 4 worker processes (adjust based on plan)
# ============================================


"""
Deliveroo - Parcel Delivery Management System
Main application entry point
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app, db

# Create Flask application instance
app = create_app()

# Flask shell context for easier debugging
@app.shell_context_processor
def make_shell_context():
    """
    Make database and models available in Flask shell
    Usage: flask shell
    """
    return {
        'db': db,
        # Models will be added here as they're created
        # 'User': User,
        # 'Order': Order,
    }

# Custom CLI commands
@app.cli.command()
def create_db():
    """
    Create database tables
    Usage: flask create-db
    """
    db.create_all()
    print("✅ Database tables created successfully!")

@app.cli.command()
def drop_db():
    """
    Drop all database tables (use with caution!)
    Usage: flask drop-db
    """
    if input("Are you sure you want to drop all tables? (yes/no): ").lower() == 'yes':
        db.drop_all()
        print("✅ All database tables dropped!")
    else:
        print("❌ Operation cancelled")

@app.cli.command()
def seed_db():
    """
    Seed database with initial data
    Usage: flask seed-db
    """
    from seed import seed_data
    seed_data()
    print("✅ Database seeded successfully!")

# Health check endpoint
@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return {
        'status': 'healthy',
        'message': 'Deliveroo API is running',
        'database': 'connected' if db.engine.url else 'not configured'
    }, 200

# Root endpoint
@app.route('/')
def index():
    """API root endpoint with available routes"""
    return {
        'message': 'Welcome to Deliveroo API',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health',
            'auth': '/auth/*',
            'orders': '/orders/*',
            'admin': '/admin/*',
            'courier': '/courier/*'
        }
    }, 200

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return {
        'error': 'Resource not found',
        'message': str(error)
    }, 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()  # Rollback any failed transactions
    return {
        'error': 'Internal server error',
        'message': 'Something went wrong on our end'
    }, 500

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return {
        'error': 'Bad request',
        'message': str(error)
    }, 400

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return {
        'error': 'Forbidden',
        'message': 'You do not have permission to access this resource'
    }, 403

@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return {
        'error': 'Unauthorized',
        'message': 'Authentication required'
    }, 401

# Run application
if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    
    # Get debug mode from environment variable
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"""
    ╔═══════════════════════════════════════╗
    ║     🚚 DELIVEROO API STARTING...     ║
    ╚═══════════════════════════════════════╝
    
    📍 Running on: http://127.0.0.1:{port}
    🔧 Debug mode: {debug}
    🗄️  Database: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] if app.config['SQLALCHEMY_DATABASE_URI'] else 'Not configured'}
    
    Available Commands:
    • flask create-db  - Create database tables
    • flask drop-db    - Drop all tables
    • flask seed-db    - Seed initial data
    • flask shell      - Open Flask shell
    • flask db init    - Initialize migrations
    • flask db migrate - Create migration
    • flask db upgrade - Apply migrations
    
    Press CTRL+C to quit
    """)
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
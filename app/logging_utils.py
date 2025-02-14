from datetime import datetime

def log_error(db, error_type, message, user_email="unknown"):
    error_ref = db.collection('errors').document()
    error_ref.set({
        'timestamp': datetime.now(),
        'error_type': error_type,
        'message': message,
        'user_email': user_email,
        'page': 'voting_interface'
    })

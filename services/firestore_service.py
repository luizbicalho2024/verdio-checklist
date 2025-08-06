from datetime import datetime
from .firebase_config import db # Importa o cliente 'db' já inicializado

# --- Funções de Usuário ---
def get_user(uid):
    doc_ref = db.collection("users").document(uid).get()
    return doc_ref.to_dict() if doc_ref.exists else None

def get_user_by_email(email):
    users_ref = db.collection("users").where("email", "==", email).limit(1).stream()
    for user in users_ref:
        user_data = user.to_dict()
        user_data['uid'] = user.id
        return user_data
    return None

def create_firestore_user(uid, email, role, password_hash, gestor_uid=None):
    user_data = {
        'email': email,
        'role': role,
        'password_hash': password_hash,
        'totp_enabled': False,
        'created_at': datetime.now()
    }
    if gestor_uid:
        user_data['gestor_uid'] = gestor_uid
    db.collection("users").document(uid).set(user_data)

def update_user_totp_info(uid, secret, enabled):
    db.collection("users").document(uid).update({
        'totp_secret': secret,
        'totp_enabled': enabled
    })

# --- Funções de Log ---
def log_action(user_email, action, details):
    log_data = {
        "timestamp": datetime.now(),
        "user": user_email,
        "action": action,
        "details": details
    }
    db.collection("logs").add(log_data)

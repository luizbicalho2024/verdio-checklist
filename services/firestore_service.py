from .firebase_config import db
from datetime import datetime

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
    
# ... (Adicione aqui as outras funções de serviço que você precisa:
# get_vehicle_sim_number, set_vehicle_sim_number, save_checklist,
# create_maintenance_order, get_maintenance_orders, etc.)

# -*- coding: utf-8 -*-
from datetime import datetime
from firebase_admin import firestore
from .firebase_config import db

def get_user(uid):
    doc_ref = db.collection("users").document(uid).get()
    return doc_ref.to_dict() if doc_ref.exists else None

def get_all_users():
    """Busca todos os usuários (motoristas e gestores) do Firestore."""
    users_ref = db.collection("users").stream()
    users_list = []
    for user in users_ref:
        user_data = user.to_dict()
        user_data['uid'] = user.id
        if user_data.get('role') != 'admin':
            users_list.append(user_data)
    return users_list

def get_all_managers():
    """Busca todos os usuários com o papel de 'gestor'."""
    users_ref = db.collection("users").where("role", "==", "gestor").stream()
    managers_list = []
    for user in users_ref:
        manager_data = user.to_dict()
        manager_data['uid'] = user.id
        managers_list.append(manager_data)
    return managers_list

def get_user_by_email(email):
    users_ref = db.collection("users").where("email", "==", email).limit(1).stream()
    for user in users_ref:
        user_data = user.to_dict()
        user_data['uid'] = user.id
        return user_data
    return None

def create_firestore_user(uid, email, role, password_hash, gestor_uid=None, etrac_api_key=None):
    user_data = {
        'email': email, 'role': role, 'password_hash': password_hash,
        'totp_enabled': False, 'created_at': datetime.now()
    }
    if gestor_uid:
        user_data['gestor_uid'] = gestor_uid
    if etrac_api_key:
        user_data['etrac_api_key'] = etrac_api_key
    db.collection("users").document(uid).set(user_data)

def update_user_data(uid, data_to_update):
    db.collection("users").document(uid).update(data_to_update)

def update_user_totp_info(uid, secret, enabled):
    db.collection("users").document(uid).update({'totp_secret': secret, 'totp_enabled': enabled})

def log_action(user_email, action, details):
    log_data = {"timestamp": datetime.now(), "user": user_email, "action": action, "details": details}
    db.collection("logs").add(log_data)

def get_logs_paginated(limit=20, start_after_doc=None):
    query = db.collection("logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    if start_after_doc:
        query = query.start_after(start_after_doc)
    return query.get()

def save_checklist(data):
    return db.collection("checklists").add(data)

def get_checklists_for_gestor(gestor_uid):
    query = db.collection("checklists").where("gestor_uid", "==", gestor_uid).order_by("timestamp", direction=firestore.Query.DESCENDING)
    return [doc.to_dict() for doc in query.stream()]

def get_pending_checklists_for_gestor(gestor_uid):
    query = db.collection("checklists").where("gestor_uid", "==", gestor_uid).where("status", "==", "Pendente").order_by("timestamp", direction=firestore.Query.DESCENDING)
    checklists = []
    for doc in query.stream():
        checklist_data = doc.to_dict()
        checklist_data['doc_id'] = doc.id
        checklists.append(checklist_data)
    return checklists

def update_checklist_status(doc_id, new_status, approver_email):
    db.collection("checklists").document(doc_id).update({
        "status": new_status, "approved_by": approver_email, "approval_timestamp": datetime.now()
    })

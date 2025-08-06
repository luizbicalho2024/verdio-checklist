# -*- coding: utf-8 -*-
from datetime import datetime
from firebase_admin import firestore
from .firebase_config import db

def get_user(uid):
    doc_ref = db.collection("users").document(uid).get()
    return doc_ref.to_dict() if doc_ref.exists else None

def get_all_users():
    users_ref = db.collection("users").stream()
    users_list = []
    for user in users_ref:
        user_data = user.to_dict()
        user_data['uid'] = user.id
        if user_data.get('role') != 'admin':
            users_list.append(user_data)
    return users_list

def get_user_by_email(email):
    users_ref = db.collection("users").where("email", "==", email).limit(1).stream()
    for user in users_ref:
        user_data = user.to_dict()
        user_data['uid'] = user.id
        return user_data
    return None

def create_firestore_user(uid, email, role, password_hash, gestor_uid=None, etrac_email=None, etrac_api_key=None):
    user_data = {
        'email': email, 'role': role, 'password_hash': password_hash,
        'totp_enabled': False, 'created_at': datetime.now()
    }
    if gestor_uid:
        user_data['gestor_uid'] = gestor_uid
    if etrac_email:
        user_data['etrac_email'] = etrac_email
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

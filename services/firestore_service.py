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

def get_all_managers():
    users_ref = db.collection("users").where("role", "==", "gestor").stream()
    managers_list = []
    for user in users_ref:
        manager_data = user.to_dict()
        manager_data['uid'] = user.id
        managers_list.append(manager_data)
    return managers_list

def get_drivers_for_manager(gestor_uid):
    """Busca todos os motoristas associados a um gestor específico."""
    query = db.collection("users").where("role", "==", "motorista").where("gestor_uid", "==", gestor_uid)
    drivers_list = []
    for doc in query.stream():
        driver_data = doc.to_dict()
        driver_data['uid'] = doc.id
        drivers_list.append(driver_data)
    return drivers_list

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
        'totp_enabled': False, 'created_at': datetime.now(),
        'is_active': True
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

def get_checklist_template():
    doc_ref = db.collection("app_configs").document("checklist_template").get()
    if doc_ref.exists:
        return doc_ref.to_dict().get("items", [])
    default_items = ["Pneus", "Luzes", "Freios", "Nível de Óleo", "Documentação"]
    db.collection("app_configs").document("checklist_template").set({"items": default_items})
    return default_items

def update_checklist_template(items_list):
    db.collection("app_configs").document("checklist_template").set({"items": items_list})

def create_maintenance_order(checklist_data):
    order_data = {
        "created_at": datetime.now(), "status": "Aberta",
        "vehicle_plate": checklist_data.get('vehicle_plate'),
        "driver_email": checklist_data.get('driver_email'),
        "gestor_uid": checklist_data.get('gestor_uid'),
        "checklist_notes": checklist_data.get('notes'),
        "failed_items": [item for item, status in checklist_data.get('items', {}).items() if status == "Não OK"],
        "maintenance_notes": ""
    }
    db.collection("maintenance_orders").add(order_data)

def get_maintenance_orders_for_gestor(gestor_uid):
    query = db.collection("maintenance_orders").where("gestor_uid", "==", gestor_uid).order_by("created_at", direction=firestore.Query.DESCENDING)
    orders = []
    for doc in query.stream():
        order_data = doc.to_dict()
        order_data['doc_id'] = doc.id
        orders.append(order_data)
    return orders

def update_maintenance_order(doc_id, updates):
    db.collection("maintenance_orders").document(doc_id).update(updates)

def update_vehicle_sim_number(plate, serial, sim_number, gestor_uid):
    doc_ref = db.collection("vehicles").document(plate)
    doc_ref.set({
        "placa": plate, "equipamento_serial": serial,
        "tracker_sim_number": sim_number, "gestor_uid": gestor_uid,
        "last_updated": datetime.now()
    })

def get_vehicle_details_by_plate(plate):
    doc_ref = db.collection("vehicles").document(plate).get()
    return doc_ref.to_dict() if doc_ref.exists else None

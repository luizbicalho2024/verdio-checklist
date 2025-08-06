import streamlit as st
from firebase_admin import firestore
import pandas as pd

# Inicializa a conexão
db = firestore.client()

# --- Funções de Usuário ---
def get_user(uid):
    user_ref = db.collection("users").document(uid).get()
    return user_ref.to_dict() if user_ref.exists else None

def create_firestore_user(uid, email, role, gestor_uid=None):
    user_data = {'email': email, 'role': role, 'totp_enabled': False}
    if gestor_uid:
        user_data['gestor_id'] = gestor_uid # UID do gestor
    db.collection("users").document(uid).set(user_data)

def update_user_totp_info(uid, secret, enabled):
    db.collection("users").document(uid).update({
        'totp_secret': secret,
        'totp_enabled': enabled
    })
# ... (todas as outras funções de `get_vehicle_sim_number`, `set_vehicle_sim_number`, etc., migram para cá) ...

# --- Funções de Checklist ---
def save_checklist(data):
    db.collection("checklists").add(data)

# --- Funções de Manutenção (NOVO) ---
def create_maintenance_order(data):
    db.collection("maintenance_orders").add(data)
    
@st.cache_data(ttl=300) # Cache de 5 minutos
def get_maintenance_orders(gestor_uid):
    orders_ref = db.collection("maintenance_orders").where("gestor_uid", "==", gestor_uid).stream()
    return [order.to_dict() for order in orders_ref]
    
def update_maintenance_order_status(order_id, new_status):
    docs = db.collection('maintenance_orders').where('order_id', '==', order_id).limit(1).get()
    if docs:
        doc_id = docs[0].id
        db.collection('maintenance_orders').document(doc_id).update({'status': new_status})
        return True
    return False

# --- Funções de Relatórios (NOVO) ---
@st.cache_data(ttl=600) # Cache de 10 minutos
def get_all_checklists_for_reports(gestor_uid):
    checklists_ref = db.collection("checklists").where("gestor_uid", "==", gestor_uid).stream()
    return [c.to_dict() for c in checklists_ref]
    
# --- Funções de Log com Paginação (NOVO) ---
def get_logs_paginated(limit=20, start_after_doc=None):
    query = db.collection("logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    if start_after_doc:
        query = query.start_after(start_after_doc)
    
    docs = query.get()
    return docs # Retorna os documentos para termos a referência do último

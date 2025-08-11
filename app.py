# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter
import numpy as np
import pyotp
import bcrypt
import requests
from firebase_admin import credentials, firestore, auth
import firebase_admin
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from math import radians, cos, sin, asin, sqrt
from io import BytesIO
import qrcode
from twilio.rest import Client

# ==============================================================================
# 1. CONFIGURAÇÃO E INICIALIZAÇÃO
# ==============================================================================

st.set_page_config(page_title="Checklist Veicular", layout="wide")

# --- Inicialização do Firebase (centralizada) ---
@st.cache_resource
def initialize_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        creds_dict = st.secrets["firebase_credentials"]
        creds_dict_pure = dict(creds_dict)
        creds = credentials.Certificate(creds_dict_pure)
        return firebase_admin.initialize_app(creds)

firebase_app = initialize_firebase_app()
db = firestore.client(app=firebase_app)
auth_client = auth

# ==============================================================================
# 2. FUNÇÕES DE SERVIÇO (do antigo services/)
# ==============================================================================

# --- Funções de Utilitários (do antigo utils/) ---
def generate_qr_code_image(uri):
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf); buf.seek(0)
    return buf

def haversine_distance(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1; dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a)); r = 6371000
    return c * r

# --- Funções do Firestore (do antigo firestore_service.py) ---
def get_user(uid):
    doc_ref = db.collection("users").document(uid).get()
    return doc_ref.to_dict() if doc_ref.exists else None

def get_all_users():
    users_ref = db.collection("users").where("role", "!=", "admin").stream()
    return [{'uid': user.id, **user.to_dict()} for user in users_ref]

def get_all_managers():
    users_ref = db.collection("users").where("role", "==", "gestor").stream()
    return [{'uid': user.id, **user.to_dict()} for user in users_ref]

def get_drivers_for_manager(gestor_uid):
    query = db.collection("users").where("role", "==", "motorista").where("gestor_uid", "==", gestor_uid)
    return [{'uid': doc.id, **doc.to_dict()} for doc in query.stream()]

def get_user_by_email(email):
    users_ref = db.collection("users").where("email", "==", email).limit(1).stream()
    for user in users_ref:
        user_data = user.to_dict(); user_data['uid'] = user.id
        return user_data
    return None

def create_firestore_user(uid, email, role, password_hash, gestor_uid=None, etrac_api_key=None):
    user_data = {
        'email': email, 'role': role, 'password_hash': password_hash,
        'totp_enabled': False, 'created_at': datetime.now(), 'is_active': True
    }
    if gestor_uid: user_data['gestor_uid'] = gestor_uid
    if etrac_api_key: user_data['etrac_api_key'] = etrac_api_key
    db.collection("users").document(uid).set(user_data)

def update_user_data(uid, data_to_update):
    db.collection("users").document(uid).update(data_to_update)

def log_action(user_email, action, details):
    db.collection("logs").add({"timestamp": datetime.now(), "user": user_email, "action": action, "details": details})

def save_checklist(data):
    try:
        _, doc_ref = db.collection("checklists").add(data)
        return doc_ref.id
    except Exception: return None

def update_checklist_with_photos(doc_id, photo_updates):
    db.collection("checklists").document(doc_id).update(photo_updates)

def get_checklists_for_gestor(gestor_uid):
    query = db.collection("checklists").where("gestor_uid", "==", gestor_uid).order_by("timestamp", direction=firestore.Query.DESCENDING)
    return [doc.to_dict() for doc in query.stream()]

def get_pending_checklists_for_gestor(gestor_uid):
    query = db.collection("checklists").where("gestor_uid", "==", gestor_uid).where("status", "==", "Pendente").order_by("timestamp", direction=firestore.Query.DESCENDING)
    checklists = []
    for doc in query.stream():
        checklist_data = doc.to_dict(); checklist_data['doc_id'] = doc.id
        checklists.append(checklist_data)
    return checklists

def update_checklist_status(doc_id, new_status, approver_email):
    db.collection("checklists").document(doc_id).update({"status": new_status, "approved_by": approver_email, "approval_timestamp": datetime.now()})

def get_checklist_template():
    doc_ref = db.collection("app_configs").document("checklist_template").get()
    if doc_ref.exists: return doc_ref.to_dict().get("items", [])
    default_items = ["Pneus", "Luzes", "Freios", "Nível de Óleo", "Documentação"]
    db.collection("app_configs").document("checklist_template").set({"items": default_items})
    return default_items

def update_checklist_template(items_list):
    db.collection("app_configs").document("checklist_template").set({"items": items_list})

def create_maintenance_order(order_data):
    db.collection("maintenance_orders").add(order_data)

def get_maintenance_orders_for_gestor(gestor_uid):
    query = db.collection("maintenance_orders").where("gestor_uid", "==", gestor_uid).order_by("created_at", direction=firestore.Query.DESCENDING)
    orders = []
    for doc in query.stream():
        order_data = doc.to_dict(); order_data['doc_id'] = doc.id
        orders.append(order_data)
    return orders

def update_maintenance_order(doc_id, updates):
    db.collection("maintenance_orders").document(doc_id).update(updates)

def update_vehicle_sim_number(plate, serial, sim_number, gestor_uid):
    db.collection("vehicles").document(plate).set({
        "placa": plate, "equipamento_serial": serial, "tracker_sim_number": sim_number,
        "gestor_uid": gestor_uid, "last_updated": datetime.now()
    })

def get_vehicle_details_by_plate(plate):
    doc_ref = db.collection("vehicles").document(plate).get()
    return doc_ref.to_dict() if doc_ref.exists else None

def save_geofence_settings(lat, lon, radius):
    db.collection("app_configs").document("geofence_settings").set({"latitude": lat, "longitude": lon, "radius_meters": radius})

def get_geofence_settings():
    doc_ref = db.collection("app_configs").document("geofence_settings").get()
    return doc_ref.to_dict() if doc_ref.exists else None

def update_maintenance_schedule(plate, data):
    data['notification_sent_for_km'] = data.get('last_maintenance_km', 0)
    db.collection("maintenance_schedules").document(plate).set(data, merge=True)

def get_maintenance_schedules_for_gestor(gestor_uid):
    query = db.collection("maintenance_schedules").where("gestor_uid", "==", gestor_uid).stream()
    return {doc.id: doc.to_dict() for doc in query}

def delete_maintenance_schedule(plate):
    try:
        db.collection("maintenance_schedules").document(plate).delete()
        return True
    except Exception: return False

def get_logs_paginated(limit=20, start_after_doc=None):
    query = db.collection("logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
    if start_after_doc:
        query = query.start_after(start_after_doc)
    return query.get()

# --- Funções de Autenticação (do antigo auth_service.py) ---
def set_custom_claims(uid, role, gestor_uid=None):
    claims = {'role': role}
    if gestor_uid: claims['gestor_uid'] = gestor_uid
    auth_client.set_custom_user_claims(uid, claims)

def create_user_with_password(email, password, role, gestor_uid=None, etrac_api_key=None):
    try:
        user = auth_client.create_user(email=email)
        set_custom_claims(user.uid, role, gestor_uid)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        create_firestore_user(user.uid, email, role, password_hash, gestor_uid, etrac_api_key)
        return user
    except Exception as e:
        st.error(f"Erro ao criar usuário: {e}"); return None

def set_user_disabled_status(uid, is_disabled: bool):
    try:
        auth_client.update_user(uid, disabled=is_disabled)
        return True
    except Exception as e:
        st.error(f"Erro ao alterar status do usuário: {e}"); return False

def update_auth_user(uid, email=None, password=None):
    try:
        if email and password: auth_client.update_user(uid, email=email, password=password)
        elif email: auth_client.update_user(uid, email=email)
        elif password: auth_client.update_user(uid, password=password)
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar autenticação: {e}"); return False

def verify_user_password(email, password):
    user_record = get_user_by_email(email)
    if user_record:
        stored_hash = user_record.get("password_hash")
        if stored_hash and bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return user_record
    return None

def is_totp_enabled(uid):
    user_data = get_user(uid)
    return user_data.get('totp_enabled', False) if user_data else False

def verify_totp_code(uid, code):
    user_data = get_user(uid)
    if user_data and user_data.get('totp_enabled'):
        secret = user_data.get('totp_secret')
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    return False

# --- Funções de Serviços Externos (eTrac, Twilio, Notificação, etc.) ---
def get_vehicles_from_etrac(email, api_key):
    # ... (código completo da função como na resposta anterior)
    pass

def send_email_notification(to_email, subject, body_html):
    # ... (código completo da função como na resposta anterior)
    pass

def logout():
    keys_to_delete = ['logged_in', 'user_uid', 'user_data', 'flow', 'pending_login_uid',
                      'editing_driver_uid', 'editing_schedule_plate', 'last_log_doc',
                      'trip_summary', 'maint_check_done', 'load_vehicles_for_maint',
                      'impersonated_uid', 'impersonated_user_data', 'current_checklist']
    for key in keys_to_delete:
        if key in st.session_state: del st.session_state[key]
    st.session_state['page'] = 'login'
    st.rerun()

# ==============================================================================
# 3. RENDERIZAÇÃO DAS PÁGINAS
# ==============================================================================

def render_motorista_page():
    # ... (código completo da página 1_Painel_Motorista.py)
    pass

def render_gestor_page():
    # ... (código completo da página 2_Painel_Gestor.py)
    pass

def render_admin_page():
    # ... (código completo da página 3_Admin.py)
    pass

def render_login_page():
    # ... (código completo da parte de login/registro/2FA do app.py)
    pass

# ==============================================================================
# 4. ROTEADOR PRINCIPAL DA APLICAÇÃO
# ==============================================================================

# Inicializa o estado da página
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# Roteador principal
if not st.session_state.get('logged_in'):
    render_login_page()
else:
    user_role = st.session_state.user_data.get('role')
    
    # Define as páginas acessíveis para cada papel
    if user_role == 'admin':
        PAGES = {"Painel Admin": render_admin_page, "Painel Gestor": render_gestor_page}
    elif user_role == 'gestor':
        PAGES = {"Painel Gestor": render_gestor_page}
    elif user_role == 'motorista':
        PAGES = {"Painel Motorista": render_motorista_page}
    else:
        PAGES = {}

    # Sidebar para navegação
    with st.sidebar:
        st.write(f"Logado como:")
        st.markdown(f"**{st.session_state.user_data.get('email')}**")
        if st.session_state.get('impersonated_uid'):
            st.info(f"Visualizando como:\n**{st.session_state.impersonated_user_data.get('email')}**")
        
        # Seleção de página na sidebar
        st.session_state.page = st.radio("Navegação", list(PAGES.keys()))
        
        if st.button("Sair", use_container_width=True):
            logout()
    
    # Renderiza a página selecionada
    page_function = PAGES.get(st.session_state.page)
    if page_function:
        page_function()
    else:
        st.error("Página não encontrada ou acesso negado.")

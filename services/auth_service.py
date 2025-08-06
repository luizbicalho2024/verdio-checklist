import streamlit as st
import pyotp
import bcrypt
from . import firestore_service as fs
from .firebase_config import auth_client, set_custom_claims

def create_user_with_password(email, password, role, gestor_uid=None):
    """Cria um usuário no Firebase Auth e um documento no Firestore com senha hash."""
    try:
        user = auth_client.create_user(email=email)
        set_custom_claims(user.uid, role, gestor_uid)
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        fs.create_firestore_user(user.uid, email, role, password_hash, gestor_uid)
        
        return user
    except Exception as e:
        st.error(f"Erro ao criar usuário: {e}")
        return None

def verify_user_password(email, password):
    """Verifica o email e a senha de um usuário buscando no Firestore."""
    user_auth_record = fs.get_user_by_email(email)
    if user_auth_record:
        stored_hash = user_auth_record.get("password_hash")
        if stored_hash and bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return user_auth_record
    return None

def generate_totp_secret():
    return pyotp.random_base32()

def get_totp_uri(email, secret):
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="ChecklistApp")

def enable_user_totp(uid, secret):
    fs.update_user_totp_info(uid, secret, enabled=True)

def verify_totp_code(uid, code):
    user_data = fs.get_user(uid)
    if user_data and user_data.get('totp_enabled'):
        secret = user_data.get('totp_secret')
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    return False

def verify_totp_code_with_secret(secret, code):
    """Verifica um código TOTP usando um segredo fornecido diretamente (para setup inicial)."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

def is_totp_enabled(uid):
    user_data = fs.get_user(uid)
    return user_data.get('totp_enabled', False) if user_data else False

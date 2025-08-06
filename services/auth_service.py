import streamlit as st
from firebase_admin import auth
import pyotp

# Importa o serviço de banco de dados para salvar/recuperar segredos 2FA
from . import firestore_service as fs 
from .firebase_config import set_custom_claims

def create_firebase_user(email, password, role, gestor_uid=None):
    """Cria um usuário no Firebase Authentication e no Firestore."""
    try:
        # Cria o usuário no serviço de autenticação
        user = auth.create_user(email=email, password=password)
        st.success(f"Usuário de autenticação {user.email} criado com UID: {user.uid}")
        
        # Define o papel do usuário (role) para as regras de segurança
        set_custom_claims(user.uid, role, gestor_uid)
        
        # Cria o documento correspondente do usuário no Firestore
        fs.create_firestore_user(user.uid, email, role, gestor_uid)
        
        return user
    except Exception as e:
        st.error(f"Erro ao criar usuário: {e}")
        return None

def sign_in(email, password):
    """Realiza o login com email e senha (mas não cria a sessão ainda)."""
    # Esta função é uma abstração. A verificação real acontece no frontend
    # usando a API do cliente ou verificando a senha com a hash.
    # Por simplicidade aqui, vamos buscar o usuário e assumir que a verificação de senha
    # seria feita em um ambiente seguro. No nosso caso, o login é conceitual
    # e a verificação do 2FA é a próxima etapa.
    try:
        user = auth.get_user_by_email(email)
        # NOTA: O SDK Admin não tem um método para verificar a senha.
        # Isso geralmente é feito no lado do cliente.
        # Aqui, estamos retornando o usuário para prosseguir com o fluxo de 2FA.
        return user
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        st.error(f"Erro de login: {e}")
        return None

def generate_totp_secret():
    """Gera um novo segredo para 2FA (TOTP)."""
    return pyotp.random_base32()

def get_totp_uri(email, secret):
    """Gera a URI 'otpauth://' para o QR Code."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name="ChecklistApp")

def enable_user_totp(uid, secret):
    """Salva o segredo TOTP e ativa o 2FA para o usuário no Firestore."""
    fs.update_user_totp_info(uid, secret, enabled=True)

def verify_totp_code(uid, code):
    """Verifica se o código 2FA fornecido pelo usuário é válido."""
    user_data = fs.get_user(uid)
    if user_data and user_data.get('totp_enabled'):
        secret = user_data.get('totp_secret')
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    return False

def is_totp_enabled(uid):
    """Verifica se o 2FA está ativo para um usuário."""
    user_data = fs.get_user(uid)
    return user_data.get('totp_enabled', False)

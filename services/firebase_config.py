import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth

@st.cache_resource
def initialize_firebase():
    """
    Inicializa o Firebase Admin SDK usando as credenciais do Streamlit Secrets.
    Garante que a inicialização ocorra apenas uma vez por sessão.
    """
    try:
        # Tenta obter a app padrão. Se não existir, lança ValueError.
        app = firebase_admin.get_app()
        return app
    except ValueError:
        # Se não foi inicializada, inicializa.
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        app = firebase_admin.initialize_app(creds)
        return app

def set_custom_claims(uid, role, gestor_uid=None):
    """
    Define 'custom claims' (papel, gestor) para um usuário no Firebase Auth.
    Isso é essencial para as regras de segurança.
    """
    claims = {'role': role}
    if gestor_uid:
        claims['gestor_uid'] = gestor_uid
    auth.set_custom_user_claims(uid, claims)

# Garante que o Firebase seja inicializado ao importar o módulo
firebase_app = initialize_firebase()

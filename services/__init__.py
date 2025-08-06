import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth

@st.cache_resource
def initialize_firebase_app():
    """
    Inicializa o Firebase Admin SDK se ainda não foi inicializado.
    Retorna a instância do app Firebase.
    """
    try:
        return firebase_admin.get_app()
    except ValueError:
        # A linha abaixo é a que causa o erro se creds_dict não for um dict.
        creds_dict = st.secrets["firebase_credentials"] 
        creds = credentials.Certificate(creds_dict)
        return firebase_admin.initialize_app(creds)

firebase_app = initialize_firebase_app()
db = firestore.client(app=firebase_app)
auth_client = auth

def set_custom_claims(uid, role, gestor_uid=None):
    """Define 'custom claims' (papel) para um usuário, essencial para as regras de segurança."""
    claims = {'role': role}
    if gestor_uid:
        claims['gestor_uid'] = gestor_uid
    auth_client.set_custom_user_claims(uid, claims)

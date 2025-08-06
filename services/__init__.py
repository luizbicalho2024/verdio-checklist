import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage

@st.cache_resource
def initialize_firebase_app():
    """
    Inicializa o Firebase Admin SDK usando as credenciais do Streamlit Secrets.
    Garante que a inicialização ocorra apenas uma vez.
    Retorna a instância do app Firebase.
    """
    try:
        return firebase_admin.get_app()
    except ValueError:
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        return firebase_admin.initialize_app(creds)

# Executa a inicialização e disponibiliza os clientes para importação
firebase_app = initialize_firebase_app()

db = firestore.client(app=firebase_app)
auth_client = auth
storage_bucket = storage.bucket(app=firebase_app)

def set_custom_claims(uid, role, gestor_uid=None):
    """Define 'custom claims' (papel) para um usuário, essencial para as regras de segurança."""
    claims = {'role': role}
    if gestor_uid:
        claims['gestor_uid'] = gestor_uid
    auth_client.set_custom_user_claims(uid, claims)

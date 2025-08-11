# -*- coding: utf-8 -*-
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage

@st.cache_resource
def initialize_firebase_app():
    """
    Inicializa o Firebase Admin SDK usando as credenciais do Streamlit Secrets,
    incluindo a configuração explícita do Storage Bucket.
    """
    try:
        return firebase_admin.get_app()
    except ValueError:
        creds_dict = st.secrets["firebase_credentials"]
        creds_dict_pure = dict(creds_dict)
        creds = credentials.Certificate(creds_dict_pure)
        
        # --- CORREÇÃO APLICADA AQUI ---
        # Passamos explicitamente o nome do bucket durante a inicialização.
        return firebase_admin.initialize_app(creds, {
            'storageBucket': creds_dict.get('storage_bucket')
        })

firebase_app = initialize_firebase_app()
db = firestore.client(app=firebase_app)
auth_client = auth
# Agora o storage.bucket() funcionará sem precisar passar o nome novamente.
storage_bucket = storage.bucket(app=firebase_app)


def set_custom_claims(uid, role, gestor_uid=None):
    claims = {'role': role}
    if gestor_uid:
        claims['gestor_uid'] = gestor_uid
    auth_client.set_custom_user_claims(uid, claims)

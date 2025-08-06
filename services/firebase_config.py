import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth

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

def set_custom_claims(uid, role, gestor_uid=None):
    claims = {'role': role}
    if gestor_uid:
        claims['gestor_uid'] = gestor_uid
    auth_client.set_custom_user_claims(uid, claims)

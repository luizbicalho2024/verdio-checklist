# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import pandas as pd

sys.path.append(os.getcwd())

from services import firestore_service, auth_service

st.set_page_config(page_title="Painel Admin", layout="wide")

if not st.session_state.get('logged_in'):
    st.warning("Faça o login."); st.stop()
user_data = st.session_state.get('user_data', {})
if user_data.get('role') != 'admin':
    st.error("Acesso negado."); st.stop()

st.title("👑 Painel de Administração")

tab1, tab2 = st.tabs(["🏢 Cadastrar Gestor", "📜 Logs de Auditoria"])

with tab1:
    st.subheader("Cadastrar Novo Gestor")
    with st.form("new_gestor_form", clear_on_submit=True):
        gestor_email = st.text_input("Email do Gestor")
        gestor_password = st.text_input("Senha Provisória", type="password")
        etrac_api_key = st.text_input("Chave da API eTrac do Gestor", type="password")
        if st.form_submit_button("Cadastrar Gestor"):
            if all([gestor_email, gestor_password, etrac_api_key]):
                if firestore_service.get_user_by_email(gestor_email):
                    st.error("Este email já está cadastrado.")
                else:
                    auth_service.create_user_with_password(
                        gestor_email,
                        gestor_password,
                        'gestor',
                        etrac_api_key=etrac_api_key
                    )
                    st.success(f"Gestor {gestor_email} criado!")
            else:
                st.warning("Preencha todos os campos.")

with tab2:
    st.subheader("Logs de Auditoria")
    if 'last_log_doc' not in st.session_state:
        st.session_state.last_log_doc = None
    
    logs_docs = firestore_service.get_logs_paginated(limit=10, start_after_doc=st.session_state.last_log_doc)
    if logs_docs:
        logs_data = [doc.to_dict() for doc in logs_docs]
        df = pd.DataFrame(logs_data)
        st.dataframe(df[['timestamp', 'user', 'action', 'details']], use_container_width=True)
        
        if len(logs_docs) == 10 and st.button("Carregar mais"):
            st.session_state.last_log_doc = logs_docs[-1]
            st.rerun()
    else:
        st.write("Nenhum log encontrado ou fim da lista.")

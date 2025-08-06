import sys
import os
import streamlit as st
import pandas as pd

sys.path.append(os.getcwd())

from services import firestore_service, auth_service

st.set_page_config(page_title="Dashboard Gestor", layout="wide")

if not st.session_state.get('logged_in'):
    st.warning("Faça o login.")
    st.stop()

user_data = st.session_state.get('user_data', {})
if user_data.get('role') != 'gestor':
    st.error("Acesso negado.")
    st.stop()

st.title(f"📊 Painel do Gestor, {user_data.get('email')}")

tab1, tab2, tab3 = st.tabs(["⚠️ Aprovações Pendentes", "📋 Histórico", "👤 Cadastrar Motorista"])

with tab1:
    st.subheader("Checklists Pendentes")
    st.info("Funcionalidade de aprovação de checklists pendentes a ser implementada aqui.")

with tab2:
    st.subheader("Histórico de Checklists")
    st.info("Funcionalidade de visualização do histórico de checklists a ser implementada aqui.")

with tab3:
    st.subheader("Cadastrar Novo Motorista")
    with st.form("new_driver_form", clear_on_submit=True):
        driver_email = st.text_input("Email do Motorista")
        driver_password = st.text_input("Senha Provisória", type="password")
        if st.form_submit_button("Cadastrar Motorista"):
            if driver_email and driver_password:
                if firestore_service.get_user_by_email(driver_email):
                    st.error("Este email já está cadastrado.")
                else:
                    auth_service.create_user_with_password(driver_email, driver_password, 'motorista', gestor_uid=st.session_state.user_uid)
                    firestore_service.log_action(user_data['email'], "CADASTRO_MOTORISTA", f"Motorista {driver_email} cadastrado.")
                    st.success(f"Motorista {driver_email} cadastrado com sucesso!")
            else:
                st.warning("Preencha todos os campos.")

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

with st.sidebar:
    st.write(f"Logado como:")
    st.markdown(f"**{user_data.get('email')}**")
    if st.button("Sair", use_container_width=True):
        auth_service.logout()

st.title("👑 Painel de Administração")

def clear_editing_state():
    if 'editing_user_uid' in st.session_state:
        del st.session_state['editing_user_uid']
    st.cache_data.clear()

tab1, tab2, tab3, tab4 = st.tabs(["⚙️ Gestão de Usuários", "👁️ Visualizar como Gestor", "📝 Gerenciar Checklist", "📜 Logs"])

with tab1:
    st.subheader("Gerenciar Usuários (Gestores e Motoristas)")
    if 'editing_user_uid' in st.session_state and st.session_state.editing_user_uid:
        uid_to_edit = st.session_state.editing_user_uid
        user_to_edit = firestore_service.get_user(uid_to_edit)
        
        st.markdown(f"### Editando: `{user_to_edit['email']}`")
        with st.form("edit_user_form"):
            new_email = st.text_input("Email", value=user_to_edit['email'])
            new_password = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")
            new_role = st.selectbox("Papel", options=['motorista', 'gestor'], index=['motorista', 'gestor'].index(user_to_edit['role']))
            
            new_etrac_api_key = user_to_edit.get('etrac_api_key', '')
            if new_role == 'gestor':
                new_etrac_api_key = st.text_input("Chave da API eTrac", value=new_etrac_api_key)

            new_gestor_uid = None
            if new_role == 'motorista':
                all_managers = firestore_service.get_all_managers()
                managers_dict = {manager['email']: manager['uid'] for manager in all_managers}
                if managers_dict:
                    current_gestor_uid = user_to_edit.get('gestor_uid')
                    manager_uids = list(managers_dict.values())
                    try:
                        current_index = manager_uids.index(current_gestor_uid) if current_gestor_uid in manager_uids else 0
                    except ValueError: current_index = 0
                    selected_manager_email = st.selectbox("Associar ao Gestor", options=managers_dict.keys(), index=current_index)
                    new_gestor_uid = managers_dict[selected_manager_email]
                else:
                    st.warning("Nenhum gestor cadastrado para associar este motorista.")

            submitted = st.form_submit_button("Salvar Alterações")
            if submitted:
                firestore_updates = {'email': new_email, 'role': new_role}
                if new_role == 'gestor':
                    firestore_updates['etrac_api_key'] = new_etrac_api_key
                    if 'gestor_uid' in user_to_edit: firestore_updates['gestor_uid'] = None
                if new_role == 'motorista':
                    firestore_updates['gestor_uid'] = new_gestor_uid
                    if 'etrac_api_key' in user_to_edit: firestore_updates['etrac_api_key'] = None
                
                firestore_service.update_user_data(uid_to_edit, firestore_updates)
                auth_service.update_auth_user(uid_to_edit, email=new_email, password=new_password if new_password else None)
                auth_service.update_user_role_and_claims(uid_to_edit, new_role, new_gestor_uid if new_role == 'motorista' else None)
                
                st.success(f"Usuário {new_email} atualizado com sucesso!")
                firestore_service.log_action(user_data['email'], "EDITAR_USUARIO", f"Dados de {new_email} foram alterados.")
                clear_editing_state()
                st.rerun()
        if st.button("Cancelar Edição"):
            clear_editing_state(); st.rerun()
    else:
        st.subheader("➕ Cadastrar Novo Gestor")
        with st.form("new_gestor_form", clear_on_submit=True):
            gestor_email = st.text_input("Email do Gestor (Login e Username da API)")
            gestor_password = st.text_input("Senha Provisória", type="password")
            etrac_api_key = st.text_input("Chave da API eTrac", type="password")
            if st.form_submit_button("Cadastrar Gestor"):
                if all([gestor_email, gestor_password, etrac_api_key]):
                    if firestore_service.get_user_by_email(gestor_email):
                        st.error("Este email já está cadastrado.")
                    else:
                        auth_service.create_user_with_password(gestor_email, gestor_password, 'gestor', etrac_api_key=etrac_api_key)
                        st.success(f"Gestor {gestor_email} criado!")
                else:
                    st.warning("Preencha todos os campos.")
        st.divider()
        st.subheader("📋 Lista de Usuários")
        if st.button("Recarregar Lista"):
            clear_editing_state(); st.rerun()

        all_users = firestore_service.get_all_users()
        if all_users:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.markdown("**Email**"); col2.markdown("**Papel**"); col3.markdown("**Gestor Associado**"); col4.markdown("**Ação**")
            for user_row in all_users:
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                    c1.write(user_row['email'])
                    c2.write(user_row['role'])
                    with c3:
                        gestor_email_display = ""
                        gestor_uid = user_row.get('gestor_uid')
                        if gestor_uid and isinstance(gestor_uid, str):
                            gestor = firestore_service.get_user(gestor_uid)
                            gestor_email_display = gestor['email'] if gestor else "UID não encontrado"
                        st.write(gestor_email_display)
                    with c4:
                        if st.button("✏️ Editar", key=f"edit_{user_row['uid']}"):
                            st.session_state['editing_user_uid'] = user_row['uid']
                            st.rerun()
                    st.divider()
        else:
            st.write("Nenhum motorista ou gestor cadastrado.")

with tab2:
    st.subheader("Visualizar Painel como Gestor")
    st.info("Selecione um gestor para visualizar o painel dele como se fosse ele.")
    managers = firestore_service.get_all_managers()
    if not managers:
        st.warning("Nenhum gestor cadastrado no sistema.")
    else:
        manager_options = {manager['email']: manager for manager in managers}
        selected_manager_email = st.selectbox("Selecione um gestor", options=manager_options.keys())
        if st.button("Visualizar Painel", type="primary"):
            selected_manager = manager_options[selected_manager_email]
            st.session_state['impersonated_uid'] = selected_manager['uid']
            st.session_state['impersonated_user_data'] = selected_manager
            st.switch_page("pages/2_Painel_Gestor.py")

with tab3:
    st.subheader("Gerenciar Modelo de Checklist Padrão")
    st.info("Edite os itens que os motoristas devem verificar. Salve para aplicar a todos os checklists futuros.")
    current_template = firestore_service.get_checklist_template()
    template_str = "\n".join(current_template)
    new_template_str = st.text_area("Itens do Checklist (um por linha)", value=template_str, height=250)
    if st.button("Salvar Modelo de Checklist", type="primary"):
        new_template_list = [line.strip() for line in new_template_str.split("\n") if line.strip()]
        firestore_service.update_checklist_template(new_template_list)
        st.success("Modelo de checklist salvo com sucesso!")
        st.cache_data.clear()

with tab4:
    st.subheader("Logs de Auditoria")
    if 'last_log_doc' not in st.session_state:
        st.session_state.last_log_doc = None
    logs_docs = firestore_service.get_logs_paginated(limit=10, start_after_doc=st.session_state.last_log_doc)
    if logs_docs:
        logs_data = [doc.to_dict() for doc in logs_docs]
        df = pd.DataFrame(logs_data)
        st.dataframe(df[['timestamp', 'user', 'action', 'details']], use_container_width=True, hide_index=True)
        if len(logs_docs) == 10 and st.button("Carregar mais"):
            st.session_state.last_log_doc = logs_docs[-1]
            st.rerun()
    else:
        st.write("Nenhum log encontrado ou fim da lista.")

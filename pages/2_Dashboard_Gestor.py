# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime

sys.path.append(os.getcwd())

from services import firestore_service, auth_service

st.set_page_config(page_title="Dashboard Gestor", layout="wide")

if not st.session_state.get('logged_in'):
    st.warning("Faça o login."); st.stop()
user_data = st.session_state.get('user_data', {})
if user_data.get('role') != 'gestor':
    st.error("Acesso negado."); st.stop()

gestor_uid = st.session_state.get('user_uid')
st.title(f"📊 Painel do Gestor, {user_data.get('email')}")

tab1, tab2, tab3 = st.tabs(["⚠️ Aprovações Pendentes", "📋 Histórico de Checklists", "👤 Cadastrar Motorista"])

with tab1:
    st.subheader("Checklists Pendentes de Aprovação")
    pending_checklists = firestore_service.get_pending_checklists_for_gestor(gestor_uid)

    if not pending_checklists:
        st.success("Nenhum checklist pendente no momento.")
    else:
        st.info(f"Você tem {len(pending_checklists)} checklist(s) aguardando sua ação.")
        for checklist in pending_checklists:
            # Formatando a data para melhor visualização
            checklist_time = checklist['timestamp'].strftime('%d/%m/%Y às %H:%M')
            with st.expander(f"**Veículo:** {checklist['vehicle_plate']} | **Motorista:** {checklist['driver_email']} | **Data:** {checklist_time}"):
                st.write("**Itens com inconformidades:**")
                inconformidades = {item: status for item, status in checklist['items'].items() if status == "Não OK"}
                for item, status in inconformidades.items():
                    st.warning(f"- {item.replace('_', ' ').capitalize()}: **{status}**")
                
                st.write("**Observações do Motorista:**")
                st.text_area("Notas", value=checklist['notes'], height=100, disabled=True, key=f"notes_{checklist['doc_id']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Aprovar Saída Mesmo Assim", key=f"approve_{checklist['doc_id']}", type="primary"):
                        firestore_service.update_checklist_status(checklist['doc_id'], "Aprovado pelo Gestor", user_data['email'])
                        firestore_service.log_action(user_data['email'], "APROVACAO_CHECKLIST", f"Checklist para {checklist['vehicle_plate']} aprovado.")
                        st.success("Checklist aprovado! A lista será atualizada.")
                        st.rerun() # Recarrega a página para atualizar a lista
                with col2:
                    if st.button("❌ Reprovar Saída", key=f"reject_{checklist['doc_id']}"):
                        firestore_service.update_checklist_status(checklist['doc_id'], "Reprovado pelo Gestor", user_data['email'])
                        firestore_service.log_action(user_data['email'], "REPROVACAO_CHECKLIST", f"Checklist para {checklist['vehicle_plate']} reprovado.")
                        st.error("Checklist reprovado. A lista será atualizada.")
                        st.rerun() # Recarrega a página para atualizar a lista

with tab2:
    st.subheader("Histórico Completo de Checklists")
    all_checklists = firestore_service.get_checklists_for_gestor(gestor_uid)

    if not all_checklists:
        st.info("Nenhum checklist encontrado no histórico.")
    else:
        # Prepara os dados para exibição no DataFrame
        display_data = []
        for item in all_checklists:
            display_data.append({
                "Data": item['timestamp'].strftime('%d/%m/%Y %H:%M'),
                "Veículo": item['vehicle_plate'],
                "Motorista": item['driver_email'],
                "Status": item['status'],
                "Observações": item['notes']
            })
        
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True)

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

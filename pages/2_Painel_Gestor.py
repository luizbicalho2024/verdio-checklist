# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter

sys.path.append(os.getcwd())

from services import firestore_service, auth_service

st.set_page_config(page_title="Painel Gestor", layout="wide")

is_impersonating = False
if st.session_state.get('user_data', {}).get('role') == 'admin' and st.session_state.get('impersonated_uid'):
    is_impersonating = True
    display_user_data = st.session_state.get('impersonated_user_data', {})
    display_uid = st.session_state.get('impersonated_uid')
    real_user_data = st.session_state.get('user_data', {})
else:
    if not st.session_state.get('logged_in'): st.warning("Faça o login."); st.stop()
    display_user_data = st.session_state.get('user_data', {})
    display_uid = st.session_state.get('user_uid')
    real_user_data = display_user_data
    if display_user_data.get('role') != 'gestor': st.error("Acesso negado."); st.stop()

with st.sidebar:
    st.write(f"Logado como:")
    st.markdown(f"**{real_user_data.get('email')}**")
    if is_impersonating:
        st.info(f"Visualizando como:\n**{display_user_data.get('email')}**")
    if st.button("Sair", use_container_width=True):
        auth_service.logout()

if is_impersonating:
    def exit_impersonation_mode():
        if 'impersonated_uid' in st.session_state: del st.session_state['impersonated_uid']
        if 'impersonated_user_data' in st.session_state: del st.session_state['impersonated_user_data']
        st.switch_page("pages/3_Admin.py")
    st.warning(f"⚠️ Você está visualizando o painel como o gestor **{display_user_data.get('email')}**.", icon="👁️")
    if st.button("⬅️ Voltar ao Painel de Admin"):
        exit_impersonation_mode()

st.title(f"📊 Painel do Gestor, {display_user_data.get('email')}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚠️ Aprovações", "📋 Histórico", "📈 Análise (BI)", "🛠️ Manutenção", "👤 Gerenciar Motoristas"])

with tab1:
    st.subheader("Checklists Pendentes de Aprovação")
    pending_checklists = firestore_service.get_pending_checklists_for_gestor(display_uid)
    if not pending_checklists:
        st.success("Nenhum checklist pendente no momento.")
    else:
        st.info(f"Você tem {len(pending_checklists)} checklist(s) aguardando sua ação.")
        for checklist in pending_checklists:
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
                        firestore_service.update_checklist_status(checklist['doc_id'], "Aprovado pelo Gestor", display_user_data['email'])
                        firestore_service.log_action(st.session_state.user_data['email'], "APROVACAO_CHECKLIST", f"Checklist para {checklist['vehicle_plate']} aprovado.")
                        st.rerun()
                with col2:
                    if st.button("❌ Reprovar e Criar OS", key=f"reject_{checklist['doc_id']}"):
                        firestore_service.update_checklist_status(checklist['doc_id'], "Reprovado pelo Gestor", display_user_data['email'])
                        firestore_service.create_maintenance_order(checklist)
                        firestore_service.log_action(st.session_state.user_data['email'], "REPROVACAO_CHECKLIST", f"Checklist para {checklist['vehicle_plate']} reprovado.")
                        st.error("Checklist reprovado e Ordem de Serviço criada.")
                        st.rerun()

with tab2:
    st.subheader("Histórico Completo de Checklists")
    all_checklists = firestore_service.get_checklists_for_gestor(display_uid)
    if not all_checklists:
        st.info("Nenhum checklist encontrado no histórico.")
    else:
        display_data = [{'Data': item['timestamp'].strftime('%d/%m/%Y %H:%M'), 'Veículo': item.get('vehicle_plate', 'N/A'),
                         'Motorista': item.get('driver_email', 'N/A'), 'Status': item.get('status', 'N/A'),
                         'Observações': item.get('notes', '')} for item in all_checklists]
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar como CSV", csv, f'historico_{datetime.now().strftime("%Y%m%d")}.csv', 'text/csv')

with tab3:
    st.subheader("Análise de Inconformidades (BI)")
    all_checklists = firestore_service.get_checklists_for_gestor(display_uid)
    if not all_checklists:
        st.info("Não há dados de checklists para analisar.")
    else:
        failed_items, failed_vehicles = [], []
        for checklist in all_checklists:
            if checklist.get('status') and 'Aprovado' not in checklist.get('status'):
                failed_vehicles.append(checklist.get('vehicle_plate'))
                for item, status in checklist.get('items', {}).items():
                    if status == 'Não OK':
                        failed_items.append(item.replace('_', ' ').capitalize())
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Itens que mais falham")
            if failed_items:
                item_counts = Counter(failed_items)
                fig, ax = plt.subplots()
                ax.pie(item_counts.values(), labels=item_counts.keys(), autopct='%1.1f%%', startangle=90)
                ax.axis('equal'); st.pyplot(fig)
            else:
                st.success("Nenhuma falha registrada!")
        with col2:
            st.markdown("##### Veículos com mais inconformidades")
            if failed_vehicles:
                vehicle_counts = Counter(failed_vehicles)
                df_v = pd.DataFrame(vehicle_counts.items(), columns=['Veículo', 'Nº de Falhas']).sort_values('Nº de Falhas', ascending=False)
                st.dataframe(df_v, use_container_width=True, hide_index=True)
            else:
                st.success("Nenhum veículo com falhas!")

with tab4:
    st.subheader("Ordens de Serviço (Manutenção)")
    orders = firestore_service.get_maintenance_orders_for_gestor(display_uid)
    if not orders:
        st.info("Nenhuma ordem de serviço encontrada.")
    else:
        for order in orders:
            with st.expander(f"**Veículo:** {order['vehicle_plate']} | **Status:** {order['status']} | **Data:** {order['created_at'].strftime('%d/%m/%Y')}"):
                st.write("**Itens Reportados:**", ", ".join(order.get('failed_items', [])))
                st.code(f"Observações do Motorista: {order.get('checklist_notes', 'Nenhuma.')}")
                new_status = st.selectbox("Alterar Status", ["Aberta", "Em Andamento", "Concluída"], index=["Aberta", "Em Andamento", "Concluída"].index(order['status']), key=f"status_{order['doc_id']}")
                maintenance_notes = st.text_area("Notas da Manutenção", value=order.get('maintenance_notes', ''), key=f"maint_notes_{order['doc_id']}")
                if st.button("Salvar Alterações na OS", key=f"save_os_{order['doc_id']}"):
                    updates = {"status": new_status, "maintenance_notes": maintenance_notes}
                    if new_status == "Concluída" and order['status'] != "Concluída":
                        updates['completed_at'] = datetime.now()
                    firestore_service.update_maintenance_order(order['doc_id'], updates)
                    st.success("Ordem de Serviço atualizada."); st.rerun()

with tab5:
    st.subheader("Gerenciar Equipe de Motoristas")
    if 'editing_driver_uid' in st.session_state:
        driver_to_edit = firestore_service.get_user(st.session_state.editing_driver_uid)
        st.markdown(f"### Editando Motorista: `{driver_to_edit['email']}`")
        with st.form("edit_driver_form"):
            new_email = st.text_input("Email do Motorista", value=driver_to_edit['email'])
            new_password = st.text_input("Nova Senha (deixe em branco para não alterar)", type="password")
            submitted = st.form_submit_button("Salvar Alterações")
            if submitted:
                auth_service.update_auth_user(st.session_state.editing_driver_uid, email=new_email, password=new_password if new_password else None)
                firestore_service.update_user_data(st.session_state.editing_driver_uid, {'email': new_email})
                st.success(f"Dados do motorista {new_email} atualizados.")
                firestore_service.log_action(real_user_data['email'], "EDITAR_MOTORISTA", f"Editou dados de {new_email}.")
                del st.session_state['editing_driver_uid']
                st.rerun()
        if st.button("Cancelar Edição"):
            del st.session_state['editing_driver_uid']
            st.rerun()
    else:
        with st.expander("➕ Adicionar Novo Motorista"):
            with st.form("new_driver_form", clear_on_submit=True):
                driver_email = st.text_input("Email do Novo Motorista")
                driver_password = st.text_input("Senha Provisória", type="password")
                if st.form_submit_button("Cadastrar Motorista"):
                    if driver_email and driver_password:
                        if firestore_service.get_user_by_email(driver_email):
                            st.error("Este email já está cadastrado.")
                        else:
                            auth_service.create_user_with_password(driver_email, driver_password, 'motorista', gestor_uid=display_uid)
                            firestore_service.log_action(real_user_data['email'], "CADASTRO_MOTORISTA", f"Cadastrou {driver_email}.")
                            st.success(f"Motorista {driver_email} cadastrado com sucesso!")
                    else:
                        st.warning("Preencha todos os campos.")
        st.divider()
        st.subheader("Lista de Motoristas")
        drivers = firestore_service.get_drivers_for_manager(display_uid)
        if not drivers:
            st.info("Nenhum motorista cadastrado para este gestor.")
        else:
            for driver in drivers:
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                is_active = driver.get('is_active', True)
                with col1:
                    st.write(driver['email'])
                with col2:
                    if is_active: st.success("✔️ Ativo")
                    else: st.error("❌ Desabilitado")
                with col3:
                    if st.button("✏️ Editar", key=f"edit_{driver['uid']}", disabled=not is_active):
                        st.session_state['editing_driver_uid'] = driver['uid']
                        st.rerun()
                with col4:
                    if is_active:
                        if st.button("Desabilitar", key=f"disable_{driver['uid']}"):
                            auth_service.set_user_disabled_status(driver['uid'], is_disabled=True)
                            firestore_service.update_user_data(driver['uid'], {'is_active': False})
                            st.rerun()
                    else:
                        if st.button("Habilitar", key=f"enable_{driver['uid']}", type="primary"):
                            auth_service.set_user_disabled_status(driver['uid'], is_disabled=False)
                            firestore_service.update_user_data(driver['uid'], {'is_active': True})
                            st.rerun()
                st.divider()

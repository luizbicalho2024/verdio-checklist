# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import pandas as pd

sys.path.append(os.getcwd())

from services import firestore_service, auth_service, etrac_service

st.set_page_config(page_title="Painel Admin", layout="wide")

if not st.session_state.get('logged_in'):
    st.switch_page("app.py")

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

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "⚙️ Gestão de Usuários", "👁️ Visualizar", "📲 Vincular Chip", 
    "📝 Checklist", "📍 Geofence", "🔧 Manut. Preventiva", "📜 Logs"
])

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
                    c1.write(user_row['email']); c2.write(user_row['role'])
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
    st.subheader("Vincular Número do Chip ao Veículo")
    st.info("Selecione um gestor para ver sua frota e associar o número de telefone do chip de cada rastreador.")
    all_managers_chip = firestore_service.get_all_managers()
    if not all_managers_chip:
        st.warning("Nenhum gestor cadastrado para selecionar.")
    else:
        manager_opts = {manager['email']: manager for manager in all_managers_chip}
        selected_manager_email = st.selectbox("Selecione um gestor para ver a frota", options=manager_opts.keys())
        selected_manager_data = manager_opts[selected_manager_email]
        gestor_uid = selected_manager_data['uid']
        api_key = selected_manager_data.get('etrac_api_key')
        if not api_key:
            st.error("Este gestor não possui uma chave de API eTrac configurada.")
        else:
            vehicles = etrac_service.get_vehicles_from_etrac(selected_manager_email, api_key)
            if not vehicles:
                st.warning("Nenhum veículo encontrado para este gestor na API eTrac.")
            else:
                st.write(f"Exibindo {len(vehicles)} veículos para **{selected_manager_email}**.")
                for i, vehicle in enumerate(vehicles):
                    plate = vehicle['placa']
                    serial = vehicle.get('idRastreador') or vehicle.get('equipamento_serial', 'N/A')
                    saved_data = firestore_service.get_vehicle_details_by_plate(plate)
                    current_sim = saved_data.get('tracker_sim_number', "") if saved_data else ""
                    col1, col2, col3 = st.columns([2, 2, 3])
                    col1.text(f"Placa: {plate}"); col2.text(f"Serial: {serial}")
                    with col3.form(key=f"form_{plate}_{i}"):
                        new_sim = st.text_input("Número do Chip (ex: +5569912345678)", value=current_sim, key=f"sim_{plate}_{i}")
                        if st.form_submit_button("Salvar"):
                            if new_sim and serial != 'N/A':
                                firestore_service.update_vehicle_sim_number(plate, serial, new_sim, gestor_uid)
                                st.success(f"Número do chip para a placa {plate} salvo!")
                                firestore_service.log_action(user_data['email'], "VINCULO_CHIP", f"Chip {new_sim} vinculado ao veículo {plate}.")
                                st.rerun()
                            else:
                                st.warning("Preencha o número do chip.")
                    st.divider()

with tab4:
    st.subheader("Gerenciar Modelo de Checklist Padrão")
    st.info("Edite os itens que os motoristas devem verificar. Salve para aplicar a todos os checklists futuros.")
    current_template = firestore_service.get_checklist_template()
    template_str = "\n".join(current_template)
    new_template_str = st.text_area("Itens do Checklist (um por linha)", value=template_str, height=250)
    if st.button("Salvar Modelo de Checklist", type="primary"):
        new_template_list = [line.strip() for line in new_template_str.split("\n") if line.strip()]
        firestore_service.update_checklist_template(new_template_list)
        st.success("Modelo de checklist salvo com sucesso!"); st.cache_data.clear()

with tab5:
    st.subheader("Configurar Geofence (Cerca Eletrônica)")
    st.info("Defina o ponto central e o raio do pátio da empresa. Checklists feitos fora desta área serão sinalizados.")
    current_settings = firestore_service.get_geofence_settings()
    lat_val = float(current_settings.get('latitude', 0.0)) if current_settings else 0.0
    lon_val = float(current_settings.get('longitude', 0.0)) if current_settings else 0.0
    rad_val = int(current_settings.get('radius_meters', 500)) if current_settings else 500
    with st.form("geofence_form"):
        lat = st.number_input("Latitude do Centro do Pátio", value=lat_val, format="%.6f")
        lon = st.number_input("Longitude do Centro do Pátio", value=lon_val, format="%.6f")
        radius = st.number_input("Raio da Cerca (em metros)", value=rad_val, min_value=50, step=50)
        if st.form_submit_button("Salvar Configurações", type="primary"):
            firestore_service.save_geofence_settings(lat, lon, radius)
            st.success("Configurações da geofence salvas com sucesso!")

with tab6:
    st.subheader("Planos de Manutenção Preventiva")
    st.info("Configure gatilhos de manutenção baseados em odômetro para os veículos.")
    all_managers_maint = firestore_service.get_all_managers()
    if all_managers_maint:
        manager_opts = {manager['email']: manager for manager in all_managers_maint}
        selected_manager_email = st.selectbox("Selecione um gestor para configurar a frota", options=manager_opts.keys(), key="maint_manager_select")
        selected_manager_data = manager_opts[selected_manager_email]
        gestor_uid = selected_manager_data['uid']
        api_key = selected_manager_data.get('etrac_api_key')
        if api_key:
            vehicles = etrac_service.get_vehicles_from_etrac(selected_manager_email, api_key)
            schedules = firestore_service.get_maintenance_schedules_for_gestor(gestor_uid)
            if vehicles:
                for i, v in enumerate(vehicles):
                    plate = v['placa']
                    schedule = schedules.get(plate, {})
                    with st.expander(f"Plano para {plate}"):
                        threshold_val = float(schedule.get('threshold_km', 10000))
                        last_km_val = float(schedule.get('last_maintenance_km', 0))
                        alert_range_val = float(schedule.get('alert_range_km', 500))
                        
                        with st.form(key=f"maint_form_{plate}_{i}"):
                            threshold = st.number_input("Realizar manutenção a cada (km)", min_value=1000.0, value=threshold_val, step=500.0)
                            last_km = st.number_input("Odômetro da Última Manutenção (km)", min_value=0.0, value=last_km_val)
                            alert_range = st.number_input("Gerar alerta X km antes do vencimento", min_value=100.0, value=alert_range_val, step=100.0)
                            notes = st.text_area("Descrição do Plano (ex: Troca de óleo e filtros)", value=schedule.get('notes', ''))
                            if st.form_submit_button("Salvar Plano"):
                                plan_data = {
                                    "gestor_uid": gestor_uid, "threshold_km": threshold,
                                    "last_maintenance_km": last_km, "alert_range_km": alert_range, "notes": notes
                                }
                                firestore_service.update_maintenance_schedule(plate, plan_data)
                                st.success(f"Plano de manutenção para {plate} salvo."); st.rerun()

with tab7:
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

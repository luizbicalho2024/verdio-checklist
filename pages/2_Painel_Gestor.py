# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter
import numpy as np

sys.path.append(os.getcwd())

from services import firestore_service, auth_service, etrac_service, notification_service

st.set_page_config(page_title="Painel Gestor", layout="wide")

# --- BLOCO DE VERIFICAÇÃO E REDIRECIONAMENTO ---
is_impersonating = False
# Verifica se é um admin impersonando um gestor
if st.session_state.get('user_data', {}).get('role') == 'admin' and st.session_state.get('impersonated_uid'):
    is_impersonating = True
    display_user_data = st.session_state.get('impersonated_user_data', {})
    display_uid = st.session_state.get('impersonated_uid')
    real_user_data = st.session_state.get('user_data', {})
else:
    # Se não estiver impersonando, verifica o login normal
    if not st.session_state.get('logged_in'):
        st.switch_page("app.py")  # Redireciona para o login se não estiver logado
    
    display_user_data = st.session_state.get('user_data', {})
    display_uid = st.session_state.get('user_uid')
    real_user_data = display_user_data
    if display_user_data.get('role') != 'gestor':
        st.error("Acesso negado.")
        st.stop()

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

# --- FUNÇÃO DE VERIFICAÇÃO DE MANUTENÇÃO ---
def check_for_maintenance_alerts(gestor_uid, gestor_email, api_key):
    schedules = firestore_service.get_maintenance_schedules_for_gestor(gestor_uid)
    if not schedules:
        return
    vehicles = etrac_service.get_vehicles_from_etrac(gestor_email, api_key)
    if not vehicles:
        return

    overdue_vehicles = []
    for vehicle in vehicles:
        plate = vehicle.get('placa')
        if not plate or plate not in schedules:
            continue
        
        try:
            current_odom_str = vehicle.get('odometro', '0').replace('km', '').replace('.', '').replace(',', '.').strip()
            current_odom = float(current_odom_str)
        except (ValueError, TypeError):
            continue

        schedule = schedules[plate]
        last_km = float(schedule.get('last_maintenance_km', 0))
        threshold = float(schedule.get('threshold_km', 0))
        notified_km = float(schedule.get('notification_sent_for_km', last_km))

        if threshold > 0 and current_odom > (last_km + threshold) and notified_km < (last_km + threshold):
            overdue_vehicles.append({
                "placa": plate, "odometro_atual": int(current_odom),
                "limite_km": int(last_km + threshold), "plano_desc": schedule.get('notes', 'Manutenção Preventiva')
            })
            firestore_service.update_maintenance_schedule(plate, {"notification_sent_for_km": last_km + threshold})
    if overdue_vehicles:
        for v in overdue_vehicles:
            st.toast(f"🚨 Alerta: Manutenção para {v['placa']} vencida!", icon="🚨")
        
        subject = "Alerta de Manutenção Preventiva Vencida"
        email_body = "<h3>Os seguintes veículos ultrapassaram o odômetro para a manutenção programada:</h3><ul>"
        for v in overdue_vehicles:
            email_body += f"<li><b>Veículo:</b> {v['placa']}<br><b>Manutenção:</b> {v['plano_desc']}<br><b>Odômetro Atual:</b> {v['odometro_atual']} km<br><b>Limite:</b> {v['limite_km']} km</li>"
        email_body += "</ul><p>Por favor, crie uma Ordem de Serviço no painel de manutenção.</p>"
        
        notification_service.send_email_notification(gestor_email, subject, email_body)
        firestore_service.log_action(gestor_email, "ALERTA_MANUTENCAO", f"{len(overdue_vehicles)} veículos com manutenção vencida.")

# --- RENDERIZAÇÃO DAS ABAS ---
tab_mapa, tab_aprov, tab_hist, tab_bi, tab_maint, tab_motoristas = st.tabs([
    "🗺️ Mapa da Frota", "⚠️ Aprovações", "📋 Histórico", "📈 Análise (BI)", "🛠️ Manutenção", "👤 Gerenciar Motoristas"
])

with tab_mapa:
    st.subheader("Localização da Frota em Tempo Real")
    if st.button("Atualizar Posições"):
        st.cache_data.clear()

    @st.cache_data(ttl=120)
    def get_vehicles_cached(email, api_key):
        return etrac_service.get_vehicles_from_etrac(email, api_key)

    vehicles_list = get_vehicles_cached(display_user_data.get('email'), display_user_data.get('etrac_api_key'))
    
    if not vehicles_list:
        st.warning("Nenhum veículo encontrado para exibir no mapa.")
    else:
        map_data, status_data = [], []
        for v in vehicles_list:
            lat, lon = v.get('latitude'), v.get('longitude')
            if lat and lon and str(lat).strip() and str(lon).strip():
                try: map_data.append({'lat': float(lat), 'lon': float(lon)})
                except (ValueError, TypeError): continue
            
            ignicao_status = "✔️ Ligada" if v.get('ignicao') == 1 else "❌ Desligada"
            bateria_status = f"{v.get('bateria')}V"
            status_data.append({
                "Veículo": f"{v.get('placa')} ({v.get('descricao')})",
                "Ignição": ignicao_status, "Bateria": bateria_status, "Velocidade": v.get('velocidade'),
                "Última Transmissão": v.get('data_transmissao')
            })
        
        if map_data:
            df_map = pd.DataFrame(map_data)
            st.map(df_map)
            st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum veículo com coordenadas válidas para exibir no mapa.")

with tab_aprov:
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

with tab_hist:
    st.subheader("Histórico de Checklists e Viagens")
    all_checklists = firestore_service.get_checklists_for_gestor(display_uid)
    if not all_checklists:
        st.info("Nenhum checklist encontrado no histórico.")
    else:
        display_data = [{'Data': item['timestamp'].strftime('%d/%m/%Y %H:%M'), 'Veículo': item.get('vehicle_plate', 'N/A'),
                         'Motorista': item.get('driver_email', 'N/A'), 'Status': item.get('status', 'N/A'),
                         'Localização': item.get('location_status', 'N/A'),
                         'Observações': item.get('notes', '')} for item in all_checklists]
        df = pd.DataFrame(display_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Histórico como CSV", csv, f'historico_checklists_{datetime.now().strftime("%Y%m%d")}.csv', 'text/csv')
    st.divider()
    st.subheader("Histórico Detalhado de Viagens por Veículo")
    vehicles_from_api_hist = etrac_service.get_vehicles_from_etrac(display_user_data.get('email'), display_user_data.get('etrac_api_key'))
    if vehicles_from_api_hist:
        plate_options = [v['placa'] for v in vehicles_from_api_hist]
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            selected_plate = st.selectbox("Selecione um veículo", options=plate_options, key="hist_plate_select")
        with col2:
            selected_date = st.date_input("Selecione uma data")
        with col3:
            st.write(""); st.write("")
            if st.button("Buscar Viagens"):
                with st.spinner("Buscando histórico de viagens..."):
                    trips = etrac_service.get_trip_summary(display_user_data.get('email'), display_user_data.get('etrac_api_key'), selected_plate, selected_date)
                    if 'trip_summary' not in st.session_state:
                        st.session_state.trip_summary = {}
                    st.session_state.trip_summary[selected_plate] = trips
        if 'trip_summary' in st.session_state and selected_plate in st.session_state.trip_summary:
            trips = st.session_state.trip_summary[selected_plate]
            if trips:
                st.dataframe(trips, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma viagem encontrada para este veículo nesta data.")

with tab_bi:
    st.subheader("Análise de Inconformidades (BI)")
    all_checklists_bi = firestore_service.get_checklists_for_gestor(display_uid)
    if not all_checklists_bi:
        st.info("Não há dados de checklists para analisar.")
    else:
        failed_items, failed_vehicles = [], []
        for checklist in all_checklists_bi:
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

with tab_maint:
    st.subheader("Manutenção")
    if 'maint_check_done' not in st.session_state:
        with st.spinner("Verificando alertas de manutenção..."):
            check_for_maintenance_alerts(
                gestor_uid=display_uid,
                gestor_email=display_user_data.get('email'),
                api_key=display_user_data.get('etrac_api_key')
            )
        st.session_state.maint_check_done = True
    
    st.subheader("Ordens de Serviço Corretivas e Preventivas")
    orders = firestore_service.get_maintenance_orders_for_gestor(display_uid)
    if not orders:
        st.info("Nenhuma ordem de serviço encontrada.")
    else:
        for order in orders:
            with st.expander(f"**Veículo:** {order['vehicle_plate']} | **Status:** {order['status']} | **Data:** {order['created_at'].strftime('%d/%m/%Y')}"):
                st.write("**Itens Reportados:**", ", ".join(order.get('failed_items', [])))
                st.code(f"Observações: {order.get('checklist_notes', 'Nenhuma.')}")
                new_status = st.selectbox("Alterar Status", ["Aberta", "Em Andamento", "Concluída"], index=["Aberta", "Em Andamento", "Concluída"].index(order['status']), key=f"status_{order['doc_id']}")
                maintenance_notes = st.text_area("Notas da Manutenção", value=order.get('maintenance_notes', ''), key=f"maint_notes_{order['doc_id']}")
                if st.button("Salvar Alterações na OS", key=f"save_os_{order['doc_id']}"):
                    updates = {"status": new_status, "maintenance_notes": maintenance_notes}
                    if new_status == "Concluída" and order['status'] != "Concluída":
                        updates['completed_at'] = datetime.now()
                    firestore_service.update_maintenance_order(order['doc_id'], updates)
                    st.success("Ordem de Serviço atualizada."); st.rerun()
    st.divider()
    with st.expander("Gerenciar Planos de Manutenção Preventiva"):
        if 'editing_schedule_plate' in st.session_state:
            plate_to_edit = st.session_state.editing_schedule_plate
            schedules = firestore_service.get_maintenance_schedules_for_gestor(display_uid)
            schedule_to_edit = schedules.get(plate_to_edit, {})
            vehicles_maint_list = etrac_service.get_vehicles_from_etrac(display_user_data.get('email'), display_user_data.get('etrac_api_key'))
            vehicle_info = next((v for v in vehicles_maint_list if v['placa'] == plate_to_edit), None)
            current_odometer = "N/A"
            if vehicle_info:
                current_odometer = vehicle_info.get('odometro', 'N/A')
            st.markdown(f"#### Editando Plano para `{plate_to_edit}`")
            st.info(f"Odômetro atual deste veículo: **{current_odometer}**")
            with st.form(key=f"maint_form_{plate_to_edit}"):
                threshold = st.number_input("Alertar a cada (km)", min_value=1000.0, value=float(schedule_to_edit.get('threshold_km', 10000)), step=500.0)
                last_km = st.number_input("Odômetro da Última Manutenção (km)", min_value=0.0, value=float(schedule_to_edit.get('last_maintenance_km', 0)))
                notes = st.text_area("Descrição do Plano (ex: Troca de óleo e filtros)", value=schedule_to_edit.get('notes', ''))
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Salvar Plano"):
                        plan_data = { "gestor_uid": display_uid, "threshold_km": threshold, "last_maintenance_km": last_km, "notes": notes }
                        firestore_service.update_maintenance_schedule(plate_to_edit, plan_data)
                        st.success(f"Plano de manutenção para {plate_to_edit} salvo.")
                        del st.session_state['editing_schedule_plate']
                        st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar"):
                        del st.session_state['editing_schedule_plate']
                        st.rerun()
        else:
            if st.button("Carregar Veículos para Gerenciar Planos"):
                st.session_state.load_vehicles_for_maint = True
            if st.session_state.get('load_vehicles_for_maint'):
                vehicles_maint = etrac_service.get_vehicles_from_etrac(display_user_data.get('email'), display_user_data.get('etrac_api_key'))
                schedules_maint = firestore_service.get_maintenance_schedules_for_gestor(display_uid)
                if vehicles_maint:
                    for v in vehicles_maint:
                        plate = v['placa']
                        schedule = schedules_maint.get(plate)
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if schedule:
                                st.success(f"**{plate}:** Plano ativo - Alertar a cada {int(schedule['threshold_km'])} km.")
                            else:
                                st.warning(f"**{plate}:** Nenhum plano de manutenção configurado.")
                        with col2:
                            button_text = "Editar Plano" if schedule else "Criar Plano"
                            if st.button(button_text, key=f"manage_sched_{plate}"):
                                st.session_state.editing_schedule_plate = plate
                                st.rerun()
                            if schedule and st.button("Excluir", key=f"delete_sched_{plate}"):
                                firestore_service.delete_maintenance_schedule(plate)
                                st.rerun()
                        st.divider()

with tab_motoristas:
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
                with col1: st.write(driver['email'])
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

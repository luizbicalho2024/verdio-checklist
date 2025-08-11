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

# --- LÓGICA DE IMPERSONIFICAÇÃO E LOGIN (sem alterações) ---
is_impersonating = False
if st.session_state.get('user_data', {}).get('role') == 'admin' and st.session_state.get('impersonated_uid'):
    is_impersonating = True
    display_user_data = st.session_state.get('impersonated_user_data', {})
    display_uid = st.session_state.get('impersonated_uid')
    real_user_data = st.session_state.get('user_data', {})
else:
    if not st.session_state.get('logged_in'): st.switch_page("app.py")
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

# --- FUNÇÃO DE VERIFICAÇÃO DE MANUTENÇÃO ATUALIZADA ---
def check_for_maintenance_alerts(gestor_uid, gestor_email, api_key):
    schedules = firestore_service.get_maintenance_schedules_for_gestor(gestor_uid)
    if not schedules: return
    vehicles = etrac_service.get_vehicles_from_etrac(gestor_email, api_key)
    if not vehicles: return

    overdue_vehicles = []
    for vehicle in vehicles:
        plate = vehicle.get('placa')
        if not plate or plate not in schedules: continue
        try:
            current_odom_str = vehicle.get('odometro', '0').replace('km', '').replace('.', '').replace(',', '.').strip()
            current_odom = float(current_odom_str)
        except (ValueError, TypeError): continue
        
        schedule = schedules[plate]
        last_km = float(schedule.get('last_maintenance_km', 0))
        threshold = float(schedule.get('threshold_km', 0))
        alert_range = float(schedule.get('alert_range_km', 0))
        notified_km = float(schedule.get('notification_sent_for_km', last_km))
        
        next_maintenance_km = last_km + threshold
        alert_starts_at_km = next_maintenance_km - alert_range

        if threshold > 0 and current_odom >= alert_starts_at_km and notified_km < alert_starts_at_km:
            overdue_vehicles.append({
                "placa": plate, "odometro_atual": int(current_odom), "limite_km": int(next_maintenance_km),
                "plano_desc": schedule.get('notes', 'Manutenção Preventiva')
            })
            # Cria a OS Preventiva automaticamente
            os_data = {
                "created_at": datetime.now(), "status": "Aberta", "vehicle_plate": plate,
                "driver_email": "SISTEMA", "gestor_uid": gestor_uid,
                "checklist_notes": f"Manutenção preventiva por odômetro. Limite de {int(next_maintenance_km)}km se aproximando. Odômetro atual: {int(current_odom)}km.",
                "failed_items": [schedule.get('notes', 'Manutenção Preventiva')], "maintenance_notes": ""
            }
            firestore_service.create_maintenance_order(os_data)
            # Atualiza o status da notificação para não enviar de novo neste ciclo
            firestore_service.update_maintenance_schedule(plate, {"notification_sent_for_km": next_maintenance_km})

    if overdue_vehicles:
        for v in overdue_vehicles:
            st.toast(f"🚨 Alerta: Manutenção para {v['placa']} está próxima!", icon="🚨")
        subject = "Alerta de Manutenção Preventiva Próxima do Vencimento"
        email_body = "<h3>Os seguintes veículos entraram na janela de alerta para manutenção programada:</h3><ul>"
        for v in overdue_vehicles:
            email_body += f"<li><b>Veículo:</b> {v['placa']}<br><b>Manutenção:</b> {v['plano_desc']}<br><b>Odômetro Atual:</b> {v['odometro_atual']} km<br><b>Limite:</b> {v['limite_km']} km</li>"
        email_body += "</ul><p>Uma Ordem de Serviço foi criada automaticamente no painel de manutenção.</p>"
        notification_service.send_email_notification(gestor_email, subject, email_body)
        firestore_service.log_action(gestor_email, "ALERTA_MANUTENCAO", f"{len(overdue_vehicles)} veículos com manutenção próxima.")

# --- RENDERIZAÇÃO DAS ABAS ---
tab_mapa, tab_aprov, tab_hist, tab_bi, tab_maint, tab_motoristas = st.tabs([
    "🗺️ Mapa da Frota", "⚠️ Aprovações", "📋 Histórico", "📈 Análise (BI)", "🛠️ Manutenção", "👤 Gerenciar Motoristas"
])
# ... (código das abas Mapa, Aprovações, Histórico, BI e Motoristas continua o mesmo) ...

with tab_maint:
    st.subheader("Manutenção")
    if 'maint_check_done' not in st.session_state:
        with st.spinner("Verificando alertas de manutenção..."):
            check_for_maintenance_alerts(gestor_uid=display_uid, gestor_email=display_user_data.get('email'), api_key=display_user_data.get('etrac_api_key'))
        st.session_state.maint_check_done = True
    
    st.subheader("Ordens de Serviço Corretivas e Preventivas")
    orders = firestore_service.get_maintenance_orders_for_gestor(display_uid)
    if not orders: st.info("Nenhuma ordem de serviço encontrada.")
    else:
        for order in orders:
            # ... (código para exibir ordens de serviço como antes) ...

    st.divider()
    with st.expander("Gerenciar Planos de Manutenção Preventiva"):
        if 'editing_schedule_plate' in st.session_state:
            plate_to_edit = st.session_state.editing_schedule_plate
            schedules = firestore_service.get_maintenance_schedules_for_gestor(display_uid)
            schedule_to_edit = schedules.get(plate_to_edit, {})
            vehicles_maint_list = etrac_service.get_vehicles_from_etrac(display_user_data.get('email'), display_user_data.get('etrac_api_key'))
            vehicle_info = next((v for v in vehicles_maint_list if v['placa'] == plate_to_edit), None)
            current_odometer = "N/A"
            if vehicle_info: current_odometer = vehicle_info.get('odometro', 'N/A')
            
            st.markdown(f"#### Editando Plano para `{plate_to_edit}`")
            st.info(f"Odômetro atual deste veículo: **{current_odometer}**")
            with st.form(key=f"maint_form_{plate_to_edit}"):
                threshold = st.number_input("Realizar manutenção a cada (km)", min_value=1000.0, value=float(schedule_to_edit.get('threshold_km', 10000)), step=500.0)
                last_km = st.number_input("Odômetro da Última Manutenção (km)", min_value=0.0, value=float(schedule_to_edit.get('last_maintenance_km', 0)))
                # NOVO CAMPO PARA O RANGE DO ALERTA
                alert_range = st.number_input("Gerar alerta X km antes do vencimento", min_value=100.0, value=float(schedule_to_edit.get('alert_range_km', 500)), step=100.0)
                notes = st.text_area("Descrição do Plano (ex: Troca de óleo e filtros)", value=schedule_to_edit.get('notes', ''))
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Salvar Plano"):
                        plan_data = { "gestor_uid": display_uid, "threshold_km": threshold, "last_maintenance_km": last_km, "alert_range_km": alert_range, "notes": notes }
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
                            if schedule: st.success(f"**{plate}:** Plano ativo - Manutenção a cada {int(schedule['threshold_km'])} km.")
                            else: st.warning(f"**{plate}:** Nenhum plano de manutenção configurado.")
                        with col2:
                            button_text = "Editar Plano" if schedule else "Criar Plano"
                            if st.button(button_text, key=f"manage_sched_{plate}"):
                                st.session_state.editing_schedule_plate = plate
                                st.rerun()
                            if schedule and st.button("Excluir", key=f"delete_sched_{plate}"):
                                firestore_service.delete_maintenance_schedule(plate); st.rerun()
                        st.divider()

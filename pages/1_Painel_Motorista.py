# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
from datetime import datetime

sys.path.append(os.getcwd())

from services import firestore_service, etrac_service, notification_service, auth_service, twilio_service

st.set_page_config(page_title="Painel Motorista", layout="wide")

if not st.session_state.get('logged_in'):
    st.warning("Por favor, faça o login para acessar esta página.")
    st.stop()

user_data = st.session_state.get('user_data', {})
if user_data.get('role') != 'motorista':
    st.error("Acesso negado.")
    st.stop()

with st.sidebar:
    st.write(f"Logado como:")
    st.markdown(f"**{user_data.get('email')}**")
    if st.button("Sair", use_container_width=True):
        auth_service.logout()

st.title(f"📋 Checklist Pré-Jornada")

gestor_uid = user_data.get('gestor_uid')
if not gestor_uid:
    st.error("Este usuário motorista não está associado a nenhum gestor. Por favor, contate um administrador.")
    st.stop()

gestor_data = firestore_service.get_user(gestor_uid)
gestor_email_acesso = gestor_data.get('email') if gestor_data else None
gestor_etrac_api_key = gestor_data.get('etrac_api_key') if gestor_data else None

if not gestor_email_acesso or not gestor_etrac_api_key:
    st.error("Seu gestor não foi encontrado ou não possui credenciais da eTrac configuradas.")
    st.stop()

vehicles = etrac_service.get_vehicles_from_etrac(gestor_email_acesso, gestor_etrac_api_key)
if not vehicles:
    st.warning("Nenhum veículo foi retornado pela API da eTrac.")
    st.stop()

checklist_items_template = firestore_service.get_checklist_template()
if not checklist_items_template:
    st.error("Modelo de checklist não encontrado. Contate o administrador.")
    st.stop()

vehicle_options = {f"{v['placa']} - {v.get('modelo', '')}": v for v in vehicles}
selected_vehicle_str = st.selectbox("Selecione o Veículo", options=vehicle_options.keys())

if selected_vehicle_str:
    selected_vehicle_data = vehicle_options[selected_vehicle_str]
    st.subheader(f"Itens de Verificação para {selected_vehicle_data['placa']}")
    
    with st.form("checklist_form"):
        results = {}
        for item in checklist_items_template:
            results[item] = st.radio(item.replace('_', ' ').capitalize(), ["OK", "Não OK"], horizontal=True)
        
        notes = st.text_area("Observações (obrigatório se algum item for 'Não OK')")
        
        if st.form_submit_button("Enviar Checklist"):
            is_ok = all(status == "OK" for status in results.values())
            if not is_ok and not notes:
                st.error("Preencha as observações se algum item estiver 'Não OK'.")
            else:
                checklist_data = {
                    "vehicle_plate": selected_vehicle_data['placa'],
                    "tracker_id": selected_vehicle_data.get('idRastreador'),
                    "driver_uid": st.session_state.user_uid,
                    "driver_email": user_data['email'],
                    "gestor_uid": user_data['gestor_uid'],
                    "timestamp": datetime.now(),
                    "items": results,
                    "notes": notes,
                    "status": "Aprovado" if is_ok else "Pendente"
                }
                
                if is_ok:
                    st.balloons()
                    plate = selected_vehicle_data['placa']
                    serial = selected_vehicle_data.get('idRastreador')
                    
                    vehicle_details = firestore_service.get_vehicle_details_by_plate(plate)
                    
                    if vehicle_details and vehicle_details.get('tracker_sim_number'):
                        sim_number = vehicle_details['tracker_sim_number']
                        st.info(f"Todos os itens OK. Enviando comando de desbloqueio para o veículo {plate}...")
                        twilio_service.send_unlock_sms(
                            to_number=sim_number,
                            equipamento_serial=serial,
                            admin_email_logger=user_data['email']
                        )
                    else:
                        st.error(f"ERRO: Não foi possível desbloquear o veículo {plate}. Nenhum número de chip está vinculado. Avise o administrador.")
                        checklist_data['status'] = "Pendente"
                        checklist_data['notes'] += "\n\n[SISTEMA] Falha no desbloqueio automático: Chip não cadastrado."
                else:
                    st.warning("Checklist com inconformidades. Seu gestor foi notificado por e-mail.")
                    if gestor_data and gestor_data.get('email'):
                        subject = f"Alerta: Checklist Pendente para o Veículo {selected_vehicle_data['placa']}"
                        body = f"""
                        <h3>Checklist com Inconformidades</h3>
                        <p>O motorista <b>{user_data['email']}</b> submeteu um checklist para o veículo <b>{selected_vehicle_data['placa']}</b> que requer sua atenção.</p>
                        <p><b>Observações:</b> {notes}</p>
                        <p>Por favor, acesse o painel de gestor para aprovar ou reprovar a saída do veículo.</p>
                        """
                        notification_service.send_email_notification(gestor_data['email'], subject, body)

                firestore_service.save_checklist(checklist_data)
                firestore_service.log_action(user_data['email'], "CHECKLIST_ENVIADO", f"Veículo {selected_vehicle_data['placa']} status {checklist_data['status']}.")
                st.success("Checklist enviado com sucesso!")

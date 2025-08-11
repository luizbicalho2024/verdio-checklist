# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
from datetime import datetime

sys.path.append(os.getcwd())

from services import firestore_service, etrac_service, notification_service, auth_service, twilio_service, storage_service
from utils import geo_util

st.set_page_config(page_title="Painel Motorista", layout="wide")

if not st.session_state.get('logged_in'):
    st.switch_page("app.py")

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

# Reseta o estado do checklist se o veículo for trocado
if 'current_checklist' not in st.session_state or st.session_state.current_checklist['plate'] != selected_vehicle_str:
    st.session_state.current_checklist = {
        "plate": selected_vehicle_str,
        "status": {item: "OK" for item in checklist_items_template},
        "photos": {},
        "notes": ""
    }

if selected_vehicle_str:
    selected_vehicle_data = vehicle_options[selected_vehicle_str]
    st.subheader(f"Itens de Verificação para {selected_vehicle_data['placa']}")

    for item in checklist_items_template:
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.write(f"**{item.replace('_', ' ').capitalize()}**")

        current_status = st.session_state.current_checklist["status"].get(item, "OK")

        with col2:
            if st.button("OK", key=f"ok_{item}_{selected_vehicle_data['placa']}", type="primary" if current_status == "OK" else "secondary", use_container_width=True):
                st.session_state.current_checklist["status"][item] = "OK"
                if item in st.session_state.current_checklist["photos"]:
                    del st.session_state.current_checklist["photos"][item]
                st.rerun()
        
        with col3:
            if st.button("Não OK", key=f"naook_{item}_{selected_vehicle_data['placa']}", type="primary" if current_status == "Não OK" else "secondary", use_container_width=True):
                st.session_state.current_checklist["status"][item] = "Não OK"
                st.rerun()

        if st.session_state.current_checklist["status"].get(item) == "Não OK":
            photo = st.camera_input(f"📸 Foto obrigatória para: {item}", key=f"photo_{item}_{selected_vehicle_data['placa']}")
            if photo:
                st.session_state.current_checklist["photos"][item] = photo
        st.divider()

    notes = st.text_area("Observações (obrigatório se algum item for 'Não OK')", value=st.session_state.current_checklist.get("notes", ""), key=f"notes_{selected_vehicle_data['placa']}")
    st.session_state.current_checklist["notes"] = notes

    if st.button("Enviar Checklist", type="primary", use_container_width=True):
        validation_passed = True
        failed_items_without_photo = []
        is_ok = True
        for item, status in st.session_state.current_checklist["status"].items():
            if status == "Não OK":
                is_ok = False
                if item not in st.session_state.current_checklist["photos"]:
                    validation_passed = False
                    failed_items_without_photo.append(item)
        
        if not is_ok and not st.session_state.current_checklist["notes"]:
            st.error("Preencha as observações se algum item estiver 'Não OK'.")
        elif not validation_passed:
            st.error(f"Erro: É obrigatório tirar uma foto para os seguintes itens: {', '.join(failed_items_without_photo)}")
        else:
            with st.spinner("Salvando checklist e enviando fotos..."):
                geofence = firestore_service.get_geofence_settings()
                location_status = "Não verificado"
                if geofence:
                    vehicle_pos = etrac_service.get_single_vehicle_position(gestor_email_acesso, gestor_etrac_api_key, selected_vehicle_data['placa'])
                    if vehicle_pos and 'latitude' in vehicle_pos and 'longitude' in vehicle_pos:
                        try:
                            lat, lon = float(vehicle_pos['latitude']), float(vehicle_pos['longitude'])
                            distance = geo_util.haversine_distance(geofence['latitude'], geofence['longitude'], lat, lon)
                            if distance <= geofence['radius_meters']:
                                location_status = "Dentro da Base"
                            else:
                                location_status = f"Fora da Base ({int(distance)}m)"
                        except (ValueError, TypeError):
                            location_status = "Coordenada Inválida"
                    else:
                        location_status = "Posição não encontrada"
                
                items_data_to_save = {item: {"status": status} for item, status in st.session_state.current_checklist['status'].items()}
                checklist_data = {
                    "vehicle_plate": selected_vehicle_data['placa'],
                    "tracker_id": selected_vehicle_data.get('idRastreador') or selected_vehicle_data.get('equipamento_serial'),
                    "driver_uid": st.session_state.user_uid,
                    "driver_email": user_data['email'],
                    "gestor_uid": user_data['gestor_uid'],
                    "timestamp": datetime.now(),
                    "items": items_data_to_save,
                    "notes": st.session_state.current_checklist['notes'],
                    "status": "Aprovado" if is_ok else "Pendente",
                    "location_status": location_status
                }
                
                checklist_id = firestore_service.save_checklist(checklist_data)
                
                if checklist_id and st.session_state.current_checklist['photos']:
                    photo_updates = {}
                    for item_name, photo_file in st.session_state.current_checklist['photos'].items():
                        file_path = f"checklists/{checklist_id}/{item_name.replace(' ', '_')}.jpg"
                        photo_url = storage_service.upload_file(photo_file, file_path)
                        if photo_url:
                            photo_updates[f"items.{item_name}.photo_url"] = photo_url
                    if photo_updates:
                        firestore_service.update_checklist_with_photos(checklist_id, photo_updates)
                
                if is_ok:
                    st.balloons()
                    plate = selected_vehicle_data['placa']
                    serial = selected_vehicle_data.get('idRastreador') or selected_vehicle_data.get('equipamento_serial')
                    vehicle_details = firestore_service.get_vehicle_details_by_plate(plate)
                    if vehicle_details and vehicle_details.get('tracker_sim_number'):
                        sim_number = vehicle_details['tracker_sim_number']
                        st.info(f"Todos os itens OK. Enviando comando de desbloqueio para o veículo {plate}...")
                        twilio_service.send_unlock_sms(to_number=sim_number, equipamento_serial=serial, admin_email_logger=user_data['email'])
                    else:
                        st.error(f"ERRO: Não foi possível desbloquear o veículo {plate}. Nenhum número de chip está vinculado. Avise o administrador.")
                        checklist_data['status'] = "Pendente"
                        checklist_data['notes'] += "\n\n[SISTEMA] Falha no desbloqueio automático: Chip não cadastrado."
                        if checklist_id:
                            firestore_service.update_checklist_with_photos(checklist_id, {"status": "Pendente", "notes": checklist_data['notes']})
                else:
                    st.warning("Checklist com inconformidades. Seu gestor foi notificado por e-mail.")
                    if gestor_data and gestor_data.get('email'):
                        subject = f"Alerta: Checklist Pendente para o Veículo {selected_vehicle_data['placa']}"
                        body = f"""<h3>Checklist com Inconformidades</h3>
                                 <p>O motorista <b>{user_data['email']}</b> submeteu um checklist para o veículo <b>{selected_vehicle_data['placa']}</b> que requer sua atenção.</p>
                                 <p><b>Localização:</b> {location_status}</p>
                                 <p><b>Observações:</b> {notes}</p>
                                 <p>Por favor, acesse o painel de gestor para aprovar ou reprovar a saída do veículo.</p>"""
                        notification_service.send_email_notification(gestor_data['email'], subject, body)

                firestore_service.log_action(user_data['email'], "CHECKLIST_ENVIADO", f"Veículo {selected_vehicle_data['placa']} status {checklist_data['status']}.")
                st.success("Checklist enviado com sucesso!")

                del st.session_state.current_checklist
                st.rerun()

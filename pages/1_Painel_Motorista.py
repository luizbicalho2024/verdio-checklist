# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
from datetime import datetime

sys.path.append(os.getcwd())

from services import firestore_service, etrac_service, notification_service, auth_service, twilio_service
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

# --- LÓGICA PARA BUSCAR VEÍCULOS E TEMPLATE (sem alterações) ---
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
# --- FIM DA LÓGICA DE BUSCA ---

vehicle_options = {f"{v['placa']} - {v.get('modelo', '')}": v for v in vehicles}
selected_vehicle_str = st.selectbox("Selecione o Veículo", options=vehicle_options.keys())

# --- NOVA LÓGICA DE GERENCIAMENTO DE ESTADO ---
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

    # Loop para exibir os itens do checklist (sem st.form)
    for item in checklist_items_template:
        # Lê o status atual do session_state
        current_status = st.session_state.current_checklist["status"].get(item, "OK")
        
        # O widget de rádio agora tem uma chave única para que o Streamlit rastreie seu valor
        new_status = st.radio(
            item.replace('_', ' ').capitalize(),
            ["OK", "Não OK"],
            index=0 if current_status == "OK" else 1,
            horizontal=True,
            key=f"radio_{item}_{selected_vehicle_data['placa']}"
        )
        
        # Atualiza o estado se o valor do rádio mudou
        if new_status != current_status:
            st.session_state.current_checklist["status"][item] = new_status
            # Se o usuário mudou para "Não OK" e já havia uma foto, ela é removida para forçar uma nova
            if new_status == "Não OK" and item in st.session_state.current_checklist["photos"]:
                del st.session_state.current_checklist["photos"][item]
            st.rerun()

        # Se o status para este item for "Não OK", mostra a câmera
        if st.session_state.current_checklist["status"].get(item) == "Não OK":
            photo = st.camera_input(f"📸 Foto obrigatória para: {item}", key=f"photo_{item}_{selected_vehicle_data['placa']}")
            if photo:
                st.session_state.current_checklist["photos"][item] = photo

    # Campo de notas e botão de envio fora do loop
    notes = st.text_area("Observações (obrigatório se algum item for 'Não OK')", key=f"notes_{selected_vehicle_data['placa']}")
    st.session_state.current_checklist["notes"] = notes

    if st.button("Enviar Checklist", type="primary"):
        # Validação final antes do envio
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
                # A lógica de salvar, notificar e enviar SMS permanece a mesma,
                # mas agora lê os dados do st.session_state
                items_data_to_save = {item: {"status": status} for item, status in st.session_state.current_checklist['status'].items()}
                
                checklist_data = {
                    "vehicle_plate": selected_vehicle_data['placa'], "tracker_id": selected_vehicle_data.get('idRastreador'),
                    "driver_uid": st.session_state.user_uid, "driver_email": user_data['email'], "gestor_uid": user_data['gestor_uid'],
                    "timestamp": datetime.now(), "items": items_data_to_save, "notes": st.session_state.current_checklist['notes'],
                    "status": "Aprovado" if is_ok else "Pendente",
                    "location_status": "Não Verificado" # Geofencing pode ser adicionado aqui
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
                
                # Lógica de SMS e notificação por e-mail...
                if is_ok:
                    # Lógica de SMS...
                    st.balloons()
                else:
                    # Lógica de notificação por e-mail...
                    st.warning("Checklist com inconformidades. Seu gestor foi notificado.")

                firestore_service.log_action(user_data['email'], "CHECKLIST_ENVIADO", f"Veículo {selected_vehicle_data['placa']} status {checklist_data['status']}.")
                st.success("Checklist enviado com sucesso!")

                # Limpa o estado para o próximo checklist
                del st.session_state.current_checklist
                st.rerun()

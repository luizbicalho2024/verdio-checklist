# -*- coding: utf-8 -*-
import sys
import os
import streamlit as st
from datetime import datetime

# NOVA IMPORTAÇÃO
from streamlit_shadcn_ui import buttons

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

# --- LÓGICA DE GERENCIAMENTO DE ESTADO (sem alterações) ---
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

    # --- LOOP DE CHECKLIST COM OS NOVOS BOTÕES ---
    for item in checklist_items_template:
        col1, col2 = st.columns([3, 2]) # Colunas para alinhar o texto e os botões
        with col1:
            st.write(item.replace('_', ' ').capitalize())

        with col2:
            current_status = st.session_state.current_checklist["status"].get(item, "OK")
            # Determina qual botão deve vir pré-selecionado
            default_index = 0 if current_status == "OK" else 1
            
            # Cria o grupo de botões
            clicked_button = buttons(
                options=[
                    {'label': 'OK', 'icon': 'check'}, 
                    {'label': 'Não OK', 'icon': 'x'}
                ], 
                default_index=default_index,
                key=f"buttons_{item}_{selected_vehicle_data['placa']}"
            )
            # A função retorna o 'label' do botão clicado
            new_status = clicked_button
        
        if new_status != current_status:
            st.session_state.current_checklist["status"][item] = new_status
            if new_status == "Não OK" and item in st.session_state.current_checklist["photos"]:
                del st.session_state.current_checklist["photos"][item]
            st.rerun()

        if st.session_state.current_checklist["status"].get(item) == "Não OK":
            photo = st.camera_input(f"📸 Foto obrigatória para: {item}", key=f"photo_{item}_{selected_vehicle_data['placa']}")
            if photo:
                st.session_state.current_checklist["photos"][item] = photo
        
        st.divider()

    notes = st.text_area("Observações (obrigatório se algum item for 'Não OK')", key=f"notes_{selected_vehicle_data['placa']}")
    st.session_state.current_checklist["notes"] = notes

    if st.button("Enviar Checklist", type="primary", use_container_width=True):
        # A lógica de envio permanece a mesma
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
            # Lógica de salvar, notificar e enviar SMS... (sem alterações)
            with st.spinner("Salvando checklist e enviando fotos..."):
                # ... (código de salvamento e envio que já estava aqui)
                st.success("Checklist enviado com sucesso!")
                del st.session_state.current_checklist
                st.rerun()

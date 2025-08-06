import sys, os, streamlit as st
sys.path.append(os.getcwd())
from services import firestore_service, etrac_service, twilio_service
from datetime import datetime

st.set_page_config(page_title="Dashboard Motorista", layout="wide")

if not st.session_state.get('logged_in'):
    st.warning("Por favor, faça o login para acessar esta página.")
    st.stop()

user_data = st.session_state.get('user_data', {})
if user_data.get('role') != 'motorista':
    st.error("Acesso negado."); st.stop()

st.title(f"📋 Checklist Pré-Jornada, {user_data.get('email')}")

gestor_data = firestore_service.get_user(user_data.get('gestor_uid', '')) if user_data.get('gestor_uid') else None
etrac_api_key = gestor_data.get('etrac_api_key') if gestor_data else None

if not etrac_api_key:
    st.error("Seu gestor não foi encontrado ou não possui uma chave de API eTrac configurada."); st.stop()

vehicles = etrac_service.get_vehicles_from_etrac(etrac_api_key)
if not vehicles:
    st.warning("Nenhum veículo encontrado para você."); st.stop()

vehicle_options = {f"{v['placa']} - {v['modelo']}": v for v in vehicles}
selected_vehicle_str = st.selectbox("Selecione o Veículo", options=vehicle_options.keys())

if selected_vehicle_str:
    selected_vehicle_data = vehicle_options[selected_vehicle_str]
    st.subheader(f"Itens de Verificação para {selected_vehicle_data['placa']}")
    
    with st.form("checklist_form"):
        checklist_items = {
            "pneus": "Pneus (calibragem e estado)", "luzes": "Sistema de iluminação",
            "freios": "Sistema de freios", "oleo_agua": "Níveis de óleo e água",
            "documentacao": "Documentação", "limpeza": "Limpeza da cabine"
        }
        results = {key: st.radio(desc, ["OK", "Não OK"], horizontal=True) for key, desc in checklist_items.items()}
        notes = st.text_area("Observações (obrigatório se algum item for 'Não OK')")
        
        if st.form_submit_button("Enviar Checklist"):
            is_ok = all(status == "OK" for status in results.values())
            if not is_ok and not notes:
                st.error("Preencha as observações se algum item estiver 'Não OK'.")
            else:
                checklist_data = {
                    "vehicle_id": selected_vehicle_data['idVeiculo'], "vehicle_plate": selected_vehicle_data['placa'],
                    "tracker_id": selected_vehicle_data['idRastreador'], "driver_uid": st.session_state.user_uid,
                    "driver_email": user_data['email'], "gestor_uid": user_data['gestor_uid'],
                    "timestamp": datetime.now(), "items": results, "notes": notes
                }
                
                if is_ok:
                    st.balloons()
                    checklist_data["status"] = "Aprovado"
                    # Lógica para buscar SIM e enviar SMS
                else:
                    st.warning("Checklist com inconformidades. Seu gestor foi notificado.")
                    checklist_data["status"] = "Pendente"
                
                firestore_service.save_checklist(checklist_data)
                firestore_service.log_action(user_data['email'], "CHECKLIST_ENVIADO", f"Veículo {selected_vehicle_data['placa']} status {checklist_data['status']}.")
                st.success("Checklist enviado com sucesso!")

# pages/1_Dashboard_Motorista.py

import streamlit as st
# Removido 'storage_service' das importações
from services import firestore_service, twilio_service, etrac_service
from datetime import datetime

st.set_page_config(page_title="Dashboard do Motorista", layout="wide")

# --- Verificação de Login e Nível de Acesso ---
if not st.session_state.get('logged_in'):
    st.warning("Por favor, faça o login para acessar esta página.")
    st.stop()

user_data = st.session_state.get('user_data', {})
if user_data.get('role') != 'motorista':
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()

st.title("📋 Checklist Pré-Jornada")

# ... (O resto do código para buscar veículos da eTrac continua aqui) ...

# Exemplo de formulário de checklist sem o upload
with st.form("checklist_form"):
    st.write("Marque 'OK' ou 'Não OK' para cada item abaixo.")

    checklist_items = {
        "pneus": "Pneus (calibragem e estado)",
        "luzes": "Sistema de iluminação (faróis, setas, freio)",
        "freios": "Sistema de freios (funcionamento)",
        "oleo_agua": "Níveis de óleo e água",
        "documentacao": "Documentação do veículo e da carga",
        "limpeza": "Limpeza da cabine e do baú"
    }
    
    results = {}
    for key, desc in checklist_items.items():
        results[key] = st.radio(desc, options=["OK", "Não OK"], horizontal=True)
        
    notes = st.text_area("Observações (obrigatório se algum item estiver 'Não OK')")
    
    # REMOVIDO: O st.file_uploader que estava aqui foi removido.
    
    submitted = st.form_submit_button("Enviar Checklist")
    
    if submitted:
        # ... (A lógica de submissão continua a mesma) ...
        # Apenas garanta que a linha `checklist_data["image_urls"] = image_urls`
        # seja removida, pois a variável 'image_urls' não existe mais.
        
        is_ok = all(status == "OK" for status in results.values())
            
        if not is_ok and not notes:
            st.error("É obrigatório preencher as observações se algum item estiver marcado como 'Não OK'.")
        else:
            # Monta o objeto de dados para salvar (sem image_urls)
            checklist_data = {
                # ... (seus outros campos de dados do checklist) ...
                "items": results,
                "notes": notes,
            }
            # ... (resto da lógica para aprovar ou enviar para o gestor) ...

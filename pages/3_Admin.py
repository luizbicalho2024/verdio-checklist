import streamlit as st
import sys
import os
import bcrypt
import pandas as pd
import requests # Para buscar a placa do veículo
import firebase_service as fs
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from services import firestore_service, twilio_service, etrac_service # Agora esta linha funcionará
from datetime import datetime
# --- Verificação de Login e Nível de Acesso ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, faça o login para acessar esta página.")
    st.stop()

if st.session_state['user_role'] != 'admin':
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()

# Função de simulação para buscar um veículo específico (e sua placa) da API eTrac
# Você precisará adaptar esta função com a lógica real da API eTrac
def get_single_vehicle_from_etrac(api_key, vehicle_id):
    """
    Simula uma chamada à API eTrac para buscar um único veículo.
    """
    # Exemplo de URL (substitua pela real)
    # url = f"https://api.etrac.com.br/monitoramento/veiculo/{vehicle_id}?apiKey={api_key}"
    # try:
    #     response = requests.get(url)
    #     response.raise_for_status()
    #     return response.json() 
    # except requests.exceptions.RequestException:
    #     return None
    # Retorno Fixo para fins de demonstração:
    if vehicle_id == "101": return {"idVeiculo": 101, "placa": "BRA-2E19"}
    if vehicle_id == "102": return {"idVeiculo": 102, "placa": "MER-C0SUL"}
    if vehicle_id == "103": return {"idVeiculo": 103, "placa": "TES-T3DPL"}
    return None

# --- Interface da Página Admin ---
st.title("👑 Painel de Administração")
admin_email = st.session_state['user_email']

tab1, tab2, tab3 = st.tabs(["🏢 Cadastro de Gestores", "📲 Cadastro de SIM Cards", "📜 Logs de Auditoria"])

with tab1:
    st.subheader("Gerenciar Gestores")
    with st.form("new_gestor_form", clear_on_submit=True):
        st.write("Cadastre um novo gestor no sistema.")
        gestor_email = st.text_input("Email do Gestor")
        gestor_password = st.text_input("Senha Provisória", type="password")
        gestor_etrac_api_key = st.text_input("Chave da API eTrac do Gestor", type="password")
        
        submitted = st.form_submit_button("Cadastrar Gestor")
        
        if submitted:
            if gestor_email and gestor_password and gestor_etrac_api_key:
                if fs.get_user(gestor_email):
                    st.error("Este email de gestor já está cadastrado.")
                else:
                    # Gera a hash da senha
                    hashed_pw = bcrypt.hashpw(gestor_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    # Cria o usuário gestor
                    fs.create_user(gestor_email, hashed_pw, 'gestor', etrac_api_key=gestor_etrac_api_key)
                    fs.log_action(admin_email, "CADASTRO_GESTOR", f"Gestor {gestor_email} cadastrado.")
                    st.success(f"Gestor {gestor_email} cadastrado com sucesso!")
            else:
                st.warning("Por favor, preencha todos os campos.")

with tab2:
    st.subheader("Associar Veículo ao Número do Chip (SIM Card)")
    st.info("Aqui você associa o ID do Veículo (da API eTrac) ao número de telefone do chip do rastreador que receberá o SMS.")
    
    with st.form("sim_card_form", clear_on_submit=True):
        # Para encontrar o veículo, o Admin precisa da API Key do gestor e do ID do veículo
        gestor_to_configure = st.text_input("Email do Gestor dono do veículo")
        vehicle_id_etrac = st.text_input("ID do Veículo na eTrac")
        tracker_sim_number = st.text_input("Número do Chip com código do país (Ex: +5511999998888)")
        
        submitted = st.form_submit_button("Salvar Associação")
        
        if submitted:
            if gestor_to_configure and vehicle_id_etrac and tracker_sim_number:
                gestor_data = fs.get_user(gestor_to_configure)
                if not gestor_data or gestor_data['role'] != 'gestor':
                    st.error("Nenhum gestor encontrado com este email.")
                else:
                    api_key = gestor_data.get('etrac_api_key')
                    # Busca o veículo na API para confirmar que existe e pegar a placa
                    vehicle_data = get_single_vehicle_from_etrac(api_key, vehicle_id_etrac)
                    if not vehicle_data:
                        st.error(f"Veículo com ID {vehicle_id_etrac} não encontrado na API eTrac para este gestor.")
                    else:
                        plate = vehicle_data.get('placa', 'PLACA_NAO_ENCONTRADA')
                        fs.set_vehicle_sim_number(vehicle_id_etrac, plate, tracker_sim_number, gestor_to_configure)
                        fs.log_action(admin_email, "CADASTRO_SIM", f"SIM {tracker_sim_number} associado ao veículo ID {vehicle_id_etrac} (Placa: {plate}).")
                        st.success(f"Número {tracker_sim_number} associado com sucesso ao veículo {plate}!")
            else:
                st.warning("Por favor, preencha todos os campos.")

with tab3:
    st.subheader("Visualizador de Logs do Sistema")
    
    logs_ref = fs.db.collection("logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(100).stream()
    
    all_logs = [log.to_dict() for log in logs_ref]
    
    if not all_logs:
        st.write("Nenhum log encontrado.")
    else:
        df_logs = pd.DataFrame(all_logs)
        df_logs_display = df_logs[['timestamp', 'user', 'action', 'details']]
        df_logs_display = df_logs_display.rename(columns={
            'timestamp': 'Data', 'user': 'Usuário', 'action': 'Ação', 'details': 'Detalhes'
        })
        st.dataframe(df_logs_display, use_container_width=True)

import streamlit as st
import sys
import os
import bcrypt
import pandas as pd
from twilio.rest import Client
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

if st.session_state['user_role'] != 'gestor':
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()
    
# Função para enviar SMS (reutilizada aqui para o gestor)
def send_unlock_sms(to_number, tracker_id, approver_email):
    """
    Envia o comando de desbloqueio via SMS usando Twilio.
    """
    try:
        # Carrega as credenciais do Twilio
        account_sid = st.secrets["twilio_credentials"]["account_sid"]
        auth_token = st.secrets["twilio_credentials"]["auth_token"]
        from_number = st.secrets["twilio_credentials"]["from_number"]
        
        # Carrega o template do comando SMS
        command_template = st.secrets["sms_config"]["command_template"]
        sms_body = command_template.format(tracker_id=tracker_id)
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=sms_body,
            from_=from_number,
            to=to_number
        )
        st.success(f"Comando de desbloqueio enviado para o número {to_number}. SID: {message.sid}")
        fs.log_action(approver_email, "SMS_DESBLOQUEIO_MANUAL", f"Comando enviado para rastreador {tracker_id} no número {to_number}")
        return True
    except Exception as e:
        st.error(f"Falha ao enviar SMS: {e}")
        fs.log_action(approver_email, "ERRO_SMS", f"Falha ao enviar para rastreador {tracker_id}: {e}")
        return False

# --- Interface da Página do Gestor ---
st.title("📊 Painel do Gestor")

gestor_email = st.session_state['user_email']

tab1, tab2, tab3 = st.tabs(["⚠️ Aprovações Pendentes", "📋 Histórico de Checklists", "👤 Cadastro de Motoristas"])

with tab1:
    st.subheader("Checklists Pendentes de Aprovação")
    
    pending_checklists = fs.get_pending_checklists(gestor_email)
    
    if not pending_checklists:
        st.success("Nenhum checklist pendente no momento.")
    else:
        st.info(f"Você tem {len(pending_checklists)} checklist(s) aguardando sua ação.")
        
        for checklist in pending_checklists:
            # Usamos o timestamp como um ID único para o expander e ações
            checklist_id = checklist['timestamp'] 
            
            with st.expander(f"Veículo: {checklist['vehicle_plate']} | Motorista: {checklist['driver_id']}"):
                st.write(f"**Data:** {checklist_id.strftime('%d/%m/%Y %H:%M')}")
                st.write("**Observações do Motorista:**")
                st.warning(checklist['notes'])
                
                st.write("**Itens do Checklist:**")
                # Exibe os itens que não estão OK
                for item, status in checklist['items'].items():
                    if status != "OK":
                        st.text(f" - {item.replace('_', ' ').capitalize()}: {status}")

                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Aprovar e Liberar Veículo", key=f"approve_{checklist_id}", type="primary"):
                        sim_number = fs.get_vehicle_sim_number(checklist['vehicle_id'])
                        if not sim_number:
                            st.error(f"Não é possível liberar: O número do chip para o veículo {checklist['vehicle_plate']} não está cadastrado. Vá ao painel Admin para cadastrar.")
                        else:
                            # Envia o SMS de desbloqueio
                            send_unlock_sms(sim_number, checklist['tracker_id'], gestor_email)
                            # Atualiza o status do checklist
                            fs.update_checklist_status(checklist_id, "Aprovado pelo Gestor", gestor_email)
                            fs.log_action(gestor_email, "APROVACAO_CHECKLIST", f"Checklist do veículo {checklist['vehicle_plate']} aprovado manualmente.")
                            st.success("Veículo liberado! A lista será atualizada.")
                            st.rerun()

                with col2:
                    if st.button("Reprovar e Bloquear Jornada", key=f"reject_{checklist_id}"):
                        fs.update_checklist_status(checklist_id, "Reprovado pelo Gestor", gestor_email)
                        fs.log_action(gestor_email, "REPROVACAO_CHECKLIST", f"Checklist do veículo {checklist['vehicle_plate']} reprovado.")
                        st.error("Jornada reprovada! O motorista será notificado. A lista será atualizada.")
                        st.rerun()

with tab2:
    st.subheader("Histórico Completo de Checklists")
    all_checklists = fs.get_all_checklists_for_gestor(gestor_email)
    if not all_checklists:
        st.write("Nenhum checklist encontrado no histórico.")
    else:
        # Converte para DataFrame do Pandas para fácil visualização
        df = pd.DataFrame(all_checklists)
        # Formatação e seleção de colunas
        df_display = df[['timestamp', 'vehicle_plate', 'driver_id', 'status', 'notes']]
        df_display = df_display.rename(columns={
            'timestamp': 'Data', 'vehicle_plate': 'Placa', 'driver_id': 'Motorista', 'status': 'Status', 'notes': 'Observações'
        })
        st.dataframe(df_display, use_container_width=True)

with tab3:
    st.subheader("Gerenciar Motoristas")
    with st.form("new_driver_form", clear_on_submit=True):
        st.write("Cadastre um novo motorista para sua equipe.")
        driver_email = st.text_input("Email do Motorista")
        driver_password = st.text_input("Senha Provisória", type="password")
        
        submitted = st.form_submit_button("Cadastrar Motorista")
        
        if submitted:
            if driver_email and driver_password:
                if fs.get_user(driver_email):
                    st.error("Este email de motorista já está cadastrado.")
                else:
                    # Gera a hash da senha
                    hashed_pw = bcrypt.hashpw(driver_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    # Cria o usuário
                    fs.create_user(driver_email, hashed_pw, 'motorista', gestor_id=gestor_email)
                    fs.log_action(gestor_email, "CADASTRO_MOTORISTA", f"Motorista {driver_email} cadastrado.")
                    st.success(f"Motorista {driver_email} cadastrado com sucesso!")
            else:
                st.warning("Por favor, preencha todos os campos.")

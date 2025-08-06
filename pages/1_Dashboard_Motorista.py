import streamlit as st
from datetime import datetime
import requests # Para fazer a chamada à API eTrac
from twilio.rest import Client
import firebase_service as fs

# Função para buscar veículos da API eTrac (SIMULAÇÃO)
# Você precisará adaptar esta função com a lógica real da API eTrac
def get_vehicles_from_etrac(api_key):
    """
    Simula uma chamada à API da eTrac para buscar veículos.
    Substitua esta função pela chamada real à API.
    O retorno esperado é uma lista de dicionários.
    """
    # ---- INÍCIO DO CÓDIGO DE SIMULAÇÃO ----
    # Exemplo de URL da API (substitua pela real)
    # url = f"https://api.etrac.com.br/monitoramento/veiculos?apiKey={api_key}"
    # try:
    #     response = requests.get(url)
    #     response.raise_for_status() # Lança um erro para códigos de status ruins (4xx ou 5xx)
    #     # O formato do retorno abaixo é um exemplo, ajuste conforme a resposta real da API
    #     return response.json() 
    # except requests.exceptions.RequestException as e:
    #     st.error(f"Erro ao buscar veículos da API eTrac: {e}")
    #     return []
    # ---- FIM DO CÓDIGO DE SIMULAÇÃO ----
    
    # Retorno Fixo para fins de demonstração:
    st.info("Usando dados de veículos de demonstração. Adapte a função `get_vehicles_from_etrac` com a chamada real à API.")
    return [
        {"idVeiculo": 101, "placa": "BRA-2E19", "modelo": "Scania R450", "idRastreador": "98765A"},
        {"idVeiculo": 102, "placa": "MER-C0SUL", "modelo": "Volvo FH540", "idRastreador": "98765B"},
        {"idVeiculo": 103, "placa": "TES-T3DPL", "modelo": "DAF XF", "idRastreador": "98765C"},
    ]

# Função para enviar SMS via Twilio
def send_unlock_sms(to_number, tracker_id):
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
        fs.log_action(st.session_state['user_email'], "SMS_DESBLOQUEIO_AUTO", f"Comando enviado para rastreador {tracker_id} no número {to_number}")
        return True
    except Exception as e:
        st.error(f"Falha ao enviar SMS: {e}")
        fs.log_action(st.session_state['user_email'], "ERRO_SMS", f"Falha ao enviar para rastreador {tracker_id}: {e}")
        return False


# --- Verificação de Login e Nível de Acesso ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Por favor, faça o login para acessar esta página.")
    st.stop()

if st.session_state['user_role'] != 'motorista':
    st.error("Você não tem permissão para acessar esta página.")
    st.stop()


# --- Interface da Página do Motorista ---
st.title("📋 Checklist Pré-Jornada")

user_data = st.session_state['user_data']
gestor_data = fs.get_user(user_data['gestor_id'])
if not gestor_data:
    st.error("Não foi possível encontrar os dados do seu gestor. Contate o suporte.")
    st.stop()

# Busca os veículos usando a API Key do gestor associado
etrac_api_key = gestor_data.get("etrac_api_key")
if not etrac_api_key:
    st.error("Seu gestor não possui uma chave de API da eTrac configurada.")
    st.stop()

vehicles = get_vehicles_from_etrac(etrac_api_key)

if not vehicles:
    st.warning("Nenhum veículo encontrado para você.")
    st.stop()

# Formata as opções para o selectbox
vehicle_options = {f"{v['placa']} - {v['modelo']}": v for v in vehicles}
selected_vehicle_str = st.selectbox("Selecione o Veículo", options=vehicle_options.keys())

if selected_vehicle_str:
    selected_vehicle_data = vehicle_options[selected_vehicle_str]
    
    st.subheader(f"Itens de Verificação para {selected_vehicle_data['placa']}")
    
    with st.form("checklist_form"):
        st.write("Marque 'OK' ou 'Não OK' para cada item abaixo.")

        # Itens do Checklist
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
        
        submitted = st.form_submit_button("Enviar Checklist")
        
        if submitted:
            is_ok = all(status == "OK" for status in results.values())
            
            # Validação
            if not is_ok and not notes:
                st.error("É obrigatório preencher as observações se algum item estiver marcado como 'Não OK'.")
            else:
                # Monta o objeto de dados para salvar
                checklist_data = {
                    "vehicle_id": selected_vehicle_data['idVeiculo'],
                    "vehicle_plate": selected_vehicle_data['placa'],
                    "tracker_id": selected_vehicle_data['idRastreador'],
                    "driver_id": st.session_state['user_email'],
                    "gestor_id": user_data['gestor_id'],
                    "timestamp": datetime.now(),
                    "items": results,
                    "notes": notes,
                }
                
                if is_ok:
                    st.balloons()
                    st.success("Checklist em conformidade! Enviando comando de desbloqueio...")
                    checklist_data["status"] = "Aprovado"
                    
                    # Busca o número do SIM para enviar o SMS
                    sim_number = fs.get_vehicle_sim_number(selected_vehicle_data['idVeiculo'])
                    if sim_number:
                        send_unlock_sms(sim_number, selected_vehicle_data['idRastreador'])
                    else:
                        st.error(f"Não foi possível enviar o SMS. O número do chip para o veículo {selected_vehicle_data['placa']} não está cadastrado. Avise seu gestor.")
                        # Mesmo com erro de SMS, o checklist é salvo como pendente para ação manual
                        checklist_data["status"] = "Pendente"
                        checklist_data["notes"] += "\n[SISTEMA] Falha no envio automático de SMS: SIM não cadastrado."

                else:
                    st.warning("Checklist com inconformidades. Seu gestor foi notificado para avaliar e liberar o veículo.")
                    checklist_data["status"] = "Pendente"
                
                # Salva o checklist no Firebase
                fs.save_checklist(checklist_data)
                fs.log_action(st.session_state['user_email'], "CHECKLIST_ENVIADO", f"Checklist para o veículo {selected_vehicle_data['placa']} enviado com status {checklist_data['status']}.")
                st.info("Checklist enviado com sucesso! Esta página será recarregada.")
                # st.rerun() # Opcional: recarregar a página após o envio

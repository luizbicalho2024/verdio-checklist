# -*- coding: utf-8 -*-
import streamlit as st
from twilio.rest import Client
from . import firestore_service # Importamos para logar a ação

def send_unlock_sms(to_number, equipamento_serial, admin_email_logger):
    """Envia o comando de desbloqueio via SMS usando Twilio."""
    try:
        creds = st.secrets["twilio_credentials"]
        command_template = st.secrets["sms_config"]["command_template"]
        
        # Formata o comando com o serial do equipamento
        sms_body = command_template.format(equipamento_serial=equipamento_serial)
        
        client = Client(creds["account_sid"], creds["auth_token"])
        message = client.messages.create(body=sms_body, from_=creds["from_number"], to=to_number)
        
        st.success(f"Comando de desbloqueio enviado para o número {to_number}.")
        firestore_service.log_action(admin_email_logger, "SMS_DESBLOQUEIO_AUTO", f"Comando '{sms_body}' enviado para {to_number}.")
        return True
    except Exception as e:
        st.error(f"Falha ao enviar SMS: {e}")
        firestore_service.log_action(admin_email_logger, "ERRO_SMS", f"Falha ao enviar comando para {to_number}: {e}")
        return False

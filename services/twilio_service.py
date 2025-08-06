import streamlit as st
from twilio.rest import Client

def send_unlock_sms(to_number, tracker_id):
    try:
        creds = st.secrets["twilio_credentials"]
        command_template = st.secrets["sms_config"]["command_template"]
        sms_body = command_template.format(tracker_id=tracker_id)
        
        client = Client(creds["account_sid"], creds["auth_token"])
        message = client.messages.create(body=sms_body, from_=creds["from_number"], to=to_number)
        st.success(f"Comando de desbloqueio enviado para {to_number}. SID: {message.sid}")
        return True
    except Exception as e:
        st.error(f"Falha ao enviar SMS: {e}")
        return False

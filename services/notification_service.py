# -*- coding: utf-8 -*-
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_notification(to_email, subject, body_html):
    """Envia uma notificação por e-mail."""
    try:
        creds = st.secrets["email_credentials"]
        sender_email = creds["sender_email"]
        password = creds["sender_password"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body_html, 'html'))
        
        with smtplib.SMTP(creds["smtp_server"], creds["smtp_port"]) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        
        return True
    except Exception as e:
        # Em produção, seria bom logar esse erro em vez de mostrá-lo na UI principal
        print(f"Falha ao enviar e-mail de notificação: {e}")
        return False

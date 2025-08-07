# -*- coding: utf-8 -*-
import streamlit as st
from services import auth_service, firestore_service
from utils import qr_code_util

st.set_page_config(page_title="Login - Checklist App", layout="centered")

def handle_login(email, password):
    user_record = auth_service.verify_user_password(email, password)
    if user_record:
        st.session_state['pending_login_uid'] = user_record['uid']
        st.session_state['flow'] = 'verify_2fa'
        st.rerun()
    else:
        st.error("Email ou senha inválidos.")

def handle_2fa_verification(uid, code):
    if auth_service.verify_totp_code(uid, code):
        st.session_state['logged_in'] = True
        st.session_state['user_uid'] = uid
        st.session_state['user_data'] = firestore_service.get_user(uid)
        st.session_state['flow'] = 'logged_in'
        # Não redirecionamos aqui, apenas preparamos o estado. O rerun fará o resto.
        st.rerun()
    else:
        st.error("Código 2FA inválido.")

def handle_registration(email, password):
    if firestore_service.get_user_by_email(email):
        st.error("Este email já está registrado.")
        return
    user = auth_service.create_user_with_password(email, password, role='motorista')
    if user:
        st.success("Registro bem-sucedido! Faça o login.")
        st.session_state['flow'] = 'login'
        st.rerun()

def enable_2fa_flow():
    uid = st.session_state['user_uid']
    email = st.session_state['user_data']['email']
    if 'totp_secret_temp' not in st.session_state:
        st.session_state['totp_secret_temp'] = auth_service.generate_totp_secret()
    secret = st.session_state['totp_secret_temp']
    uri = auth_service.get_totp_uri(email, secret)
    qr_image = qr_code_util.generate_qr_code_image(uri)
    st.subheader("Configure seu App Autenticador")
    st.image(qr_image)
    st.code(f"Chave manual: {secret}")
    with st.form("verify_2fa_setup"):
        verification_code = st.text_input("Insira o código de 6 dígitos para confirmar", max_chars=6)
        if st.form_submit_button("Ativar 2FA"):
            if auth_service.verify_totp_code_with_secret(secret, verification_code):
                auth_service.enable_user_totp(uid, secret)
                st.session_state.user_data['totp_enabled'] = True
                del st.session_state['totp_secret_temp']
                st.success("2FA ativado com sucesso!")
                st.session_state['flow'] = 'logged_in'
                st.rerun()
            else:
                st.error("Código de verificação inválido.")

# --- Roteador de Fluxo ---
if 'flow' not in st.session_state:
    st.session_state['flow'] = 'login'

# Se o usuário já está logado e acessa a página principal, redireciona-o
if st.session_state.get('logged_in') and st.session_state.get('flow') != 'logged_in':
    st.session_state['flow'] = 'logged_in'

if st.session_state['flow'] == 'login':
    st.title("Login do Sistema de Checklist")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            handle_login(email, password)
    if st.button("Não tem uma conta? Registre-se"):
        st.session_state['flow'] = 'register'
        st.rerun()

elif st.session_state['flow'] == 'register':
    st.title("Registro de Novo Usuário")
    with st.form("register_form"):
        reg_email = st.text_input("Seu Email")
        reg_password = st.text_input("Crie uma Senha", type="password")
        if st.form_submit_button("Registrar"):
            if reg_email and reg_password:
                handle_registration(reg_email, reg_password)
            else:
                st.warning("Preencha todos os campos.")
    if st.button("Já tem uma conta? Faça o login"):
        st.session_state['flow'] = 'login'
        st.rerun()

elif st.session_state['flow'] == 'verify_2fa':
    uid = st.session_state.get('pending_login_uid')
    if not uid:
        st.session_state['flow'] = 'login'
        st.rerun()
    if auth_service.is_totp_enabled(uid):
        st.title("Verificação de Dois Fatores")
        code = st.text_input("Insira o código do seu app autenticador", max_chars=6)
        if st.button("Verificar"):
            handle_2fa_verification(uid, code)
    else:
        st.session_state.update({'logged_in': True, 'user_uid': uid, 'user_data': firestore_service.get_user(uid), 'flow': 'logged_in'})
        st.rerun()

# --- BLOCO DE CÓDIGO ALTERADO ---
elif st.session_state['flow'] == 'logged_in':
    # Em vez de mostrar uma mensagem de boas-vindas aqui,
    # verificamos se o redirecionamento já foi feito.
    if 'redirected' not in st.session_state:
        st.session_state['redirected'] = True
        role = st.session_state.user_data.get('role')

        # Redireciona com base no papel do usuário
        if role == 'motorista':
            st.switch_page("pages/1_Dashboard_Motorista.py")
        elif role == 'gestor':
            st.switch_page("pages/2_Painel_Gestor.py")
        elif role == 'admin':
            st.switch_page("pages/3_Admin.py")
        else:
            st.error("Papel de usuário desconhecido. Contate o suporte.")
            if st.button("Sair"):
                st.session_state.clear(); st.session_state['flow'] = 'login'; st.rerun()
    
    # Se o usuário já foi redirecionado e voltou para a página inicial,
    # mostramos o painel de logout e 2FA.
    else:
        user_data = st.session_state.user_data
        st.title(f"Bem-vindo(a), {user_data.get('email', '')}!")
        st.info("Você já está logado. Use o menu à esquerda para navegar.")
        if not user_data.get('totp_enabled'):
            if st.button("🔒 Ativar Autenticação de Dois Fatores"):
                st.session_state['flow'] = 'enable_2fa'
                st.rerun()
        if st.button("Sair"):
            st.session_state.clear()
            st.session_state['flow'] = 'login'
            st.rerun()
# --- FIM DO BLOCO ALTERADO ---

elif st.session_state['flow'] == 'enable_2fa':
    enable_2fa_flow()

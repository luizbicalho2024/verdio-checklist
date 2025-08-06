import streamlit as st
from firebase_admin import auth

# Importa os novos serviços e utilitários
from services import auth_service, firestore_service
from utils import qr_code_util

st.set_page_config(page_title="Login - Checklist App", layout="centered")

def handle_login(email, password):
    try:
        user = auth.get_user_by_email(email)
        # NOTA: Como o Admin SDK não verifica senhas, esta etapa é conceitual.
        # Em um app real com cliente, a verificação aconteceria antes.
        # Aqui, prosseguimos para a verificação 2FA.
        st.session_state['pending_login_uid'] = user.uid
        st.session_state['flow'] = 'verify_2fa'
        st.rerun()
    except Exception:
        st.error("Email ou senha inválidos. (Simulação de verificação)")

def handle_2fa_verification(uid, code):
    if auth_service.verify_totp_code(uid, code):
        st.session_state['logged_in'] = True
        st.session_state['user_uid'] = uid
        user_data = firestore_service.get_user(uid)
        st.session_state['user_data'] = user_data
        st.session_state['flow'] = 'logged_in'
        st.success("Login bem-sucedido!")
        st.rerun()
    else:
        st.error("Código 2FA inválido.")

def handle_registration(email, password):
    # Cria o usuário como motorista por padrão. A promoção para gestor é feita pelo admin.
    user = auth_service.create_firebase_user(email, password, role='motorista')
    if user:
        st.success("Registro bem-sucedido! Faça o login.")
        st.session_state['flow'] = 'login'
        st.rerun()

def enable_2fa_flow(uid):
    secret = auth_service.generate_totp_secret()
    st.session_state['totp_secret_temp'] = secret
    uri = auth_service.get_totp_uri(st.session_state['user_data']['email'], secret)
    qr_image = qr_code_util.generate_qr_code_image(uri)
    
    st.subheader("Configure seu App Autenticador")
    st.write("1. Abra o Google Authenticator (ou similar).")
    st.write("2. Escaneie o QR Code abaixo:")
    st.image(qr_image)
    st.write("3. Insira o código gerado para confirmar:")
    
    verification_code = st.text_input("Código de Verificação 2FA")
    if st.button("Ativar 2FA"):
        if auth_service.verify_totp_code_with_secret(secret, verification_code): # Função auxiliar necessária
            auth_service.enable_user_totp(uid, secret)
            st.success("2FA ativado com sucesso!")
            st.session_state['flow'] = 'logged_in'
            st.rerun()
        else:
            st.error("Código de verificação inválido.")


# --- Lógica de Fluxo da Página ---

# Inicializa o estado da sessão
if 'flow' not in st.session_state:
    st.session_state['flow'] = 'login'

# Roteador de Fluxo
if st.session_state['flow'] == 'login':
    st.title("Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            handle_login(email, password)
    
    if st.button("Não tem uma conta? Registre-se"):
        st.session_state['flow'] = 'register'
        st.rerun()

elif st.session_state['flow'] == 'register':
    st.title("Registro de Novo Usuário")
    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Registrar")
        if submitted:
            handle_registration(email, password)
            
    if st.button("Já tem uma conta? Faça o login"):
        st.session_state['flow'] = 'login'
        st.rerun()

elif st.session_state['flow'] == 'verify_2fa':
    st.title("Verificação de Dois Fatores")
    uid = st.session_state['pending_login_uid']
    if auth_service.is_totp_enabled(uid):
        code = st.text_input("Insira o código do seu app autenticador")
        if st.button("Verificar"):
            handle_2fa_verification(uid, code)
    else:
        # Se 2FA não estiver ativo, loga o usuário diretamente
        st.session_state['logged_in'] = True
        st.session_state['user_uid'] = uid
        st.session_state['user_data'] = firestore_service.get_user(uid)
        st.session_state['flow'] = 'logged_in'
        st.success("Login bem-sucedido!")
        st.rerun()

elif st.session_state['flow'] == 'logged_in':
    st.title("Bem-vindo(a)!")
    user_data = st.session_state['user_data']
    st.write(f"Logado como: {user_data['email']}")
    st.write(f"Papel: {user_data['role'].capitalize()}")
    st.info("Navegue para seu dashboard no menu à esquerda.")

    # Opção para ativar 2FA
    if not user_data.get('totp_enabled'):
        if st.button("Ativar Autenticação de Dois Fatores (2FA)"):
            st.session_state['flow'] = 'enable_2fa'
            st.rerun()

    if st.button("Sair"):
        st.session_state.clear()
        st.session_state['flow'] = 'login'
        st.rerun()

elif st.session_state['flow'] == 'enable_2fa':
    enable_2fa_flow(st.session_state['user_uid'])

import streamlit as st
from firebase_admin import credentials

st.set_page_config(page_title="Verificador Final", layout="centered")
st.header("🕵️ Verificador Final de Segredos do Firebase")

# 1. Verifica se a seção de segredos existe
if "firebase_credentials" in st.secrets:
    st.success("Passo 1: A seção `[firebase_credentials]` foi encontrada no secrets.toml.")
    
    creds_from_secrets = st.secrets["firebase_credentials"]
    
    # 2. Verifica o tipo de dado lido pelo Streamlit
    st.write(f"Passo 2: O tipo de dado lido pelo Streamlit é: **{type(creds_from_secrets)}**.")

    # 3. Tenta converter para um dicionário puro (a correção principal)
    try:
        dict_creds = dict(creds_from_secrets)
        st.success("Passo 3: Conversão para dicionário puro bem-sucedida.")
        
        # 4. Tenta inicializar o objeto de credenciais do Firebase
        try:
            creds_object = credentials.Certificate(dict_creds)
            st.success("✅ SUCESSO TOTAL! O objeto de credenciais do Firebase foi criado com sucesso.")
            st.balloons()
            st.info("Pode reverter o app.py para o código da aplicação e tudo deve funcionar.")
            
        except Exception as e:
            st.error("❌ ERRO FINAL: Falha ao criar o objeto de credenciais do Firebase.")
            st.write("A biblioteca do Firebase retornou o seguinte erro detalhado:")
            st.exception(e) # Mostra o erro exato do Firebase
            
    except Exception as e:
        st.error("❌ ERRO CRÍTICO: Falha ao converter os segredos para um dicionário.")
        st.write("Isso quase certamente significa um erro de sintaxe no seu arquivo `secrets.toml`.")
        st.exception(e)

else:
    st.error("❌ ERRO GRAVE: A seção `[firebase_credentials]` não foi encontrada.")
    st.write("Verifique se o nome do cabeçalho no seu `secrets.toml` está escrito exatamente assim: `[firebase_credentials]`")

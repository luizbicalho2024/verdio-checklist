import streamlit as st

st.header("🕵️ Verificador de Segredos")

# Verifica se a seção existe
if "firebase_credentials" in st.secrets:
    creds = st.secrets["firebase_credentials"]
    
    st.success("A seção [firebase_credentials] foi encontrada!")
    
    # Verifica se o tipo é um dicionário
    st.write(f"O tipo de dado lido é: **{type(creds)}**")

    if isinstance(creds, dict):
        st.success("✅ Excelente! O segredo foi lido como um dicionário.")
        st.write("Conteúdo lido (parcial):")
        # st.json exibe o dicionário de forma legível
        st.json({k: v for k, v in creds.items() if k != 'private_key'})
    else:
        st.error("❌ Erro! O segredo NÃO foi lido como um dicionário. Verifique a formatação do seu secrets.toml, especialmente o cabeçalho `[firebase_credentials]`.")

else:
    st.error("❌ Erro! A seção `[firebase_credentials]` não foi encontrada no seu arquivo de segredos. Verifique se o nome está correto.")

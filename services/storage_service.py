import streamlit as st
from firebase_admin import storage
from uuid import uuid4

def upload_file_to_storage(file, user_uid):
    """
    Faz upload de um arquivo para o Firebase Storage e retorna a URL pública.
    """
    if file is None:
        return None
    try:
        # Pega o bucket padrão do Firebase Storage
        bucket = storage.bucket()
        
        # Gera um nome de arquivo único para evitar conflitos
        file_extension = file.name.split('.')[-1]
        file_name = f"checklists/{user_uid}/{uuid4()}.{file_extension}"
        
        # Cria um blob (objeto) no bucket
        blob = bucket.blob(file_name)
        
        # Faz o upload do conteúdo do arquivo
        blob.upload_from_file(file, content_type=file.type)
        
        # Torna o arquivo publicamente acessível (você pode querer usar URLs assinadas para mais segurança)
        blob.make_public()
        
        return blob.public_url
    except Exception as e:
        st.error(f"Erro no upload da imagem: {e}")
        return None

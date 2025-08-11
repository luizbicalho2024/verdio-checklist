# -*- coding: utf-8 -*-
import streamlit as st
from firebase_admin import storage
from uuid import uuid4

def upload_file(file, destination_path):
    """
    Faz upload de um objeto de arquivo para o Firebase Storage.
    
    Args:
        file: O objeto de arquivo (do st.camera_input).
        destination_path: O caminho no Storage onde o arquivo será salvo.

    Returns:
        A URL pública do arquivo enviado ou None se falhar.
    """
    if file is None:
        return None
    try:
        bucket = storage.bucket()
        blob = bucket.blob(destination_path)
        
        # O st.camera_input retorna um objeto BytesIO, então usamos upload_from_file
        file.seek(0)
        blob.upload_from_file(file, content_type='image/jpeg')
        
        # Torna o arquivo publicamente acessível
        blob.make_public()
        
        return blob.public_url
    except Exception as e:
        st.error(f"Erro no upload do arquivo: {e}")
        return None

# -*- coding: utf-8 -*-
# Este arquivo gerencia a comunicação com a API da eTrac.
import streamlit as st
import requests

def get_vehicles_from_etrac(api_key):
    """
    Busca os veículos de um cliente na API da eTrac usando a chave fornecida.
    """
    # A URL base da API. Verifique na documentação se esta é a URL correta.
    # A documentação que você forneceu (https://api.etrac.com.br/monitoramento/doc)
    # sugere que a URL para obter os veículos é esta.
    url = "https://api.etrac.com.br/monitoramento/veiculos"
    
    # Os parâmetros da requisição, incluindo a chave da API.
    params = {
        'apiKey': api_key
    }
    
    try:
        # Faz a requisição GET para a API com um timeout de 10 segundos.
        response = requests.get(url, params=params, timeout=10)
        
        # Lança um erro para respostas com códigos de erro HTTP (4xx ou 5xx).
        # Se a chave da API for inválida, por exemplo, isso irá gerar um erro 401.
        response.raise_for_status()
        
        # Retorna a lista de veículos em formato JSON.
        # A API deve retornar uma lista de dicionários. Ex: [{'placa': 'ABC-1234', ...}]
        vehicles = response.json()
        
        if not vehicles:
            st.warning("A API eTrac não retornou veículos para a chave fornecida.")
            return []
            
        return vehicles

    except requests.exceptions.HTTPError as http_err:
        # Erros específicos de HTTP (como 401 Não Autorizado, 404 Não Encontrado)
        if response.status_code == 401:
            st.error("Erro de Autenticação com a API eTrac: A chave da API é inválida ou expirou.")
        else:
            st.error(f"Erro HTTP ao buscar veículos da eTrac: {http_err}")
        return []
        
    except requests.exceptions.RequestException as e:
        # Erros gerais de rede (falha de conexão, timeout, etc.)
        st.error(f"Erro de conexão com a API eTrac: {e}")
        return []

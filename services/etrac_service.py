# -*- coding: utf-8 -*-
import streamlit as st
import requests

def get_vehicles_from_etrac(email, api_key):
    """
    Busca as últimas posições da frota (que contém os dados dos veículos)
    usando o método POST e Basic Auth.
    """
    # Novo endpoint correto
    url = "http://api.etrac.com.br/monitoramento/ultimas-posicoes"
    
    st.info(f"Conectando à eTrac com o usuário: {email}...")
    
    try:
        # Faz a requisição POST. A autenticação Basic Auth é feita passando uma tupla (username, password) para o parâmetro `auth`.
        response = requests.post(url, auth=(email, api_key), timeout=15)
        
        # Lança um erro para respostas com códigos de erro HTTP (4xx ou 5xx).
        response.raise_for_status()
        
        # A API retorna uma lista de dicionários, um para cada veículo.
        vehicle_data = response.json()
        
        if not vehicle_data:
            st.warning("A API eTrac não retornou veículos para estas credenciais.")
            return []
            
        # Opcional: Extrair apenas os campos que precisamos para evitar carregar dados demais.
        # Vamos assumir que o retorno tem 'placa' e 'modelo' para o dropdown.
        # Adicione outros campos que vierem da API se precisar deles.
        simplified_vehicles = []
        for vehicle in vehicle_data:
            simplified_vehicles.append({
                'placa': vehicle.get('placa'),
                'modelo': vehicle.get('modelo', 'Modelo não informado'), # Exemplo com valor padrão
                'idRastreador': vehicle.get('idRastreador') # Supondo que este campo exista
            })
            
        return simplified_vehicles

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401:
            st.error("Erro de Autenticação com a API eTrac: O e-mail ou a chave da API estão incorretos.")
        else:
            st.error(f"Erro HTTP ao buscar veículos da eTrac: {http_err}")
        return []
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão com a API eTrac: {e}")
        return []

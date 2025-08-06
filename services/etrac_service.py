# -*- coding: utf-8 -*-
# Este arquivo gerencia a comunicação com a API da eTrac.
import streamlit as st
import requests

def get_vehicles_from_etrac(email, api_key):
    """
    Busca as últimas posições da frota (que contém os dados dos veículos)
    usando o método POST e Basic Auth, e processa a resposta JSON corretamente.
    """
    url = "http://api.etrac.com.br/monitoramento/ultimas-posicoes"
    
    st.info(f"Conectando à eTrac com o usuário: {email}...")
    
    try:
        # Faz a requisição POST com autenticação Basic Auth e um timeout de 15 segundos.
        response = requests.post(url, auth=(email, api_key), timeout=15)
        
        # Lança um erro para respostas com códigos de erro HTTP (4xx ou 5xx).
        response.raise_for_status()
        
        # A API retorna uma lista de dicionários.
        vehicle_list_from_api = response.json()
        
        if not vehicle_list_from_api:
            st.warning("A API eTrac não retornou veículos para estas credenciais.")
            return []
        
        # --- LÓGICA DE PROCESSAMENTO CORRIGIDA ---
        # Itera sobre a lista de veículos retornada pela API.
        simplified_vehicles = []
        for vehicle_data in vehicle_list_from_api:
            # Garante que estamos lidando com um dicionário antes de extrair os dados.
            if isinstance(vehicle_data, dict):
                simplified_vehicles.append({
                    # Mapeia os campos da API para os campos que nossa aplicação espera.
                    'placa': vehicle_data.get('placa'),
                    'modelo': vehicle_data.get('descricao', 'Modelo não informado'), # Usamos 'descricao' como 'modelo'
                    'idRastreador': vehicle_data.get('equipamento_serial') # Usamos 'equipamento_serial' como 'idRastreador'
                })
            
        st.success(f"{len(simplified_vehicles)} veículos carregados com sucesso da eTrac!")
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
    except ValueError:
        # Erro caso a resposta da API não seja um JSON válido.
        st.error("A API da eTrac retornou uma resposta inesperada que não é um JSON válido.")
        st.code(response.text) # Mostra o texto cru da resposta para depuração
        return []

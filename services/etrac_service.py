# -*- coding: utf-8 -*-
# Este arquivo gerencia a comunicação com a API da eTrac.
import streamlit as st
import requests

def get_vehicles_from_etrac(email, api_key):
    """
    Busca as últimas posições da frota, processando corretamente a chave "retorno" da resposta JSON.
    """
    url = "http://api.etrac.com.br/monitoramento/ultimas-posicoes"
    
    st.info(f"Conectando à eTrac com o usuário: {email}...")
    
    try:
        response = requests.post(url, auth=(email, api_key), timeout=15)
        response.raise_for_status()
        
        # Pega o objeto JSON completo da resposta.
        response_data = response.json()
        
        # --- CORREÇÃO PRINCIPAL APLICADA AQUI ---
        # Acessa a lista de veículos que está DENTRO da chave "retorno".
        vehicle_list_from_api = response_data.get('retorno')
        
        # Verifica se a chave "retorno" existe e se é uma lista.
        if not vehicle_list_from_api or not isinstance(vehicle_list_from_api, list):
            st.warning("A API eTrac não retornou uma lista de veículos válida.")
            # Opcional: mostrar o erro retornado pela API, se houver.
            if response_data.get("erro"):
                st.error(f"Erro da API: {response_data.get('erro')}")
            return []
        
        # Itera sobre a lista de veículos retornada pela API.
        simplified_vehicles = []
        for vehicle_data in vehicle_list_from_api:
            if isinstance(vehicle_data, dict):
                simplified_vehicles.append({
                    'placa': vehicle_data.get('placa'),
                    'modelo': vehicle_data.get('descricao', 'Modelo não informado'),
                    'idRastreador': vehicle_data.get('equipamento_serial')
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
        st.error("A API da eTrac retornou uma resposta inesperada que não é um JSON válido.")
        st.code(response.text)
        return []

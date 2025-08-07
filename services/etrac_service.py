# -*- coding: utf-8 -*-
import streamlit as st
import requests

def get_vehicles_from_etrac(email, api_key):
    """Busca as últimas posições da frota completa."""
    url = "http://api.etrac.com.br/monitoramento/ultimas-posicoes"
    try:
        response = requests.post(url, auth=(email, api_key), timeout=15)
        response.raise_for_status()
        response_data = response.json()
        vehicle_list = response_data.get('retorno')
        if not vehicle_list or not isinstance(vehicle_list, list):
            if response_data.get("erro"): st.error(f"Erro da API: {response_data.get('erro')}")
            return []
        return vehicle_list
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 401: st.error("Erro de Autenticação com a API eTrac: Credenciais inválidas.")
        else: st.error(f"Erro HTTP ao buscar frota: {http_err}")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão com a API eTrac: {e}")
        return []
    except ValueError:
        st.error("A API da eTrac retornou uma resposta inesperada (não-JSON).")
        return []

def get_single_vehicle_position(email, api_key, plate):
    """Busca a última posição de um único veículo."""
    url = "http://api.etrac.com.br/monitoramento/ultimaposicao"
    try:
        response = requests.post(url, auth=(email, api_key), json={"placa": plate}, timeout=10)
        response.raise_for_status()
        response_data = response.json()
        # A resposta para um único veículo pode não estar aninhada
        return response_data.get('retorno', [response_data])[0]
    except Exception:
        return None # Retorna None em caso de qualquer erro

def get_trip_summary(email, api_key, plate, date):
    """Busca o resumo de viagens de um veículo para uma data específica."""
    url = "http://api.etrac.com.br/monitoramento/resumoviagens"
    formatted_date = date.strftime("%d-%m-%Y")
    try:
        response = requests.post(url, auth=(email, api_key), json={"placa": plate, "data": formatted_date}, timeout=20)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get('conducoes', [])
    except Exception as e:
        st.error(f"Não foi possível buscar o resumo de viagens: {e}")
        return []

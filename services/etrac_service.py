import streamlit as st
import requests

def get_vehicles_from_etrac(api_key):
    st.info("Usando dados de veículos de demonstração. Substitua pela chamada real à API eTrac.")
    # A LÓGICA REAL DA SUA API DEVE VIR AQUI
    # Exemplo:
    # try:
    #     url = f"https://api.etrac.com.br/monitoramento/veiculos?apiKey={api_key}"
    #     response = requests.get(url, timeout=10)
    #     response.raise_for_status()
    #     return response.json()
    # except requests.RequestException as e:
    #     st.error(f"Erro ao conectar com a API eTrac: {e}")
    #     return []
    
    # Dados de simulação:
    return [
        {"idVeiculo": 101, "placa": "BRA-2E19", "modelo": "Scania R450", "idRastreador": "98765A"},
        {"idVeiculo": 102, "placa": "MER-C0SUL", "modelo": "Volvo FH540", "idRastreador": "98765B"},
    ]

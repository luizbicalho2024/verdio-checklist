import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Função para inicializar o Firebase. Usa st.cache_resource para garantir que seja executado apenas uma vez.
@st.cache_resource
def initialize_firebase():
    """
    Inicializa a conexão com o Firebase usando as credenciais do Streamlit Secrets.
    Retorna a instância do cliente Firestore.
    """
    try:
        # Verifica se o app já foi inicializado
        firebase_admin.get_app()
    except ValueError:
        # Carrega as credenciais do arquivo secrets.toml
        creds_dict = st.secrets["firebase_credentials"]
        creds = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(creds)
    
    return firestore.client()

# Instancia o cliente do Firestore
db = initialize_firebase()

# --- Funções de Log ---
def log_action(user_email, action, details):
    """
    Registra uma ação no log de auditoria do Firestore.
    """
    log_data = {
        "timestamp": firestore.SERVER_TIMESTAMP,
        "user": user_email,
        "action": action,
        "details": details
    }
    db.collection("logs").add(log_data)

# --- Funções de Usuário ---
def get_user(email):
    """
    Busca um usuário pelo email.
    """
    user_ref = db.collection("users").document(email).get()
    if user_ref.exists:
        return user_ref.to_dict()
    return None

def create_user(email, password_hash, role, gestor_id=None, etrac_api_key=None):
    """
    Cria um novo usuário no Firestore.
    """
    user_data = {
        "email": email,
        "hashed_password": password_hash,
        "role": role,
    }
    if gestor_id:
        user_data["gestor_id"] = gestor_id
    if etrac_api_key:
        user_data["etrac_api_key"] = etrac_api_key
        
    db.collection("users").document(email).set(user_data)

# --- Funções de Veículo ---
def get_vehicle_sim_number(vehicle_id_etrac):
    """
    Busca o número do SIM card de um veículo pelo seu ID da eTrac.
    """
    # O ID do documento na nossa coleção 'vehicles' é o próprio ID do veículo da eTrac
    vehicle_ref = db.collection("vehicles").document(str(vehicle_id_etrac)).get()
    if vehicle_ref.exists:
        return vehicle_ref.to_dict().get("tracker_sim_number")
    return None

def set_vehicle_sim_number(vehicle_id_etrac, plate, sim_number, gestor_id):
    """
    Cadastra ou atualiza o número do SIM de um veículo.
    """
    vehicle_data = {
        "vehicle_id_etrac": vehicle_id_etrac,
        "plate": plate,
        "tracker_sim_number": sim_number,
        "gestor_id": gestor_id
    }
    # Usamos o ID da eTrac como ID do nosso documento para fácil busca
    db.collection("vehicles").document(str(vehicle_id_etrac)).set(vehicle_data)

# --- Funções de Checklist ---
def save_checklist(data):
    """
    Salva um novo checklist no Firestore.
    """
    db.collection("checklists").add(data)

def get_pending_checklists(gestor_id):
    """
    Busca checklists pendentes para um gestor específico.
    """
    checklists_ref = db.collection("checklists").where("gestor_id", "==", gestor_id).where("status", "==", "Pendente").stream()
    return [checklist.to_dict() for checklist in checklists_ref]
    
def get_all_checklists_for_gestor(gestor_id):
    """
    Busca todos os checklists de um gestor.
    """
    checklists_ref = db.collection("checklists").where("gestor_id", "==", gestor_id).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
    return [checklist.to_dict() for checklist in checklists_ref]


def update_checklist_status(checklist_id, new_status, approved_by):
    """
    Atualiza o status de um checklist (quando o gestor aprova/reprova).
    """
    # Precisamos primeiro encontrar o documento pelo ID do checklist (que não é o ID do documento)
    docs = db.collection('checklists').where('timestamp', '==', checklist_id).limit(1).get()
    if docs:
        doc_id = docs[0].id
        db.collection('checklists').document(doc_id).update({
            'status': new_status,
            'approved_by_gestor': True,
            'approved_by': approved_by
        })
        return True
    return False

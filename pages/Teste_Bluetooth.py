import streamlit as st
import streamlit.components.v1 as components
import os
import time

# --- ETAPA 1: DEFINIR O CÓDIGO DO FRONTEND ---
JS_CODE = """
window.addEventListener('load', function() {
    const Streamlit = window.Streamlit;

    let bleDevice;
    let writeCharacteristic;
    const textEncoder = new TextEncoder();

    function onRender(event) {
      const { serviceUuid, characteristicUuid, command } = event.detail.args;

      let connectButton = document.getElementById("connectButton");
      if (!connectButton) {
        connectButton = document.createElement("button");
        connectButton.id = "connectButton";
        connectButton.textContent = "Conectar ao FMB140";
        document.body.appendChild(connectButton);

        connectButton.onclick = async () => {
          if (bleDevice && bleDevice.gatt.connected) {
            Streamlit.setComponentValue({ status: "already_connected" });
            return;
          }
          try {
            Streamlit.setComponentValue({ status: "connecting" });
            bleDevice = await navigator.bluetooth.requestDevice({
              filters: [{ services: [serviceUuid.toLowerCase()] }],
              optionalServices: [serviceUuid.toLowerCase()]
            });

            const server = await bleDevice.gatt.connect();
            const service = await server.getPrimaryService(serviceUuid.toLowerCase());
            writeCharacteristic = await service.getCharacteristic(characteristicUuid.toLowerCase());
            
            Streamlit.setComponentValue({ status: "connected", deviceName: bleDevice.name });

          } catch (error) {
            Streamlit.setComponentValue({ status: "error", payload: error.message });
          }
        };
      }

      if (command && writeCharacteristic) {
        try {
          writeCharacteristic.writeValue(textEncoder.encode(command));
          Streamlit.setComponentValue({ status: "command_sent", payload: command });
        } catch (error) {
          Streamlit.setComponentValue({ status: "error", payload: error.message });
        }
      }
    }

    Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
    Streamlit.setComponentReady();
    Streamlit.setFrameHeight(50);
});
"""

HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Streamlit BLE Component</title>
</head>
<body>
    <script>
        {JS_CODE}
    </script>
</body>
</html>
"""

# --- ETAPA 2: FUNÇÃO QUE DECLARA O COMPONENTE ---
_component_func = None

def teltonika_commander(service_uuid: str, characteristic_uuid: str, command: str = None, key=None):
    global _component_func
    
    if _component_func is None:
        build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "component-build")
        os.makedirs(build_dir, exist_ok=True)
        
        with open(os.path.join(build_dir, "index.html"), "w") as f:
            f.write(HTML_TEMPLATE)
            
        _component_func = components.declare_component(
            "ble_control",
            path=build_dir
        )

    component_value = _component_func(
        serviceUuid=service_uuid,
        characteristicUuid=characteristic_uuid,
        command=command,
        key=key,
        default=None
    )
    return component_value


# --- ETAPA 3: A APLICAÇÃO STREAMLIT PRINCIPAL ---
st.set_page_config(layout="centered")
st.title("Controle Remoto DOUT1 - Teltonika FMB140")

st.info("""
**Instruções:**
1.  Primeiro, clique em **'Conectar ao FMB140'**.
2.  Selecione seu dispositivo na janela do navegador.
3.  Após a conexão, use os botões 'Ativar' e 'Desativar' para controlar a DOUT1.
""")

# UUIDs Corrigidos para o Nordic UART Service (NUS)
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_CHAR_WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

if 'command_to_send' not in st.session_state:
    st.session_state.command_to_send = None
if 'status' not in st.session_state:
    st.session_state.status = "Desconectado"
if 'device_name' not in st.session_state:
    st.session_state.device_name = ""

col1, col2 = st.columns(2)
with col1:
    if st.button("🟢 Ativar DOUT1", use_container_width=True):
        st.session_state.command_to_send = "setdigout 1 1"

with col2:
    if st.button("🔴 Desativar DOUT1", use_container_width=True):
        st.session_state.command_to_send = "setdigout 1 0"

component_response = teltonika_commander(
    service_uuid=NUS_SERVICE_UUID,
    characteristic_uuid=NUS_CHAR_WRITE_UUID,
    command=st.session_state.command_to_send,
    key="ble_commander"
)

if st.session_state.command_to_send is not None:
    st.session_state.command_to_send = None

st.header("Status da Conexão")
status_placeholder = st.empty()

if component_response:
    status = component_response.get("status")
    if status == "connecting":
        st.session_state.status = "Conectando..."
    elif status == "connected":
        st.session_state.device_name = component_response.get("deviceName", "")
        st.session_state.status = f"✅ Conectado a **{st.session_state.device_name}**"
        st.balloons()
    elif status == "command_sent":
        st.session_state.status = f"✅ Conectado a **{st.session_state.device_name}**"
        st.success(f"Comando enviado: '{component_response.get('payload')}'")
        time.sleep(1)
    elif status == "error":
        st.session_state.status = f"❌ Erro: {component_response.get('payload')}"

status_placeholder.markdown(st.session_state.status)

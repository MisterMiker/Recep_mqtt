import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import pandas as pd

# ---------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------
st.set_page_config(
    page_title="Lector de Sensor MQTT",
    page_icon="📡",
    layout="centered"
)

# ---------------------------
# ESTILO VISUAL PERSONALIZADO
# ---------------------------
st.markdown("""
    <style>
    .stApp {
        background-color: #e8eddf;
        color: #242423;
    }
    h1, h2, h3, h4 {
        color: #333533;
    }
    .metric-label {
        font-weight: bold;
        font-size: 1.2em;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------
# VARIABLES DE ESTADO
# ---------------------------
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = None
if 'history' not in st.session_state:
    st.session_state.history = []


# ---------------------------
# FUNCIÓN PARA UN SOLO MENSAJE
# ---------------------------
def get_mqtt_message(broker, port, topic, client_id):
    message_received = {"received": False, "payload": None}
    
    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
        except:
            payload = message.payload.decode()
        message_received["payload"] = payload
        message_received["received"] = True

    try:
        client = mqtt.Client(client_id=client_id)
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()

        timeout = time.time() + 5
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)

        client.loop_stop()
        client.disconnect()

        return message_received["payload"]
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# SIDEBAR DE CONFIGURACIÓN
# ---------------------------
with st.sidebar:
    st.subheader('⚙️ Configuración de Conexión')
    broker = st.text_input('Broker MQTT', value='broker.mqttdashboard.com')
    port = st.number_input('Puerto', value=1883, min_value=1, max_value=65535)
    topic = st.text_input('Tópico', value='Sensor/THP2')
    client_id = st.text_input('ID del Cliente', value='streamlit_client')

# ---------------------------
# TÍTULO E INFORMACIÓN
# ---------------------------
st.title('📡 Lector de Sensor MQTT')
st.markdown("Visualiza datos de sensores en tiempo real y en gráficos históricos.")

st.divider()

# ---------------------------
# BOTÓN DE LECTURA MANUAL
# ---------------------------
if st.button('🔄 Obtener Datos del Sensor', use_container_width=True):
    with st.spinner('Conectando al broker y esperando datos...'):
        data = get_mqtt_message(broker, int(port), topic, client_id)
        st.session_state.sensor_data = data

# ---------------------------
# MODO TIEMPO REAL
# ---------------------------
st.divider()
live_mode = st.toggle("📶 Activar modo tiempo real", value=False)

if live_mode:
    st.info("Recibiendo datos continuamente... detén la ejecución para salir.")
    placeholder = st.empty()
    chart_placeholder = st.empty()

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
        except:
            payload = {"value": message.payload.decode()}

        st.session_state.sensor_data = payload

        # Guardar histórico
        if isinstance(payload, dict) and "temperature" in payload:
            st.session_state.history.append(payload["temperature"])
            if len(st.session_state.history) > 50:
                st.session_state.history.pop(0)

        # Actualizar métricas
        with placeholder.container():
            if isinstance(payload, dict):
                cols = st.columns(len(payload))
                for i, (key, value) in enumerate(payload.items()):
                    icon = ""
                    if "temp" in key.lower():
                        icon = "🌡️"
                    elif "hum" in key.lower():
                        icon = "💧"
                    elif "press" in key.lower():
                        icon = "⛰️"
                    cols[i].metric(label=f"{icon} {key}", value=value)
            else:
                st.code(payload)

        # Actualizar gráfico
        if st.session_state.history:
            with chart_placeholder.container():
                st.line_chart(st.session_state.history, height=200)

    client = mqtt.Client(client_id=client_id)
    client.on_message = on_message
    client.connect(broker, port, 60)
    client.subscribe(topic)
    client.loop_forever()

# ---------------------------
# MOSTRAR DATOS RECIENTES
# ---------------------------
if st.session_state.sensor_data and not live_mode:
    st.divider()
    st.subheader('📊 Últimos Datos Recibidos')
    data = st.session_state.sensor_data

    if isinstance(data, dict) and 'error' in data:
        st.error(f"❌ Error de conexión: {data['error']}")
    else:
        st.success('✅ Datos recibidos correctamente')
        if isinstance(data, dict):
            cols = st.columns(len(data))
            for i, (key, value) in enumerate(data.items()):
                icon = ""
                if "temp" in key.lower():
                    icon = "🌡️"
                elif "hum" in key.lower():
                    icon = "💧"
                elif "press" in key.lower():
                    icon = "⛰️"
                cols[i].metric(label=f"{icon} {key}", value=value)

            with st.expander('Ver JSON completo'):
                st.json(data)

            # Agregar a histórico y mostrar gráfico
            if "temperature" in data:
                st.session_state.history.append(data["temperature"])
                st.line_chart(st.session_state.history, height=200)
        else:
            st.code(data)

# Dashboard Streamlit (Streamlit Cloud) - lee Supabase, analítica con Pandas, control del LED por MQTT
import time, threading, requests
import pandas as pd, streamlit as st, plotly.express as px
import paho.mqtt.client as mqtt

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HDR = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
API = f"{SUPABASE_URL}/rest/v1/operaciones"
BROKER, T_CMD, T_EST = "broker.hivemq.com", "trez/jmiranda/foco/cmd", "trez/jmiranda/foco/estado"
DISPOSITIVO = "ESP32-Wokwi"

def leer():
    r = requests.get(API, headers=HDR, params={"select": "*", "order": "fecha_hora.asc"}, timeout=10)
    r.raise_for_status()
    return pd.DataFrame(r.json())

def enviar(cmd):
    """Publica la orden al ESP32 y espera su respuesta (máx 6 s)."""
    resp, ev = {"v": "SIN_RESPUESTA"}, threading.Event()
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    def on_connect(cl, u, f, rc, p):
        cl.subscribe(T_EST); time.sleep(0.3); cl.publish(T_CMD, cmd)
    def on_message(cl, u, m):
        resp["v"] = m.payload.decode().strip(); ev.set()
    c.on_connect, c.on_message = on_connect, on_message
    c.connect(BROKER, 1883, 30); c.loop_start(); ev.wait(6); c.loop_stop(); c.disconnect()
    return resp["v"]

def operar(accion, cmd, df):
    previo = df.iloc[-1].estado if not df.empty else "OFF"
    est = enviar(cmd)
    dur = 0
    if accion == "APAGAR" and previo == "ON":
        enc = df[df.accion == "ENCENDER"]
        if not enc.empty:
            dur = int((pd.Timestamp.now(tz="UTC") - enc.iloc[-1].fecha_hora).total_seconds())
    requests.post(API, headers=HDR, json={"accion": accion, "estado": est,
                  "dispositivo": DISPOSITIVO, "duracion_seg": dur}, timeout=10)
    return est

st.set_page_config(page_title="Dashboard Foco IoT", layout="wide")
st.title("💡 Dashboard IoT – Foco LED (ESP32 Wokwi)")

df = leer()
if not df.empty:
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], utc=True)

# ---- Control del foco ----
st.subheader("🎛️ Control del foco")
b0, b1, b2, b3 = st.columns(4)
if b0.button("🔄 Actualizar", use_container_width=True): st.rerun()
for col, (txt, acc, cmd) in zip([b1, b2, b3], [("💡 ENCENDER", "ENCENDER", "ON"),
                                              ("⚫ APAGAR", "APAGAR", "OFF"),
                                              ("🔍 CONSULTAR", "CONSULTAR", "STATUS")]):
    if col.button(txt, use_container_width=True):
        st.toast(f"Respuesta ESP32: {operar(acc, cmd, df)}"); time.sleep(1); st.rerun()

if df.empty:
    st.warning("Aún no hay operaciones registradas."); st.stop()
df["fecha_local"] = df.fecha_hora.dt.tz_convert("America/Lima")

# ---- P3: estado e indicadores ----
ult = df.iloc[-1]
st.subheader("Estado del dispositivo")
c1, c2, c3 = st.columns(3)
c1.metric("Estado actual del foco", "🟡 ON" if ult.estado == "ON" else "⚫ OFF")
c2.metric("Última operación", ult.accion)
c3.metric("Fecha y hora (Lima)", ult.fecha_local.strftime("%d/%m/%Y %H:%M:%S"))

# ---- P4: analítica ----
total = len(df)
enc = int((df.accion == "ENCENDER").sum())
apa = int((df.accion == "APAGAR").sum())
cons = int((df.accion == "CONSULTAR").sum())
t_total = int(df.duracion_seg.sum())
st.subheader("📊 Analítica de funcionamiento")
k = st.columns(5)
k[0].metric("Total operaciones", total); k[1].metric("Encendidos", enc)
k[2].metric("Apagados", apa); k[3].metric("Consultas de estado", cons)
k[4].metric("Tiempo total funcionamiento", f"{t_total//60} min {t_total%60} s")

g1, g2 = st.columns(2)
pt = df.accion.value_counts().reset_index(); pt.columns = ["accion", "cantidad"]
g1.plotly_chart(px.bar(pt, x="accion", y="cantidad", color="accion", text="cantidad",
                       title="Operaciones por tipo"), use_container_width=True)
pe = df.estado.value_counts().reset_index(); pe.columns = ["estado", "cantidad"]
g2.plotly_chart(px.pie(pe, names="estado", values="cantidad", title="Estados del foco"),
                use_container_width=True)
df["minuto"] = df.fecha_local.dt.strftime("%Y-%m-%d %H:%M")
ptiempo = df.groupby("minuto").size().reset_index(name="operaciones")
st.plotly_chart(px.line(ptiempo, x="minuto", y="operaciones", markers=True,
                        title="Operaciones por fecha y hora"), use_container_width=True)

st.subheader("🧠 Interpretación de resultados")
prom = t_total / apa if apa else 0
pico = ptiempo.loc[ptiempo.operaciones.idxmax(), "minuto"]
st.info(f"Se registraron **{total} operaciones**: {enc} encendidos ({enc/total*100:.1f}%), "
        f"{apa} apagados ({apa/total*100:.1f}%) y {cons} consultas ({cons/total*100:.1f}%). "
        f"El foco estuvo encendido **{t_total} s** en total, con un promedio de **{prom:.1f} s por ciclo**. "
        f"Mayor actividad: **{pico}**. Estado actual: **{ult.estado}**.")

st.subheader("📜 Historial de operaciones")
st.dataframe(df[["id", "fecha_local", "accion", "estado", "dispositivo", "duracion_seg"]]
             .sort_values("id", ascending=False), use_container_width=True, hide_index=True)

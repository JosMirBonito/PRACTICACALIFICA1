// App React Native (web) - publicada en Vercel, datos en Supabase, LED por MQTT
import React, { useEffect, useRef, useState } from 'react';
import { View, Text, Pressable, FlatList, StyleSheet } from 'react-native';
import { createClient } from '@supabase/supabase-js';
import mqtt from 'mqtt/dist/mqtt.esm';
import { SUPABASE_URL, SUPABASE_KEY, MQTT_URL, T_CMD, T_EST, DISPOSITIVO } from './config';

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

export default function App() {
  const [estado, setEstado] = useState('...');
  const [conectado, setConectado] = useState(false);
  const [hist, setHist] = useState([]);
  const cli = useRef(null);
  const espera = useRef(null);
  const estadoRef = useRef('OFF');

  const cargar = async () => {
    const { data } = await supabase.from('operaciones').select('*').order('id', { ascending: false }).limit(50);
    setHist(data || []);
  };

  useEffect(() => {
    const c = mqtt.connect(MQTT_URL, { clientId: 'web-' + Math.random().toString(16).slice(2) });
    c.on('connect', () => { setConectado(true); c.subscribe(T_EST); });
    c.on('close', () => setConectado(false));
    c.on('message', (_t, msg) => {
      const v = msg.toString().trim();
      estadoRef.current = v; setEstado(v);
      if (espera.current) { espera.current(v); espera.current = null; }
    });
    cli.current = c;
    cargar();
    return () => c.end();
  }, []);

  // Envía orden al ESP32 y espera su respuesta (máx 5 s)
  const enviar = (cmd) => new Promise((res) => {
    const t = setTimeout(() => { espera.current = null; res('SIN_RESPUESTA'); }, 5000);
    espera.current = (v) => { clearTimeout(t); res(v); };
    cli.current.publish(T_CMD, cmd);
  });

  const segundosEncendido = async () => {
    const { data } = await supabase.from('operaciones').select('fecha_hora')
      .eq('accion', 'ENCENDER').order('id', { ascending: false }).limit(1);
    return data && data.length ? Math.round((Date.now() - new Date(data[0].fecha_hora)) / 1000) : 0;
  };

  const accion = async (nombre, cmd) => {
    const previo = estadoRef.current;
    const est = await enviar(cmd);
    const dur = nombre === 'APAGAR' && previo === 'ON' ? await segundosEncendido() : 0;
    await supabase.from('operaciones').insert({ accion: nombre, estado: est, dispositivo: DISPOSITIVO, duracion_seg: dur });
    cargar();
  };

  const Boton = ({ t, color, onPress }) => (
    <Pressable style={[s.btn, { backgroundColor: color }]} onPress={onPress}><Text style={s.btnT}>{t}</Text></Pressable>
  );

  return (
    <View style={s.c}>
      <Text style={s.h}>💡 Foco LED IoT</Text>
      <Text style={s.sub}>MQTT: {conectado ? '🟢 conectado' : '🔴 desconectado'}</Text>
      <Text style={s.estado}>Estado: {estado}</Text>
      <View style={s.row}>
        <Boton t="Encender" color="#2563eb" onPress={() => accion('ENCENDER', 'ON')} />
        <Boton t="Apagar" color="#b91c1c" onPress={() => accion('APAGAR', 'OFF')} />
        <Boton t="Consultar" color="#4b5563" onPress={() => accion('CONSULTAR', 'STATUS')} />
      </View>
      <Text style={s.h2}>Historial</Text>
      <FlatList data={hist} keyExtractor={(i) => String(i.id)}
        renderItem={({ item }) => (
          <Text style={s.i}>{new Date(item.fecha_hora).toLocaleString('es-PE')} | {item.accion} | {item.estado} | {item.dispositivo} | {item.duracion_seg}s</Text>
        )} />
    </View>
  );
}

const s = StyleSheet.create({
  c: { flex: 1, padding: 20, maxWidth: 700, width: '100%', alignSelf: 'center' },
  h: { fontSize: 26, fontWeight: 'bold', marginTop: 20 },
  sub: { color: '#555', marginVertical: 4 },
  estado: { fontSize: 20, marginVertical: 10 },
  row: { flexDirection: 'row', gap: 10 },
  btn: { flex: 1, padding: 14, borderRadius: 8, alignItems: 'center' },
  btnT: { color: '#fff', fontWeight: 'bold' },
  h2: { fontSize: 20, fontWeight: 'bold', marginTop: 20, marginBottom: 6 },
  i: { fontSize: 13, borderBottomWidth: 1, borderColor: '#ddd', paddingVertical: 6 },
});

// 1) Pega aquí los datos de tu proyecto Supabase (Project Settings -> API)
export const SUPABASE_URL = 'https://TU-PROYECTO.supabase.co';
export const SUPABASE_KEY = 'TU_ANON_PUBLIC_KEY';

// 2) MQTT (mismo broker y tópicos que el ESP32 de Wokwi)
export const MQTT_URL = 'wss://broker.hivemq.com:8884/mqtt';
export const T_CMD = 'trez/jmiranda/foco/cmd';
export const T_EST = 'trez/jmiranda/foco/estado';
export const DISPOSITIVO = 'ESP32-Wokwi';

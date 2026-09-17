# Drone Environment Monitor — Ground Station Frontend

Real-time ground-station dashboard for MQ-2 (combustible/smoke), MQ-4 (methane)
and MQ-7 (carbon monoxide) sensors on an Arduino, streamed over a WebSocket.

```text
Arduino ──USB serial──> FastAPI ──WebSocket──> Next.js dashboard
```

## Quick start

1. Start the FastAPI backend (from `backend/`):

```bash
python main.py
```

2. Start the dashboard:

```bash
npm run dev
```

3. Open http://localhost:3000

## WebSocket

The dashboard connects to `ws://127.0.0.1:8000/ws/sensors` and expects JSON like:

```json
{"mq2":421,"mq4":186,"mq7":302}
```

To change the endpoint, set `NEXT_PUBLIC_WS_URL` or edit `lib/config.ts`

## CORS

No backend change is required. Browsers do **not** enforce same-origin policy on
WebSocket connections, so the FastAPI app does not need CORS middleware for the
dashboard to receive data.

## Demo mode

Use the **DEMO** toggle in the header to generate simulated (local) readings so
you can evaluate the UI without the Arduino. Demo data is always clearly marked
as simulated.

## Calibration

Raw ADC values are shown uncalibrated. True ppm concentrations are never
invented. To enable estimated ppm:

1. Expose the sensor to a known gas concentration.
2. Record ADC → ppm points in `lib/calibration.ts`.
3. Calibrated sensors then show `~XX ppm`, clearly labelled **ESTIMATED**.

Status thresholds in `lib/config.ts` are prototype placeholders that need
validation via calibration.

## Project structure

```text
app/              Next.js App Router (page, layout, globals.css)
components/       DashboardHeader, ConnectionStatus, GasSensorCard, GasChart,
                  GasAnalysis, EnvironmentalStatus, SensorDetailsTable,
                  ConcentrationPanel, StatusPill
hooks/            useSensorWebSocket (live WS + reconnection + demo mode)
lib/              config, gasAnalysis, baseline, calibration, format, demoSensors
types/            sensor.ts (strongly typed sensor model)
```
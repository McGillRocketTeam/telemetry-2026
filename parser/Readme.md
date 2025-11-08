# Telemetry Struct Generator

This Python utility automatically generates C++ `__packed__` structs and unions from a structured Excel file (`telemetry.xlsx`).

## 🚀 Usage

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Go to H26 Avionics Packet Coordinator google sheet and download as excel. Put your Excel file in the same directory as the python script and name it `telemetry.xlsx`.

3. Run the generator

   ```bash
   python generate_structs.py
   ```

4. Output

   ```
   telemetry_packets.cpp
   ```
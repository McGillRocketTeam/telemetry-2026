# Telemetry Struct Generator

This Python utility automatically generates C++ `__packed__` structs and unions from a structured Excel file (`telemetry.xlsx`).

## 🚀 Usage

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the generator

   ```bash
   python generate_structs.py
   ```

   The telemetry data is automatically pulled from the [Google Sheet](https://docs.google.com/spreadsheets/d/1Ukaums3NfbJdVOQL7E1QMyPNoQ7gD5Zxciiz4ucRUrk/edit?gid=965673768#gid=965673768).

3. Output

   ```
   telemetry_packets.cpp
   ```
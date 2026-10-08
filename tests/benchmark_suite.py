import sys
import os
import requests
import time
import statistics
import threading
import psutil
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


BASE_URL = "http://127.0.0.1:5000/recommend"

RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)
    
OUTPUT_FILE = os.path.join(RESULTS_DIR, "meresi_jegyzokonyv.txt")
ITERATIONS = 20



scenarios = [
    {
        "id": "T1",
        "name": "Alapállapot (Baseline)",
        "payload": {"constraints": {}, "preferences": {}, "settings": {"limit": 35}}
    },
    {
        "id": "T2",
        "name": "Komplex Gráf Szűrés",
        "payload": {
            "constraints": {
                "age": {"active": True, "values": ["18-25"]},
                "genres": {"active": True, "values": ["fantasy"]},
                "excluded_authors": {"active": True, "values": ["stephen-king"]}
            },
            "preferences": {},
            "settings": {"limit": 35}
        }
    },
    {
        "id": "T3",
        "name": "Hibrid Matek (Full Load)",
        "payload": {
            "constraints": {"age": {"active": True, "values": ["26-40"]}},
            "preferences": {
                "books": {
                    "values": ["4:2ff61c09-fa2b-4909-9fd0-76f6b5186e64:3"],
                    "weight_content": 50,
                    "weight_collab": 50
                }
            },
            "settings": {"limit": 50, "randomness": 0.2}
        }
    }
]



monitor_running = False
resource_stats = {"cpu_max": 0, "ram_max": 0, "ram_avg": [], "cpu_avg": []}

def get_flask_processes():
    """Megkeresi a futó app.py folyamatokat."""
    current_pid = os.getpid()
    procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] == current_pid: continue
            if proc.info['name'] and 'python' in proc.info['name']:
                cmdline = proc.info['cmdline']
                if cmdline and any('app.py' in arg for arg in cmdline):
                    procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return procs





def monitor_resources():
    """Háttérszálon futó erőforrás-figyelő."""
    global resource_stats
    resource_stats = {"cpu_max": 0, "ram_max": 0, "ram_avg": [], "cpu_avg": []}
    
    flask_procs = get_flask_processes()
    if not flask_procs:
        print(" [Monitor] Hiba: Nem találom a Flask folyamatot!")
        return

    while monitor_running:
        total_cpu = 0.0
        total_ram = 0.0
        
        for proc in flask_procs:
            try:
                total_cpu += proc.cpu_percent(interval=None)
                total_ram += proc.memory_info().rss / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if total_cpu > resource_stats["cpu_max"]: resource_stats["cpu_max"] = total_cpu
        if total_ram > resource_stats["ram_max"]: resource_stats["ram_max"] = total_ram
        
        resource_stats["cpu_avg"].append(total_cpu)
        resource_stats["ram_avg"].append(total_ram)
        
        time.sleep(0.5)




def run_benchmark():
    global monitor_running
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== KOMPLEX TELJESÍTMÉNY ÉS ERŐFORRÁS TESZT ===\n")
        f.write(f"Dátum: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Ismétlések száma: {ITERATIONS}\n")
        f.write("=================================================\n\n")

    print(f"Mérés indítása... ({ITERATIONS} kör / teszt)")
    
    try:
        requests.post(BASE_URL, json=scenarios[0]['payload'])
    except:
        print("HIBA: A szerver nem fut!")
        return

    for sc in scenarios:
        print(f"\n>> Teszt indítása: {sc['name']}...")
        
        monitor_running = True
        monitor_thread = threading.Thread(target=monitor_resources)
        monitor_thread.start()
        
        latencies = []
        for i in range(ITERATIONS):
            start = time.time()
            resp = requests.post(BASE_URL, json=sc['payload'])
            end = time.time()
            
            if resp.status_code == 200:
                latencies.append((end - start) * 1000)
            
            time.sleep(0.2) 

        monitor_running = False
        monitor_thread.join()
        
        avg_latency = statistics.mean(latencies) if latencies else 0
        min_latency = min(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        
        avg_cpu = statistics.mean(resource_stats["cpu_avg"]) if resource_stats["cpu_avg"] else 0
        avg_ram = statistics.mean(resource_stats["ram_avg"]) if resource_stats["ram_avg"] else 0
        
        result_text = (
            f"TESZT: {sc['name']} ({sc['id']})\n"
            f"----------------------------------------\n"
            f"Válaszidő (Latency):\n"
            f"  Átlag: {avg_latency:.2f} ms\n"
            f"  Min:   {min_latency:.2f} ms\n"
            f"  Max:   {max_latency:.2f} ms\n\n"
            f"Erőforrás (Resource):\n"
            f"  Átlagos CPU: {avg_cpu:.1f} %\n"
            f"  Csúcs CPU:   {resource_stats['cpu_max']:.1f} %\n"
            f"  Átlagos RAM: {avg_ram:.2f} MB\n"
            f"  Csúcs RAM:   {resource_stats['ram_max']:.2f} MB\n"
            f"----------------------------------------\n\n"
        )
        
        print(f"   Kész. Átlag: {avg_latency:.2f}ms | CPU Peak: {resource_stats['cpu_max']:.1f}%")
        
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(result_text)

    print(f"\nMérés befejezve. Részletes adatok: {OUTPUT_FILE}")

if __name__ == "__main__":
        
    run_benchmark()
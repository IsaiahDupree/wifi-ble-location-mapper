import argparse, platform, re, subprocess, time, requests, asyncio
from libs.core.schema import Observation, GeoPoint
from pydantic import BaseModel
try:
    from bleak import BleakScanner; BLE_AVAILABLE=True
except Exception:
    BLE_AVAILABLE=False
try:
    import gpsd; GPSD_AVAILABLE=True
except Exception:
    GPSD_AVAILABLE=False

def dbm_from_percent(pct:int)->int: return int(round(pct/2 - 100))

def scan_wifi_windows():
    out = subprocess.check_output(["netsh","wlan","show","networks","mode=bssid"], text=True, errors="ignore")
    blocks = re.split(r"\n\s*SSID \d+ :", out); results=[]
    for block in blocks[1:]:
        ssid = block.strip().splitlines()[0].strip()
        for b in re.split(r"\n\s*BSSID \d+ :", block)[1:]:
            lines=b.splitlines(); bssid=lines[0].strip(); signal=None; channel=None
            for ln in lines[1:]:
                if "Signal" in ln:
                    m=re.search(r"(\d+)%", ln); signal=int(m.group(1)) if m else None
                if "Channel" in ln:
                    m=re.search(r"(\d+)", ln); channel=int(m.group(1)) if m else None
            if bssid and signal is not None:
                results.append({"ssid":ssid,"bssid":bssid,"rssi_dbm":dbm_from_percent(signal),"channel":channel})
    return results

def scan_wifi_macos():
    airport="/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    out = subprocess.check_output([airport,"-s"], text=True, errors="ignore")
    results=[]
    for ln in out.splitlines()[1:]:
        if not ln.strip(): continue
        parts=re.split(r"\s{2,}", ln.strip())
        if len(parts)<3: continue
        ssid, bssid = parts[0], parts[1]
        try: rssi=int(parts[2])
        except: continue
        channel=None
        if len(parts)>=4:
            ch=parts[3].split(",")[0]
            try: channel=int(ch)
            except: pass
        results.append({"ssid":ssid,"bssid":bssid,"rssi_dbm":rssi,"channel":channel})
    return results

def scan_wifi_linux():
    try:
        out = subprocess.check_output(["nmcli","-f","SSID,BSSID,CHAN,FREQ,SIGNAL","dev","wifi"], text=True, errors="ignore")
        results=[]
        for ln in out.splitlines()[1:]:
            if not ln.strip(): continue
            m = re.match(r"(.+?)\s+([0-9A-Fa-f:]{17})\s+(\d+)\s+(\d+)\s+(\d+)", ln.strip())
            if not m: continue
            ssid,bssid,chan,freq,signal = m.groups()
            results.append({"ssid":ssid,"bssid":bssid,"rssi_dbm":dbm_from_percent(int(signal)),"channel":int(chan),"freq_mhz":int(freq)})
        return results
    except Exception:
        return []

async def scan_ble_once(timeout: float=5.0):
    if not BLE_AVAILABLE: return []
    devs = await BleakScanner.discover(timeout=timeout); out=[]
    for d in devs:
        uuids = getattr(d, "metadata",{}).get("uuids") if hasattr(d,"metadata") else None
        out.append({"address":getattr(d,"address",None),"rssi_dbm":getattr(d,"rssi",None),"service_uuids":uuids})
    return out

def get_gps_location(gpsd_host="127.0.0.1", gpsd_port=2947):
    """Get current GPS location from gpsd daemon."""
    if not GPSD_AVAILABLE:
        return None
    try:
        gpsd.connect(host=gpsd_host, port=gpsd_port)
        packet = gpsd.get_current()
        if packet.mode >= 2:  # 2D fix or better
            return GeoPoint(lat=packet.lat, lon=packet.lon, 
                          alt=packet.alt if packet.mode >= 3 else None,
                          accuracy_m=packet.error.get('c', None) if hasattr(packet, 'error') else None)
    except Exception as e:
        print(f"[GPS] error: {e}")
    return None

def post(server:str, obs:Observation):
    try: requests.post(server.rstrip("/")+"/observation", json=obs.model_dump(), timeout=5).raise_for_status()
    except Exception as e: print("[POST] error:", e)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:9000")
    ap.add_argument("--observer", required=True)
    ap.add_argument("--lat", type=float, help="Fixed latitude (required if not using GPS)")
    ap.add_argument("--lon", type=float, help="Fixed longitude (required if not using GPS)")
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--radios", nargs="+", default=["wifi","ble"], choices=["wifi","ble"])
    ap.add_argument("--gpsd", action="store_true", help="Use GPS daemon for live location")
    ap.add_argument("--gpsd-host", default="127.0.0.1", help="GPSD host")
    ap.add_argument("--gpsd-port", type=int, default=2947, help="GPSD port")
    args=ap.parse_args()
    
    # Determine location source
    if args.gpsd:
        if not GPSD_AVAILABLE:
            print("[ERROR] gpsd-py3 not available. Install with: pip install gpsd-py3")
            return
        print(f"[GPS] Using GPS daemon at {args.gpsd_host}:{args.gpsd_port}")
        loc = None  # Will be updated from GPS
    else:
        if args.lat is None or args.lon is None:
            print("[ERROR] --lat and --lon required when not using --gpsd")
            return
        loc = GeoPoint(lat=args.lat, lon=args.lon)
        print(f"[FIXED] Using fixed location: {args.lat}, {args.lon}")
    loop=asyncio.get_event_loop()
    while True:
        # Update location from GPS if enabled
        if args.gpsd:
            gps_loc = get_gps_location(args.gpsd_host, args.gpsd_port)
            if gps_loc:
                loc = gps_loc
                print(f"[GPS] Updated location: {loc.lat:.6f}, {loc.lon:.6f}")
            else:
                print("[GPS] No fix available, skipping scan")
                time.sleep(args.interval)
                continue
        
        if "wifi" in args.radios:
            try:
                sys=platform.system().lower()
                wifi = scan_wifi_windows() if "windows" in sys else scan_wifi_macos() if "darwin" in sys else scan_wifi_linux()
                for w in wifi:
                    post(args.server, Observation(observer_id=args.observer, radio="wifi", signal_id=w["bssid"],
                         ssid=w.get("ssid"), freq_mhz=w.get("freq_mhz"), channel=w.get("channel"),
                         rssi_dbm=int(w["rssi_dbm"]), observer_location=loc, raw={"source":"os_cli"}))
                print(f"[WIFI] sent {len(wifi)} observations")
            except Exception as e: print("[WIFI] error:", e)
        if "ble" in args.radios:
            try:
                ble = loop.run_until_complete(scan_ble_once(5.0))
                for b in ble:
                    if b["address"] is None or b["rssi_dbm"] is None: continue
                    post(args.server, Observation(observer_id=args.observer, radio="ble", signal_id=b["address"],
                         service_uuids=b.get("service_uuids"), rssi_dbm=int(b["rssi_dbm"]),
                         observer_location=loc, raw={"source":"bleak"}))
                print(f"[BLE] sent {len(ble)} observations")
            except Exception as e: print("[BLE] error:", e)
        time.sleep(args.interval)

if __name__ == "__main__":
    main()

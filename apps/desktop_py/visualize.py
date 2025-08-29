import argparse, os, requests, pandas as pd

def build_pydeck(df, out_html):
    import pydeck as pdk
    view = pdk.ViewState(latitude=df["lat"].mean() if not df.empty else 0,
                         longitude=df["lon"].mean() if not df.empty else 0, zoom=12 if not df.empty else 1)
    df["weight"] = (df["rssi_dbm"] - df["rssi_dbm"].min() + 1).clip(1) if not df.empty else 1
    deck = pdk.Deck(
        layers=[
            pdk.Layer("HexagonLayer", data=df, get_position='[lon, lat]', elevation_scale=10,
                      pickable=True, extruded=True, radius=20, get_elevation_weight="weight",
                      elevation_aggregation="MEAN"),
            pdk.Layer("ScatterplotLayer", data=df, get_position='[lon, lat]', get_radius=5, pickable=True),
        ],
        initial_view_state=view, map_style="light"
    )
    deck.to_html(out_html, open_browser=False); print(f"[viz] wrote {out_html} (pydeck)")

def build_folium(df, out_html):
    import folium
    from folium.plugins import HeatMap
    m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()], zoom_start=13) if not df.empty else folium.Map([0,0],2)
    if not df.empty:
        df["weight"] = (df["rssi_dbm"] - df["rssi_dbm"].min() + 1).clip(1)
        HeatMap(df[["lat","lon","weight"]].values.tolist(), radius=20).add_to(m)
        for _,r in df.iterrows():
            folium.CircleMarker([r["lat"],r["lon"]], radius=3, popup=f"{r['radio']} {r['signal_id']} {r['rssi_dbm']} dBm").add_to(m)
    m.save(out_html); print(f"[viz] wrote {out_html} (folium)")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:9000")
    ap.add_argument("--out", default="map.html")
    ap.add_argument("--limit", type=int, default=2000)
    args=ap.parse_args()
    data = requests.get(args.server.rstrip("/")+f"/observations?limit={args.limit}", timeout=10).json()
    rows=[{"radio":o.get("radio"),"signal_id":o.get("signal_id"),"ssid":o.get("ssid"),
           "rssi_dbm":o.get("rssi_dbm"),"lat":(o.get("observer_location") or {}).get("lat"),
           "lon":(o.get("observer_location") or {}).get("lon")} for o in data]
    df = pd.DataFrame(rows).dropna(subset=["lat","lon"])
    if os.environ.get("MAPBOX_API_KEY"): build_pydeck(df, args.out)
    else: build_folium(df, args.out)

if __name__ == "__main__":
    main()

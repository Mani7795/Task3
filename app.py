from flask import Flask, render_template, request
import requests
import folium
import os

app = Flask(__name__)

API_URL = "https://www.microburbs.com.au/report_generator/api/suburb/properties"
HEADERS = {
    "Authorization": "Bearer test",
    "Content-Type": "application/json"
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def query_amenities(lat, lon, radius=2000):
    """
    Query OpenStreetMap for nearby railway stations, schools, and grocery stores.
    Returns a dict of category -> list of (name, lat, lon).
    """
    query = f"""
    [out:json];
    (
      node["railway"="station"](around:{radius},{lat},{lon});
      node["amenity"="school"](around:{radius},{lat},{lon});
      node["shop"="supermarket"](around:{radius},{lat},{lon});
    );
    out body;
    """
    try:
        response = requests.get(OVERPASS_URL, params={"data": query}, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return {"railway": [], "school": [], "grocery": []}

    results = {"railway": [], "school": [], "grocery": []}
    for el in data.get("elements", []):
        lat, lon = el.get("lat"), el.get("lon")
        tags = el.get("tags", {})
        name = tags.get("name", "Unnamed")

        if tags.get("railway") == "station":
            results["railway"].append((name, lat, lon))
        elif tags.get("amenity") == "school":
            results["school"].append((name, lat, lon))
        elif tags.get("shop") == "supermarket":
            results["grocery"].append((name, lat, lon))

    return results


def create_map(properties, suburb):
    """Generate Folium map with properties and nearby amenities."""
    default_location = [-33.8688, 151.2093]
    m = folium.Map(location=default_location, zoom_start=13, tiles="OpenStreetMap", width="100%", height="700px")

    markers = []
    for p in properties:
        lat, lon = p.get("latitude"), p.get("longitude")
        if not lat or not lon:
            continue

        price = p.get("price", "-")
        popup_html = f"""
        <b>{p.get('area_name', '-')}</b><br>
        Type: {p.get('property_type', '-')}<br>
        Price: ${price:,}<br>
        Beds: {p.get('bedrooms', '-')} | Baths: {p.get('bathrooms', '-')}
        """

        # Color markers by price range
        if price and price != "-" and isinstance(price, (int, float)):
            if price < 1000000:
                color = "green"
            elif price < 1500000:
                color = "orange"
            else:
                color = "red"
        else:
            color = "blue"

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=p.get("area_name", "Property"),
            icon=folium.Icon(color=color, icon="home", prefix="fa")
        ).add_to(m)
        markers.append((lat, lon))

    # Center map
    if markers:
        avg_lat = sum(lat for lat, _ in markers) / len(markers)
        avg_lon = sum(lon for _, lon in markers) / len(markers)
        m.location = [avg_lat, avg_lon]
        m.fit_bounds(markers)
    else:
        avg_lat, avg_lon = default_location

    # Query and add nearby amenities
    amenities = query_amenities(avg_lat, avg_lon)

  
    
    # Schools
    for name, lat, lon in amenities["school"]:
        folium.Marker(
            [lat, lon],
            icon=folium.Icon(color="cadetblue", icon="graduation-cap", prefix="fa"),
            popup=f"🏫 <b>{name}</b><br>School"
        ).add_to(m)

    # Grocery stores
    for name, lat, lon in amenities["grocery"]:
        folium.Marker(
            [lat, lon],
            icon=folium.Icon(color="lightgray", icon="shopping-cart", prefix="fa"),
            popup=f"🛒 <b>{name}</b><br>Grocery Store"
        ).add_to(m)

    # Save map
    map_path = os.path.join("templates", "map.html")
    m.save(map_path)
    return "map.html"


@app.route("/", methods=["GET"])
def home():
    suburb = request.args.get("suburb", default="Belmont North", type=str)
    params = {"suburb": suburb}

    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return render_template("error.html", message=f"API request failed: {e}")

    results = data.get("results", [])
    formatted = []
    for p in results:
        addr = p.get("address", {})
        attr = p.get("attributes", {})
        coords = p.get("coordinates", {})

        raw_land = attr.get("land_size")
        if raw_land is None or str(raw_land).lower() in ("none", "nan", ""):
            land_size = "None"
        elif not str(raw_land).lower().endswith("m²"):
            land_size = f"{raw_land} m²"
        else:
            land_size = raw_land

        formatted.append({
            "area_name": p.get("area_name", "-"),
            "street": addr.get("street", "-"),
            "suburb": addr.get("sal", "-"),
            "state": addr.get("state", "-"),
            "property_type": p.get("property_type", "-"),
            "price": p.get("price", "-"),
            "bedrooms": attr.get("bedrooms", "-"),
            "bathrooms": attr.get("bathrooms", "-"),
            "garage_spaces": attr.get("garage_spaces", "-"),
            "land_size": land_size,
            "listing_date": p.get("listing_date", "-"),
            "latitude": coords.get("latitude"),
            "longitude": coords.get("longitude"),
            "description": attr.get("description", "-"),
        })

    map_file = create_map(formatted, suburb)
    return render_template("index.html", properties=formatted, suburb=suburb, map_file=map_file)


@app.route("/map")
def show_map():
    return render_template("map.html")


if __name__ == "__main__":
    app.run(debug=True)

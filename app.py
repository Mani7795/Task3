from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

API_URL = "https://www.microburbs.com.au/report_generator/api/suburb/properties"
HEADERS = {
    "Authorization": "Bearer test",
    "Content-Type": "application/json"
}

@app.route('/', methods=['GET'])
def home():
    suburb = request.args.get('suburb', default='Belmont North', type=str)
    params = {"suburb": suburb}

    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return render_template("error.html", message=f"API request failed: {e}")
    except ValueError:
        return render_template("error.html", message="Invalid JSON received from API.")

    # Extract property list
    properties = data.get("results", [])

    # Format key fields for cleaner display
    formatted = []
    for p in properties:
        addr = p.get("address", {})
        attr = p.get("attributes", {})
        coords = p.get("coordinates", {})

        formatted.append({
            "area_name": p.get("area_name", "-"),
            "street": addr.get("street", "-"),
            "suburb": addr.get("sal", "-"),
            "state": addr.get("state", "-"),
            "property_type": p.get("property_type", "-"),
            "price": p.get("price", "-"),
            "bedrooms": attr.get("bedrooms", "-"),
            "bathrooms": attr.get("bathrooms", "-"),
            "land_size": attr.get("land_size", "-"),
            "garage_spaces": attr.get("garage_spaces", "-"),
            "listing_date": p.get("listing_date", "-"),
            "latitude": coords.get("latitude", "-"),
            "longitude": coords.get("longitude", "-"),
            "description": attr.get("description", "-")
        })

    return render_template("index.html", properties=formatted, suburb=suburb)


@app.route('/api/properties')
def api_properties():
    suburb = request.args.get('suburb', default='Belmont North', type=str)
    params = {"suburb": suburb}
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)

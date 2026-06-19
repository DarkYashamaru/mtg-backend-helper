from flask import Flask, request, jsonify
from services.deck_processor import process_deck
import requests
from curl_cffi import requests as curl_req
from bs4 import BeautifulSoup
from services.mtg_database import *
import unicodedata

app = Flask(__name__)


@app.route("/api/health")
def health():
    return {"status": "ok"}

@app.route("/api/cards/id/<oracle_id>", methods=["GET"])
def card_by_id(oracle_id):
    try:
        card = get_card_by_id(oracle_id)

        return jsonify(card)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/cards/name/<path:name>", methods=["GET"])
def card_by_name(name):
    try:
        card = get_card_by_name(name)

        return jsonify(card)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}

    deck_text = data.get("deck_text", "").strip()

    if not deck_text:
        return jsonify({
            "success": False,
            "error": "deck_text is required"
        }), 400

    try:
        result = process_deck(deck_text)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
@app.route("/api/deck-cards", methods=["POST"])
def deck_cards():
    data = request.get_json(silent=True) or {}

    deck_text = data.get("deck_text", "").strip()

    if not deck_text:
        return jsonify({
            "success": False,
            "error": "deck_text is required"
        }), 400

    try:
        cards = get_cards_bulk(deck_text)

        return jsonify({
            "success": True,
            "cards": cards
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
@app.route("/api/themes/by-commander/<oracle_id>", methods=["GET"])
def themes_by_card(oracle_id):
    try:
        # 1. Pull data directly from the mtg-database service
        themes = get_themes_by_card(oracle_id)
        
        # 2. Return the array data straight back to the frontend
        return jsonify(themes)

    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve strategy themes: {str(e)}"
        }), 500
    
@app.route("/api/advanced", methods=["GET"])
def advanced_search_route():
    print("FLASK INCOMING:", request.args.to_dict(flat=False))
    try:
        results = advanced_search(
            name=request.args.get("name"),
            colors=request.args.getlist("colors"),
            exact_colors=request.args.get("exact_colors", "false").lower() == "true",

            tags=request.args.getlist("tags"),
            exclude_tags=request.args.getlist("exclude_tags"),

            card_type=request.args.get("card_type"),

            oracle_text=request.args.getlist("oracle_text"),
            exclude_oracle_text=request.args.getlist("exclude_oracle_text"),
        )

        return jsonify(results)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
    
def clean_card_name(name):
    normalized = unicodedata.normalize('NFD', name)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn').replace("’", "'")

@app.route('/api/scrape-price', methods=['GET'])
def get_card_price():
    raw_name = request.args.get('name')
    if not raw_name:
        return jsonify({"error": "Missing 'name' query parameter"}), 400

    # Clean the name for the search bar
    search_name = clean_card_name(raw_name)
    url = f"https://dracostore.co/catalogo?q={curl_req.utils.quote(search_name)}&sort=price_asc"

    try:
        response = curl_req.get(url, impersonate="chrome", timeout=10)
        
        if response.status_code != 200:
            return jsonify({"success": False, "dracostore_status_code": response.status_code}), 400

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- CASE A: The store redirected us straight to the specific card page ---
        if "/carta/" in response.url:
            # On the direct card page, look for the main text containing "COP"
            price_span = soup.find('span', string=lambda text: text and 'COP' in text)
            if price_span:
                clean_price = price_span.text.strip().replace('$', '').replace(' COP', '').strip()
                return jsonify({"success": True, "card": raw_name, "currency": "COP", "price": clean_price})

        # --- CASE B: We are on the standard catalog results list page ---
        else:
            # Try to find a link matching either the raw name or the cleaned name
            card_link = soup.find('a', {'aria-label': raw_name}) or soup.find('a', {'aria-label': search_name})
            
            if card_link:
                card_container = card_link.parent
                price_span = card_container.find('span', string=lambda text: text and 'COP' in text)
                
                if price_span:
                    clean_price = price_span.text.strip().replace('$', '').replace(' COP', '').strip()
                    return jsonify({"success": True, "card": raw_name, "currency": "COP", "price": clean_price})

        return jsonify({"error": f"Card '{raw_name}' found, but couldn't parse the price layout."}), 404

    except Exception as e:
        return jsonify({"error": f"Failed to connect to store: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

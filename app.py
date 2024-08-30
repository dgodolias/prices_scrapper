from flask import Flask, request, jsonify, render_template
import threading
import prices_scraper


app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    data = request.json
    product = data.get("product")
    country = data.get("country")

    results = []
    
    if country == "all":
        # Run the search for all countries
        for country_data in prices_scraper.EU_COUNTRIES:
            search_results = prices_scraper.run_search(product, country_data)
            results.extend(search_results)
    else:
        # Run the search for a specific country
        country_data = next(c for c in prices_scraper.EU_COUNTRIES if c["country_code"] == country)
        results = prices_scraper.run_search(product, country_data)
    
    # Convert prices to Euro if necessary
    prices_scraper.convert_currencies_to_euro(results)
    
    # Sort results by price
    sorted_results = sorted(results, key=lambda x: x[0])

    return jsonify({"results": [
        {"price": price, "link": link, "country": country_code}
        for price, _, link, country_code, _ in sorted_results
    ]})

if __name__ == "__main__":
    app.run(debug=True)

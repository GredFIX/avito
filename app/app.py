from flask import Flask, request, jsonify
import psycopg2
import datetime
import re


def conn():
    return psycopg2.connect(
        database="metrics_db", user="admin", host="db", password="admin", port="5432"
    )


def validate(request, var):
    try:
        x = request.json[var]
        return x
    except KeyError:
        return None


# Init app
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Create a metrics
@app.route("/metrics", methods=["POST"])
def add_metrics():
    try:
        date = request.json["date"]
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except KeyError as e:
        return jsonify(error="no 'date' in request")
    except ValueError as e:
        return jsonify(error="incorrect 'date' type")

    views = validate(request, "views")
    clicks = validate(request, "clicks")
    cost = validate(request, "cost")

    if (views is not None) and (
        (not str(views).isdigit()) or (int(views) > 2147483647)
    ):
        return jsonify(error="incorrect 'views' type")
    if (clicks is not None) and (
        (not str(clicks).isdigit()) or (int(clicks) > 2147483647)
    ):
        return jsonify(error="incorrect 'clicks' type")
    if (cost is not None) and (not re.search(r"^\d{1,16}\,\d\d\s[₽]$", str(cost))):
        return jsonify(error="incorrect 'cost' type")
    con = conn()
    cur = con.cursor()
    cur.execute(
        """INSERT INTO metrics (DATE_M,VIEWS,CLICKS,COST)
  				VALUES (%(date)s, %(views)s, %(clicks)s, %(cost)s)""",
        {"date": date, "views": views, "clicks": clicks, "cost": cost},
    )
    con.commit()
    return jsonify(status="OK")


# Get metricss
@app.route("/metrics/<date>&<date1>", methods=["GET"])
def get_metrics(date, date1):
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return jsonify(error="incorrect 'date' type")

    try:
        datetime.datetime.strptime(date1, "%Y-%m-%d")
    except ValueError:
        return jsonify(error="incorrect 'date1' type")

    con = conn()
    cur = con.cursor()
    cur.execute(
        """SELECT date_m, SUM(views) AS views, SUM(clicks) AS clicks, SUM(cost) AS cost FROM metrics
  				WHERE date_m BETWEEN SYMMETRIC %(date)s AND %(date1)s
  				GROUP BY date_m
  				ORDER BY date_m""",
        {"date": date, "date1": date1},
    )
    r = [
        dict((cur.description[i][0], value) for i, value in enumerate(row))
        for row in cur.fetchall()
    ]
    for d in r:
        date_m = d.get("date_m").strftime("%Y-%m-%d")
        if d.get("cost") is None:
            cpc_m = cpm_m = None
        else:
            cost = d.get("cost").replace("\u202f", "")
            d.update(cost=cost)
            cost = float(re.search(r"\d*\.\d*", cost.replace(",", ".")).group(0))
            try:
                cpc_m = (
                    None
                    if d.get("clicks") is None
                    else "{:.2f} ₽".format(cost / d.get("clicks")).replace(".", ",")
                )
            except ZeroDivisionError:
                cpc_m = "0,00 ₽"

            try:
                cpm_m = (
                    None
                    if d.get("views") is None
                    else "{:.2f} ₽".format(cost / d.get("views") * 1000).replace(
                        ".", ","
                    )
                )
            except ZeroDivisionError:
                cpm_m = "0,00 ₽"
        d.update(date_m=date_m, cpc=cpc_m, cpm=cpm_m)
    return jsonify(r)


# Delete metrics
@app.route("/metrics", methods=["DELETE"])
def delete_metrics():
    con = conn()
    cur = con.cursor()
    cur.execute("DELETE FROM metrics")
    con.commit()
    return jsonify(status="OK")


# Run Server
if __name__ == "__main__":
    app.run(host="0.0.0.0")

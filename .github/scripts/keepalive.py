"""Mantiene Cumpleping activo: renueva la web app gratuita de PythonAnywhere (caduca cada mes),
comprueba que responde y reactiva el job de cron-job.org si se desactivó.

Variables: PA_USERNAME, PA_PASSWORD, PA_API_TOKEN, CRONJOB_API_KEY. Falla (exit 1) ante cualquier problema para que GitHub avise por email.
"""
import json
import os
import sys
import urllib.request
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

USER = os.environ["PA_USERNAME"]
DOMAIN = f"{USER}.pythonanywhere.com"
API = f"https://www.pythonanywhere.com/api/v0/user/{USER}/webapps/{DOMAIN}/"


def request(url, token, method="GET", body=None, scheme="Token"):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    req.add_header("Authorization", f"{scheme} {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"{}")


def expiry():
    return date.fromisoformat(request(API, os.environ["PA_API_TOKEN"])["expiry"])


def extend_pythonanywhere():
    before = expiry()
    print(f"Caducidad antes: {before}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto("https://www.pythonanywhere.com/login/")
            page.fill('input[name="auth-username"]', USER)
            page.fill('input[name="auth-password"]', os.environ["PA_PASSWORD"])
            page.get_by_role("button", name="Log in").click()
            page.wait_for_load_state("networkidle")
            page.goto(f"https://www.pythonanywhere.com/user/{USER}/webapps/")
            page.get_by_text("Run until", exact=False).first.click()
            page.wait_for_load_state("networkidle")
        except Exception:
            page.screenshot(path="keepalive-error.png", full_page=True)
            raise
        finally:
            browser.close()
    after = expiry()
    print(f"Caducidad después: {after}")
    if after < date.today() + timedelta(days=20):
        sys.exit(f"La caducidad no avanzó ({after}): el botón no se pulsó o el login falló")


def check_web():
    code = urllib.request.urlopen(f"https://{DOMAIN}/", timeout=30).status
    print(f"Web HTTP {code}")
    if code != 200:
        sys.exit(f"La web responde {code}")


def reactivate_cronjob():
    key = os.environ["CRONJOB_API_KEY"]
    jobs = [j for j in request("https://api.cron-job.org/jobs", key, scheme="Bearer")["jobs"] if DOMAIN in j["url"]]
    if not jobs:
        sys.exit("No hay ningún job de cron-job.org que apunte a la web")
    for j in jobs:
        if not j["enabled"]:
            request(f"https://api.cron-job.org/jobs/{j['jobId']}", key, "PATCH", {"job": {"enabled": True}}, "Bearer")
            print(f"Job {j['jobId']} estaba desactivado: reactivado")
        else:
            print(f"Job {j['jobId']} activo")


if __name__ == "__main__":
    extend_pythonanywhere()
    check_web()
    reactivate_cronjob()

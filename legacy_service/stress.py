# Нагрузка на сервис: 10 клиентов одновременно бронируют одну комнату.
import json
import threading
import urllib.request

URL = "http://127.0.0.1:8080"
ROOM = 101
DAY = "2026-10-27"
CLIENTS = 10

results = []
lock = threading.Lock()
barrier = threading.Barrier(CLIENTS)


def post(path, payload):
    req = urllib.request.Request(URL + path, method="POST",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def client(n):
    barrier.wait()
    code, body = post("/bookings", {"room": ROOM, "day": DAY, "hour": 9 + n % 10, "user": "user%d" % n})
    with lock:
        results.append((code, body))


if __name__ == "__main__":
    threads = [threading.Thread(target=client, args=(i,)) for i in range(CLIENTS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    created = sum(1 for c, _ in results if c == 201)
    denied = sum(1 for c, _ in results if c == 409)

    with urllib.request.urlopen("%s/bookings?room=%d&day=%s" % (URL, ROOM, DAY)) as resp:
        stored = [b for b in json.loads(resp.read().decode("utf-8")) if b["status"] == "active"]

    print()
    print("клиентов:            ", CLIENTS)
    print("ответов 201 Created: ", created)
    print("ответов 409 Conflict:", denied)
    print("активных броней в БД:", len(stored))
    print("лимит по условию:     5")
    if len(stored) > 5:
        print("КВОТА НАРУШЕНА: записано больше лимита")
    else:
        print("квота соблюдена")

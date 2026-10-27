# Система бронирования переговорных комнат.
# Учебная версия сервиса: пишем быстро, отладка через print.
import json
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

rooms = [
    {"id": 101, "name": "Переговорная 101", "seats": 8, "floor": 1},
    {"id": 102, "name": "Переговорная 102", "seats": 12, "floor": 1},
    {"id": 201, "name": "Переговорная 201", "seats": 4, "floor": 2},
]

bookings = []
next_id = 1


def find_room(room_id):
    for r in rooms:
        if r["id"] == room_id:
            return r
    return None


def slots_for(room_id, day):
    free = []
    for h in range(9, 19):
        busy = False
        for b in bookings:
            if b["room"] == room_id and b["day"] == day and b["hour"] == h and b["status"] == "active":
                busy = True
        if not busy:
            free.append(h)
    return free


def create_booking(room_id, day, hour, user):
    global next_id
    print("create_booking: room=", room_id, "day=", day, "hour=", hour, "user=", user)

    if find_room(room_id) is None:
        print("нет такой комнаты")
        return None, "room not found"

    if hour < 9 or hour > 18:
        print("час вне диапазона", hour)
        return None, "hour out of range"

    cnt = 0
    for b in bookings:
        if b["room"] == room_id and b["day"] == day and b["status"] == "active":
            cnt = cnt + 1
    print("занято сейчас:", cnt)

    time.sleep(random.uniform(0.001, 0.004))

    if cnt < 5:
        booking = {
            "id": next_id,
            "room": room_id,
            "day": day,
            "hour": hour,
            "user": user,
            "status": "active",
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        next_id = next_id + 1
        time.sleep(0.002)
        bookings.append(booking)
        print("бронь создана, id =", booking["id"])
        return booking, None

    print("квота исчерпана")
    return None, "quota exceeded"


def cancel_booking(booking_id):
    for b in bookings:
        if b["id"] == booking_id:
            b["status"] = "cancelled"
            print("отменена бронь", booking_id)
            return True
    print("бронь не найдена", booking_id)
    return False


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        query = parse_qs(parsed.query)
        print("GET", self.path)

        if parts == ["health"]:
            self._send(200, {"status": "ok", "bookings": len(bookings)})
            return

        if parts == ["rooms"]:
            self._send(200, rooms)
            return

        if len(parts) == 3 and parts[0] == "rooms" and parts[2] == "slots":
            room_id = int(parts[1])
            day = query.get("day", ["2026-10-27"])[0]
            if find_room(room_id) is None:
                self._send(404, {"error": "room not found"})
                return
            self._send(200, {"room": room_id, "day": day, "free": slots_for(room_id, day)})
            return

        if parts == ["bookings"]:
            result = bookings
            if "room" in query:
                result = [b for b in result if b["room"] == int(query["room"][0])]
            if "day" in query:
                result = [b for b in result if b["day"] == query["day"][0]]
            self._send(200, result)
            return

        self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        print("POST", self.path, raw)

        if parts != ["bookings"]:
            self._send(404, {"error": "not found"})
            return

        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            print("битый json", e)
            self._send(400, {"error": "bad json"})
            return

        booking, err = create_booking(data["room"], data["day"], data["hour"], data["user"])
        if err is not None:
            self._send(409, {"error": err})
            return
        self._send(201, booking)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        print("DELETE", self.path)
        if len(parts) == 2 and parts[0] == "bookings":
            if cancel_booking(int(parts[1])):
                self._send(200, {"result": "cancelled"})
            else:
                self._send(404, {"error": "booking not found"})
            return
        self._send(404, {"error": "not found"})


class ThreadedServer(HTTPServer):
    daemon_threads = True

    def process_request(self, request, client_address):
        t = threading.Thread(target=self.__handle, args=(request, client_address))
        t.daemon = True
        t.start()

    def __handle(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception as e:
            print("ошибка обработки:", e)
        finally:
            self.shutdown_request(request)


if __name__ == "__main__":
    print("запуск сервера на порту 8080")
    ThreadedServer(("127.0.0.1", 8080), Handler).serve_forever()

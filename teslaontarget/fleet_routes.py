"""Bridge Tesla Fleet Telemetry navigation fields from MQTT into TAK."""

import base64
import hashlib
import json
import logging
import math
import os
import threading
import time

import paho.mqtt.client as mqtt

from .cot import (format_cot_for_tak, generate_cot_packet,
                  generate_delete_packet, generate_destination_packet,
                  generate_route_packet)
from .tak_client import TAKClient

logger = logging.getLogger(__name__)
MAX_TAK_PACKET_BYTES = 60_000


def decode_polyline(encoded, precision=6):
    """Decode Google's signed-delta polyline format used by RouteLine."""
    points, index, lat, lon, scale = [], 0, 0, 0, 10 ** precision
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            result = shift = 0
            while True:
                if index >= len(encoded):
                    raise ValueError("truncated polyline")
                value = ord(encoded[index]) - 63
                index += 1
                result |= (value & 0x1F) << shift
                shift += 5
                if value < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lon += deltas[1]
        points.append((lat / scale, lon / scale))
    return points


def decode_route_line(encoded):
    """Extract field 1 (Google polyline6) from Tesla's base64 protobuf."""
    data = base64.b64decode(encoded, validate=True)
    index = 0

    def varint():
        nonlocal index
        value = shift = 0
        while index < len(data):
            byte = data[index]
            index += 1
            value |= (byte & 0x7f) << shift
            if byte < 0x80:
                return value
            shift += 7
        raise ValueError("truncated RouteLine protobuf")

    while index < len(data):
        tag = varint()
        field, wire = tag >> 3, tag & 7
        if wire == 2:
            size = varint()
            value = data[index:index + size]
            index += size
            if field == 1:
                return decode_polyline(value.decode("ascii"))
        elif wire == 5:
            index += 4
        elif wire == 0:
            varint()
        else:
            raise ValueError(f"unsupported RouteLine wire type {wire}")
    return None


def simplify_route(points, tolerance):
    """Simplify a route with Ramer-Douglas-Peucker, preserving key turns."""
    if len(points) <= 2:
        return points
    keep = {0, len(points) - 1}
    pending = [(0, len(points) - 1)]
    while pending:
        start_index, end_index = pending.pop()
        start, end = points[start_index], points[end_index]
        dy, dx = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dy, dx)
        farthest, farthest_index = 0, None
        for index in range(start_index + 1, end_index):
            point = points[index]
            distance = (math.hypot(point[0] - start[0], point[1] - start[1])
                        if not length else
                        abs(dx * (point[0] - start[0]) -
                            dy * (point[1] - start[1])) / length)
            if distance > farthest:
                farthest, farthest_index = distance, index
        if farthest_index is not None and farthest > tolerance:
            keep.add(farthest_index)
            pending.extend(((start_index, farthest_index),
                            (farthest_index, end_index)))
    return [points[index] for index in sorted(keep)]


def fit_route_packet(uid, callsign, points, limit=MAX_TAK_PACKET_BYTES):
    """Use the least simplification needed to fit TAK Server's frame limit."""
    packet = generate_route_packet(uid, callsign, points)
    if len(format_cot_for_tak(packet)) <= limit:
        return packet, points

    low, high = 0, 1e-7
    while True:
        fitted = simplify_route(points, high)
        packet = generate_route_packet(uid, callsign, fitted)
        if len(format_cot_for_tak(packet)) <= limit:
            break
        low, high = high, high * 2

    best = (packet, fitted)
    for _ in range(24):
        tolerance = (low + high) / 2
        fitted = simplify_route(points, tolerance)
        packet = generate_route_packet(uid, callsign, fitted)
        if len(format_cot_for_tak(packet)) <= limit:
            high, best = tolerance, (packet, fitted)
        else:
            low = tolerance
    return best


class FleetRouteBridge:
    def __init__(self, tak_client):
        self.tak = tak_client
        self.state = {}
        self.lock = threading.Lock()

    def _send(self, packet):
        self.tak.send_cot(format_cot_for_tak(packet))

    def _clear_navigation(self, uid, vehicle):
        if not vehicle.get("route_active") and vehicle.get("navigation_cleared"):
            return
        for suffix, cot_type in (("route", "u-d-f"),
                                 ("destination", "b-m-p-s-m")):
            self._send(generate_delete_packet(
                f"{uid}-{suffix}", f"{uid}-{suffix}", cot_type))
        vehicle["route_active"] = False
        vehicle["navigation_cleared"] = True
        vehicle.pop("RouteLine", None)
        vehicle.pop("DestinationLocation", None)
        vehicle.pop("DestinationName", None)
        logger.info("Cleared active navigation for %s",
                    vehicle.get("VehicleName") or "Tesla")

    def _send_destination(self, uid, vehicle):
        location = vehicle.get("DestinationLocation")
        if not vehicle.get("route_active") or not location:
            return
        if location.get("latitude") is None or location.get("longitude") is None:
            return
        callsign = vehicle.get("VehicleName") or "Tesla"
        self._send(generate_destination_packet(
            uid, callsign, location, vehicle.get("DestinationName"), vehicle))

    def _send_position(self, uid, vehicle):
        location = vehicle.get("Location")
        if not location:
            return
        self._send(generate_cot_packet({
            "UID": uid,
            "display_name": vehicle.get("VehicleName") or "Tesla",
            "vehicle_model": vehicle.get("CarType") or "Vehicle",
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "heading": vehicle.get("GpsHeading") or 0,
            "speed": vehicle.get("VehicleSpeed") or 0,
            "battery_level": vehicle.get("Soc") or 0,
        }))

    def refresh_positions(self):
        """Refresh cached PLI so stationary vehicles do not expire in ATAK."""
        with self.lock:
            for vin, vehicle in self.state.items():
                uid = "TESLA-" + hashlib.sha256(vin.encode()).hexdigest()[:12]
                self._send_position(uid, vehicle)

    def heartbeat_forever(self, interval):
        while True:
            time.sleep(interval)
            self.refresh_positions()

    def handle(self, topic, payload):
        parts = topic.split("/")
        if len(parts) != 4 or parts[0] != "telemetry" or parts[2] != "v":
            return
        vin, field = parts[1], parts[3]
        value = json.loads(payload)
        with self.lock:
            vehicle = self.state.setdefault(vin, {})
            vehicle[field] = value
            uid = "TESLA-" + hashlib.sha256(vin.encode()).hexdigest()[:12]
            callsign = vehicle.get("VehicleName") or "Tesla"
            if field == "Location":
                self._send_position(uid, vehicle)
            if field == "RouteLine" and not value:
                self._clear_navigation(uid, vehicle)
            elif field == "RouteLine":
                points = decode_route_line(value)
                if not points:
                    self._clear_navigation(uid, vehicle)
                    logger.warning("RouteLine for %s contains no geometry",
                                   callsign)
                else:
                    vehicle["route_active"] = True
                    vehicle["navigation_cleared"] = False
                    packet, fitted = fit_route_packet(uid, callsign, points)
                    self._send(packet)
                    self._send_destination(uid, vehicle)
                    logger.info("Sent active route for %s (%d/%d points)",
                                callsign, len(fitted), len(points))
            if field == "VehicleName":
                self._send_position(uid, vehicle)
                encoded = vehicle.get("RouteLine")
                if vehicle.get("route_active") and encoded:
                    points = decode_route_line(encoded)
                    if points:
                        packet, _ = fit_route_packet(uid, callsign, points)
                        self._send(packet)
            if field in {"DestinationLocation", "DestinationName", "VehicleName",
                         "MilesToArrival", "MinutesToArrival",
                         "RouteTrafficMinutesDelay",
                         "ExpectedEnergyPercentAtTripArrival"}:
                self._send_destination(uid, vehicle)


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    tak = TAKClient(f"tcp://{os.environ['TAK_SERVER']}:{os.getenv('TAK_PORT', '8085')}")
    bridge = FleetRouteBridge(tak)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id="teslaontarget-fleet-routes")
    client.on_connect = lambda c, _u, _f, _r, _p: c.subscribe("telemetry/+/v/+", qos=1)
    client.on_message = lambda _c, _u, message: bridge.handle(message.topic, message.payload)
    client.connect(os.getenv("FLEET_MQTT_HOST", "127.0.0.1"),
                   int(os.getenv("FLEET_MQTT_PORT", "1883")))
    threading.Thread(
        target=bridge.heartbeat_forever,
        args=(int(os.getenv("PLI_HEARTBEAT_SECONDS", "60")),),
        daemon=True,
    ).start()
    client.loop_forever()


if __name__ == "__main__":
    main()

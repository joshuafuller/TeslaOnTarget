import base64
import json
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from teslaontarget.cot import (generate_delete_packet,
                               generate_destination_packet,
                               generate_route_packet)
from teslaontarget.fleet_routes import (FleetRouteBridge, decode_polyline,
                                        decode_route_line, main)

ROUTE = b'"CiBfaXpsaEF+cmxnZEZfe2dlQ355d2xAX2t3ekNuYHtuSQ=="'


def test_precision_six_polyline_and_atak_overlay():
    # Precision-6 encoding of (38.5,-120.2), (40.7,-120.95), (43.252,-126.453).
    points = decode_polyline("_izlhA~rlgdF_{geC~ywl@_kwzCn`{nI")
    assert points == [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
    root = ET.fromstring(generate_route_packet("TESLA-test", "Tron", points))
    assert root.get("type") == "u-d-f"
    assert root.get("uid") == "TESLA-test-route"
    assert [link.get("point") for link in root.findall("./detail/link")] == [
        "38.5,-120.2", "40.7,-120.95", "43.252,-126.453"]


def test_route_line_extracts_polyline_from_tesla_protobuf():
    value = "CiBfaXpsaEF+cmxnZEZfe2dlQ355d2xAX2t3ekNuYHtuSQ=="
    assert decode_route_line(value) == [
        (38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]


def test_route_line_without_geometry_returns_none():
    # Real Fleet Telemetry sample containing only field 2 route metrics.
    value = ("EgcNnXmEQhABEgcNmoAzQhACEgcNFKAyQhABEgcNCGaTQRACEgcNlH6RQRAB"
             "EgcN4AOPQRACEgcN95KLQRACEgcNOoCKQRACEgcNE62IQRABEgcNTeqGQRAC"
             "EgcNadmEQRABEgcNVaFvQRACEgcNpC1sQRABEgcNJzJXQBACEgcNSx85QBAB"
             "EgUNjq7CPhIHDU7x2D0QAQ==")
    assert decode_route_line(value) is None


@pytest.mark.parametrize("raw", [b"\x15\0\0\0\0", b"\x10\x01"])
def test_route_line_skips_known_non_geometry_wire_types(raw):
    assert decode_route_line(base64.b64encode(raw).decode()) is None


@pytest.mark.parametrize("raw, message", [
    (b"\x80", "truncated RouteLine protobuf"),
    (b"\x09", "unsupported RouteLine wire type 1"),
])
def test_route_line_rejects_malformed_protobuf(raw, message):
    with pytest.raises(ValueError, match=message):
        decode_route_line(base64.b64encode(raw).decode())


def test_bridge_does_not_send_fake_route_for_metrics_only_route_line():
    tak = Mock()
    bridge = FleetRouteBridge(tak)
    base = "telemetry/VIN/v"
    bridge.handle(f"{base}/DestinationLocation",
                  b'{"latitude":30.422536,"longitude":-86.696005}')
    bridge.handle(f"{base}/RouteLine", json.dumps(
        "EgcNnXmEQhABEgcNmoAzQhACEgcNFKAyQhABEgcNCGaTQRAC"
        "EgcNlH6RQRABEgcN4AOPQRACEgcN95KLQRAC").encode())
    packets = [ET.fromstring(call.args[0]) for call in tak.send_cot.call_args_list]
    assert [packet.get("type") for packet in packets] == ["b-m-p-s-m"]


def test_invalid_route_inputs():
    with pytest.raises(ValueError, match="truncated"):
        decode_polyline("_")
    with pytest.raises(ValueError, match="at least two"):
        generate_route_packet("id", "Tron", [(1, 2)])


def test_destination_is_named_spot_marker_with_fallback():
    named = ET.fromstring(generate_destination_packet(
        "id", "Tron", {"latitude": 1, "longitude": 2}, "Publix", {
            "MilesToArrival": 12.34,
            "MinutesToArrival": 24.4,
            "RouteTrafficMinutesDelay": 5.2,
            "ExpectedEnergyPercentAtTripArrival": 42,
        }))
    assert named.get("type") == "b-m-p-s-m"
    assert named.find("./detail/contact").get("callsign") == "Publix"
    assert named.find("./detail/color").get("argb") == "-16711681"
    assert named.findtext("./detail/remarks") == (
        "Active destination for Tron | 12.3 mi | 24 min | "
        "Traffic +5 min | 42% at arrival")
    fallback = ET.fromstring(generate_destination_packet(
        "id", "Tron", {"latitude": 1, "longitude": 2}))
    assert fallback.find("./detail/contact").get("callsign") == "Tron destination"


def test_delete_packet_force_deletes_target_uid():
    root = ET.fromstring(generate_delete_packet(
        "delete-id", "TESLA-test-route", "u-d-f"))
    assert root.get("type") == "t-x-d-d"
    assert root.find("./detail/link").attrib == {
        "uid": "TESLA-test-route", "relation": "none", "type": "u-d-f"}
    assert root.find("./detail/__forcedelete") is not None


def test_bridge_ignores_other_topics_and_sends_route_and_destination():
    tak = Mock()
    bridge = FleetRouteBridge(tak)
    bridge.handle("other/topic", b"null")
    assert not tak.send_cot.called

    base = "telemetry/VIN/v"
    bridge.handle(f"{base}/VehicleName", b'"Tron"')
    bridge.handle(f"{base}/DestinationLocation", b'{"latitude":1,"longitude":2}')
    bridge.handle(f"{base}/DestinationName", b'"Publix"')
    bridge.handle(f"{base}/RouteLine", ROUTE)
    assert tak.send_cot.call_count == 2
    assert b"u-d-f" in tak.send_cot.call_args_list[-2].args[0]
    assert b"Publix" in tak.send_cot.call_args.args[0]


def test_bridge_replaces_one_route_per_vehicle_and_clears_navigation():
    tak = Mock()
    bridge = FleetRouteBridge(tak)
    route = ROUTE
    bridge.handle("telemetry/VIN/v/RouteLine", route)
    first = ET.fromstring(tak.send_cot.call_args.args[0])
    bridge.handle("telemetry/VIN/v/RouteLine", route)
    replacement = ET.fromstring(tak.send_cot.call_args.args[0])
    assert first.get("uid") == replacement.get("uid")

    bridge.handle("telemetry/VIN/v/RouteLine", b"null")
    deletes = [ET.fromstring(call.args[0]) for call in tak.send_cot.call_args_list[-2:]]
    assert [event.find("./detail/link").get("uid") for event in deletes] == [
        first.get("uid"), first.get("uid").replace("-route", "-destination")]
    assert all(event.get("type") == "t-x-d-d" for event in deletes)

    count = tak.send_cot.call_count
    bridge.handle("telemetry/VIN/v/RouteLine", b"null")
    assert tak.send_cot.call_count == count


def test_bridge_refreshes_active_destination_metadata_only_with_valid_location():
    tak = Mock()
    bridge = FleetRouteBridge(tak)
    base = "telemetry/VIN/v"
    bridge.handle(f"{base}/RouteLine", ROUTE)
    bridge.handle(f"{base}/DestinationLocation", b'{"latitude":null,"longitude":2}')
    assert tak.send_cot.call_count == 1
    bridge.handle(f"{base}/DestinationLocation", b'{"latitude":1,"longitude":2}')
    bridge.handle(f"{base}/MilesToArrival", b"12.3")
    assert b"12.3 mi" in tak.send_cot.call_args.args[0]


def test_bridge_sends_and_refreshes_fleet_position():
    tak = Mock()
    bridge = FleetRouteBridge(tak)
    base = "telemetry/VIN/v"
    bridge.handle(f"{base}/VehicleName", b'"Tron"')
    bridge.handle(f"{base}/GpsHeading", b"123")
    bridge.handle(f"{base}/VehicleSpeed", b"45")
    bridge.handle(f"{base}/Soc", b"67")
    bridge.handle(f"{base}/Location", b'{"latitude":30.4,"longitude":-86.9}')
    packet = ET.fromstring(tak.send_cot.call_args.args[0])
    assert packet.find("point").attrib["lat"] == "30.4"
    assert packet.find("./detail/contact").get("callsign") == "Tron"
    assert packet.find("./detail/track").get("course") == "123.00000000"
    assert packet.find("./detail/status").get("battery") == "67"

    bridge.refresh_positions()
    assert tak.send_cot.call_count == 2


def test_position_refresh_ignores_vehicle_without_location():
    tak = Mock()
    bridge = FleetRouteBridge(tak)
    bridge.state["VIN"] = {"VehicleName": "Tron"}
    bridge.refresh_positions()
    assert not tak.send_cot.called


def test_heartbeat_waits_then_refreshes():
    bridge = FleetRouteBridge(Mock())
    with patch("teslaontarget.fleet_routes.time.sleep",
               side_effect=[None, KeyboardInterrupt]), \
         patch.object(bridge, "refresh_positions") as refresh:
        with pytest.raises(KeyboardInterrupt):
            bridge.heartbeat_forever(10)
    refresh.assert_called_once()


def test_main_wires_mqtt_callbacks(monkeypatch):
    monkeypatch.setenv("TAK_SERVER", "tak.example")
    monkeypatch.setenv("TAK_PORT", "8085")
    monkeypatch.setenv("FLEET_MQTT_HOST", "mqtt.example")
    monkeypatch.setenv("FLEET_MQTT_PORT", "1884")
    client = Mock()
    with patch("teslaontarget.fleet_routes.TAKClient") as tak_cls, \
         patch("teslaontarget.fleet_routes.mqtt.Client", return_value=client), \
         patch("teslaontarget.fleet_routes.threading.Thread") as thread:
        main()
    tak_cls.assert_called_once_with("tcp://tak.example:8085")
    client.connect.assert_called_once_with("mqtt.example", 1884)
    client.loop_forever.assert_called_once()
    thread.return_value.start.assert_called_once()
    subscriber = Mock()
    client.on_connect(subscriber, None, None, None, None)
    subscriber.subscribe.assert_called_once_with("telemetry/+/v/+", qos=1)
    with patch.object(FleetRouteBridge, "handle") as handle:
        client.on_message(None, None, SimpleNamespace(topic="a", payload=b"b"))
    handle.assert_called_once_with("a", b"b")

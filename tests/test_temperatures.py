"""Run with python3 tests/test_temperatures.py; no Home Assistant dependency."""

import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "helpers", Path(__file__).parent.parent / "custom_components/pulse_monitor/helpers.py"
)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


class TemperatureTests(unittest.TestCase):
    def test_native_resource_payload(self):
        resource = {
            "temperature": 53,
            "agent": {
                "temperature": 53,
                "sensors": {
                    "temperatureCelsius": {
                        "cpu_core_0": 52,
                        "cpu_package": 53,
                        "nvme0": 57.85,
                    },
                    "additional": {"acpitz_temp1": 27.8, "voltage": 12},
                    "fanRpm": {"fan0": 1500},
                    "powerWatts": {"cpu_package": 15},
                    "custom": [{"id": "not_native", "value": 99}],
                },
            },
        }
        original = deepcopy(resource)
        readings = h.temperature_readings(resource)
        self.assertEqual(len(readings), 4)
        self.assertEqual(readings["temperature"]["value"], 53)
        self.assertEqual(
            readings["temperature_sensor_cpu_package"]["name"], "CPU package temperature"
        )
        self.assertEqual(readings["temperature_sensor_nvme0"]["value"], 57.85)
        self.assertEqual(resource, original)

    def test_absent_temperature_does_not_become_zero(self):
        for resource in (None, {}, {"agent": {}}, {"agent": {"sensors": None}}):
            with self.subTest(resource=resource):
                self.assertEqual(h.temperature_readings(resource), {})

    def test_primary_prefers_agent_then_resource(self):
        readings = h.temperature_readings({"agent": {"temperature": 42}, "temperature": 99})
        self.assertEqual(readings["temperature"]["value"], 42)
        readings = h.temperature_readings({"temperature": 47})
        self.assertEqual(readings["temperature"]["value"], 47)

    def test_zero_and_negative_typed_temperatures_are_valid(self):
        resource = {
            "agent": {"temperature": 0, "sensors": {"temperatureCelsius": {"outdoor": -5}}}
        }
        readings = h.temperature_readings(resource)
        self.assertEqual(readings["temperature"]["value"], 0)
        self.assertEqual(readings["temperature_sensor_outdoor"]["value"], -5)

    def test_invalid_numbers_are_rejected(self):
        for value in (None, True, False, "53", float("nan"), float("inf"), -float("inf"), {}, []):
            with self.subTest(value=value):
                resource = {
                    "agent": {
                        "temperature": value,
                        "sensors": {"temperatureCelsius": {"cpu": value}},
                    }
                }
                self.assertEqual(h.temperature_readings(resource), {})

    def test_late_readings_and_disappearance(self):
        resource = {"agent": {"sensors": {"temperatureCelsius": {}}}}
        self.assertEqual(h.temperature_readings(resource), {})
        resource["agent"]["sensors"]["temperatureCelsius"]["cpu_package"] = 50
        self.assertIn("temperature_sensor_cpu_package", h.temperature_readings(resource))
        del resource["agent"]["sensors"]["temperatureCelsius"]["cpu_package"]
        self.assertEqual(h.temperature_readings(resource), {})

    def test_gpu_identity_survives_reordering(self):
        gpus = [
            {"id": "pci-1", "name": "Example GPU", "temperatureCelsius": 65},
            {"id": "pci-2", "temperatureCelsius": 50},
        ]
        first = h.temperature_readings({"agent": {"sensors": {"gpu": gpus}}})
        second = h.temperature_readings({"agent": {"sensors": {"gpu": list(reversed(gpus))}}})
        self.assertEqual(first, second)
        self.assertEqual(first["temperature_gpu_pci-1"]["value"], 65)

    def test_disk_identity_survives_device_renaming(self):
        disk = {
            "device": "sda",
            "serial": "example-serial",
            "wwn": "example-wwn",
            "temperature": 35,
            "collection": {"temperature": {"state": "available"}},
        }
        first = h.temperature_readings({"agent": {"sensors": {"smart": [disk]}}})
        disk["device"] = "sdb"
        second = h.temperature_readings({"agent": {"sensors": {"smart": [disk]}}})
        self.assertEqual(set(first), set(second))
        self.assertEqual(first["temperature_disk_example-wwn"]["value"], 35)

    def test_smart_missing_standby_and_failed_collection(self):
        for patch in (
            {"temperature": 0},
            {"temperature": -1},
            {"temperature": True},
            {"standby": True},
            {"collection": {"temperature": {"state": "unavailable"}}},
        ):
            with self.subTest(patch=patch):
                disk = {"device": "sda", "temperature": 35, **patch}
                self.assertEqual(h.temperature_readings({"agent": {"sensors": {"smart": [disk]}}}), {})

    def test_legacy_smart_and_identity_fallback(self):
        for extra, key in (({"serial": "serial-1"}, "serial-1"), ({}, "sda")):
            disk = {"device": "sda", "temperature": 35, **extra}
            readings = h.temperature_readings({"agent": {"sensors": {"smart": [disk]}}})
            self.assertIn(f"temperature_disk_{key}", readings)

    def test_malformed_optional_collections(self):
        resource = {
            "agent": {
                "sensors": {
                    "temperatureCelsius": [],
                    "gpu": [None, {}, "invalid"],
                    "smart": [None, {}, "invalid"],
                }
            }
        }
        self.assertEqual(h.temperature_readings(resource), {})


if __name__ == "__main__":
    unittest.main()

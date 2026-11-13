"""Product types and specification templates for the GEANT catalog.

This is the single source of truth used by:
- the admin product form (which spec fields to show for each product type),
- the storefront (readable spec labels, and mapping store categories such as "Lavage"
  to the product types stored in ``products.category``).

Stored ``products.category`` values are the product type keys below (``laptop``, ``tv``,
``smartphone`` ... ), so existing data and the AI assistant keep working unchanged.
The spec keys ``ram_gb``, ``storage_gb``, ``screen_inches`` and ``refresh_rate_hz`` and their
units (GB, GB, inch, Hz) are the ones the AI assistant can filter on - keep them identical.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

YES_NO = ("Yes", "No")
ENERGY = ("A+++", "A++", "A+", "A", "B", "C", "D", "E", "F", "G")


@dataclass(frozen=True)
class SpecField:
    key: str
    label: str
    kind: str = "text"  # "number" | "text" | "select"
    unit: str | None = None
    options: tuple[str, ...] = ()  # suggestions (number/text) or the allowed values (select)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "unit": self.unit,
            "options": list(self.options),
        }


@dataclass(frozen=True)
class ProductType:
    key: str
    label: str
    group: str
    fields: tuple[SpecField, ...]


def _num(key: str, label: str, unit: str | None = None, *options: object) -> SpecField:
    return SpecField(key, label, "number", unit, tuple(str(o) for o in options))


def _sel(key: str, label: str, *options: str) -> SpecField:
    return SpecField(key, label, "select", None, tuple(options))


def _txt(key: str, label: str, *options: str) -> SpecField:
    return SpecField(key, label, "text", None, tuple(options))


# Every spec is defined once so that a key always has the same label and unit.
REGISTRY: dict[str, SpecField] = {
    f.key: f
    for f in (
        _txt("processor", "Processor", "Intel Core i3", "Intel Core i5", "Intel Core i7",
             "Intel Core i9", "AMD Ryzen 3", "AMD Ryzen 5", "AMD Ryzen 7", "Apple M-series",
             "Snapdragon", "MediaTek", "Exynos"),
        _num("ram_gb", "RAM", "GB", 2, 3, 4, 6, 8, 12, 16, 24, 32, 64),
        _num("storage_gb", "Storage", "GB", 32, 64, 128, 256, 512, 1000, 2000),
        _sel("storage_type", "Storage type", "SSD", "HDD", "SSD + HDD", "eMMC"),
        _num("screen_inches", "Screen size", "inch", 13.3, 14, 15.6, 16, 17.3),
        _txt("graphics", "Graphics card", "Integrated", "NVIDIA GeForce RTX", "NVIDIA GeForce GTX",
             "AMD Radeon"),
        _sel("operating_system", "Operating system", "Windows 11", "Windows 10", "Linux", "macOS",
             "FreeDOS / No OS", "Android", "iOS"),
        _num("weight_kg", "Weight", "kg"),
        _num("battery_mah", "Battery", "mAh", 3000, 4000, 5000, 6000),
        _num("rear_camera_mp", "Rear camera", "MP", 12, 48, 50, 64, 108, 200),
        _num("front_camera_mp", "Front camera", "MP", 8, 12, 16, 32),
        _sel("network", "Network", "4G", "5G"),
        _sel("dual_sim", "Dual SIM", *YES_NO),
        _sel("resolution", "Resolution", "HD", "Full HD", "2K (QHD)", "4K", "8K"),
        _sel("display_type", "Display type", "LCD", "IPS", "AMOLED", "OLED", "LED", "QLED",
             "Mini LED", "NanoCell"),
        _num("refresh_rate_hz", "Refresh rate", "Hz", 50, 60, 75, 90, 100, 120, 144, 165, 240),
        _sel("smart_tv", "Smart TV", *YES_NO),
        _sel("built_in_receiver", "Built-in satellite receiver", *YES_NO),
        _num("hdmi_ports", "HDMI ports", None, 1, 2, 3, 4),
        _sel("panel_type", "Panel type", "IPS", "VA", "TN", "OLED"),
        _num("response_time_ms", "Response time", "ms", 1, 4, 5, 8),
        _sel("form_factor", "Form factor", "Tower", "Mini PC", "All-in-one"),
        _sel("printer_type", "Printer type", "Inkjet", "Laser", "Multifunction", "Thermal"),
        _sel("color_printing", "Printing", "Colour", "Monochrome"),
        _num("print_speed_ppm", "Print speed", "ppm"),
        _txt("connectivity", "Connectivity", "Wi-Fi", "Bluetooth", "USB", "Ethernet",
             "Wi-Fi + Bluetooth"),
        _sel("speaker_type", "Speaker type", "Bluetooth speaker", "Soundbar", "Home theatre",
             "Party speaker"),
        _num("power_w", "Power", "W"),
        _num("battery_hours", "Battery life", "h"),
        _sel("headphone_type", "Headphone type", "In-ear", "On-ear", "Over-ear"),
        _sel("wireless", "Wireless", *YES_NO),
        _sel("noise_cancelling", "Noise cancelling", *YES_NO),
        _num("capacity_kg", "Capacity", "kg", 5, 6, 7, 8, 9, 10, 12),
        _num("spin_speed_rpm", "Spin speed", "rpm", 800, 1000, 1200, 1400, 1600),
        _sel("loading_type", "Loading type", "Front loading", "Top loading"),
        _sel("energy_class", "Energy class", *ENERGY),
        _sel("inverter", "Inverter", *YES_NO),
        _sel("dryer_type", "Dryer type", "Heat pump", "Condenser", "Vented"),
        _num("place_settings", "Place settings", None, 9, 12, 13, 14, 15),
        _num("width_cm", "Width", "cm", 45, 55, 60, 70, 90),
        _num("height_cm", "Height", "cm"),
        _num("capacity_l", "Capacity", "L"),
        _sel("fridge_type", "Fridge type", "Single door", "Double door", "Combi (fridge + freezer)",
             "Side by side", "French door"),
        _sel("no_frost", "No Frost", *YES_NO),
        _sel("freezer_type", "Freezer type", "Chest", "Upright"),
        _num("drawers", "Drawers", None, 3, 4, 5, 6),
        _num("cooling_btu", "Cooling capacity", "BTU", 9000, 12000, 18000, 24000, 30000),
        _sel("ac_type", "Air conditioner type", "Split", "Window", "Portable", "Cassette",
             "Floor standing"),
        _sel("ac_mode", "Mode", "Cooling only", "Cooling & heating"),
        _sel("oven_type", "Installation", "Built-in", "Freestanding", "Countertop"),
        _sel("fuel", "Fuel / energy", "Gas", "Electric", "Induction", "Mixed (gas + electric)",
             "Wood", "Fuel oil"),
        _num("burners", "Burners", None, 2, 3, 4, 5),
        _sel("microwave_type", "Microwave type", "Solo", "With grill", "Combi"),
        _num("airflow_m3h", "Airflow", "m³/h"),
        _sel("hood_type", "Hood type", "Wall mounted", "Island", "Built-in", "Telescopic"),
        _sel("heater_type", "Heater type", "Gas heater", "Electric heater", "Oil radiator",
             "Fan heater", "Stove", "Convector"),
        _sel("blender_type", "Blender type", "Countertop", "Hand blender", "Personal"),
        _sel("vacuum_type", "Vacuum type", "Bagged", "Bagless", "Robot", "Handheld", "Wet & dry"),
        _num("dust_capacity_l", "Dust capacity", "L"),
        _sel("coffee_type", "Coffee machine type", "Espresso", "Capsule", "Filter", "Bean to cup"),
        _num("pressure_bar", "Pressure", "bar", 15, 19, 20),
        _sel("iron_type", "Iron type", "Steam", "Dry", "Steam station"),
        _num("warranty_months", "Warranty", "months", 6, 12, 24, 36),
        _txt("color", "Color", "Black", "White", "Silver", "Grey", "Blue", "Red", "Gold"),
    )
}

# Shown for every product type (after the type-specific fields).
COMMON_KEYS = ("warranty_months", "color")


def _f(key: str, *options: object) -> SpecField:
    """Registry field, optionally with type-specific suggestions/options."""
    field = REGISTRY[key]
    if options:
        return replace(field, options=tuple(str(o) for o in options))
    return field


def _type(key: str, label: str, group: str, *fields: SpecField) -> ProductType:
    specific = [f for f in fields if f.key not in COMMON_KEYS]
    return ProductType(key, label, group, tuple(specific) + tuple(REGISTRY[k] for k in COMMON_KEYS))


GROUPS: tuple[str, ...] = (
    "Informatique",
    "Multimédia",
    "Lavage",
    "Froid",
    "Climatisation",
    "Cuisson",
    "Chauffage",
    "Petit électroménager",
)

PRODUCT_TYPES: tuple[ProductType, ...] = (
    # --- Informatique ---
    _type("laptop", "Laptop", "Informatique", _f("processor"), _f("ram_gb", 4, 8, 16, 32, 64),
          _f("storage_gb"), _f("storage_type"), _f("screen_inches"), _f("graphics"),
          _f("operating_system", "Windows 11", "Windows 10", "Linux", "macOS", "FreeDOS / No OS"),
          _f("weight_kg")),
    _type("desktop", "Desktop PC", "Informatique", _f("processor"), _f("ram_gb", 4, 8, 16, 32, 64),
          _f("storage_gb"), _f("storage_type"), _f("graphics"),
          _f("operating_system", "Windows 11", "Windows 10", "Linux", "FreeDOS / No OS"),
          _f("form_factor")),
    _type("tablet", "Tablet", "Informatique", _f("screen_inches", 8, 10.1, 10.9, 11, 12.9),
          _f("ram_gb", 2, 3, 4, 6, 8, 12), _f("storage_gb"), _f("processor"),
          _f("operating_system", "Android", "iOS", "Windows 11"), _f("battery_mah"),
          _f("network")),
    _type("monitor", "Monitor", "Informatique", _f("screen_inches", 19, 22, 24, 27, 32, 34),
          _f("resolution"), _f("panel_type"), _f("refresh_rate_hz"), _f("response_time_ms"),
          _f("hdmi_ports")),
    _type("printer", "Printer", "Informatique", _f("printer_type"), _f("color_printing"),
          _f("print_speed_ppm"), _f("connectivity")),
    # --- Multimédia ---
    _type("tv", "TV", "Multimédia", _f("screen_inches", 32, 40, 43, 50, 55, 65, 75, 85),
          _f("resolution"), _f("display_type", "LED", "QLED", "OLED", "Mini LED", "NanoCell"),
          _f("refresh_rate_hz", 50, 60, 100, 120, 144), _f("smart_tv"),
          _f("operating_system", "Android TV", "Google TV", "webOS", "Tizen", "VIDAA", "None"),
          _f("built_in_receiver"), _f("hdmi_ports")),
    _type("smartphone", "Smartphone", "Multimédia", _f("screen_inches", 5.5, 6.1, 6.5, 6.7, 6.8),
          _f("ram_gb", 3, 4, 6, 8, 12, 16), _f("storage_gb", 32, 64, 128, 256, 512, 1000),
          _f("processor", "Snapdragon", "MediaTek Helio", "MediaTek Dimensity", "Exynos",
             "Apple A-series"),
          _f("display_type", "LCD", "IPS", "AMOLED", "OLED"), _f("rear_camera_mp"),
          _f("front_camera_mp"), _f("battery_mah"), _f("network"), _f("dual_sim"),
          _f("operating_system", "Android", "iOS")),
    _type("speaker", "Speaker / Soundbar", "Multimédia", _f("speaker_type"), _f("power_w"),
          _f("connectivity"), _f("battery_hours")),
    _type("headphones", "Headphones", "Multimédia", _f("headphone_type"), _f("wireless"),
          _f("noise_cancelling"), _f("battery_hours")),
    # --- Lavage ---
    _type("washing_machine", "Washing machine", "Lavage", _f("capacity_kg"), _f("spin_speed_rpm"),
          _f("loading_type"), _f("energy_class"), _f("inverter"), _f("width_cm", 55, 60, 70)),
    _type("dryer", "Tumble dryer", "Lavage", _f("capacity_kg"), _f("dryer_type"),
          _f("energy_class"), _f("width_cm", 55, 60, 70)),
    _type("dishwasher", "Dishwasher", "Lavage", _f("place_settings"), _f("energy_class"),
          _f("width_cm", 45, 60)),
    # --- Froid ---
    _type("refrigerator", "Refrigerator", "Froid", _f("capacity_l"), _f("fridge_type"),
          _f("no_frost"), _f("energy_class"), _f("inverter"), _f("height_cm")),
    _type("freezer", "Freezer", "Froid", _f("capacity_l"), _f("freezer_type"), _f("no_frost"),
          _f("energy_class"), _f("drawers")),
    # --- Climatisation ---
    _type("air_conditioner", "Air conditioner", "Climatisation", _f("cooling_btu"), _f("ac_type"),
          _f("ac_mode"), _f("inverter"), _f("energy_class")),
    # --- Cuisson ---
    _type("cooker", "Cooker (stove + oven)", "Cuisson", _f("burners", 4, 5), _f("fuel", "Gas",
          "Electric", "Mixed (gas + electric)"), _f("capacity_l"), _f("width_cm", 50, 60, 90)),
    _type("hob", "Hob", "Cuisson", _f("burners", 2, 3, 4, 5),
          _f("fuel", "Gas", "Electric", "Induction", "Mixed (gas + electric)"),
          _f("width_cm", 30, 60, 75, 90)),
    _type("oven", "Oven", "Cuisson", _f("oven_type"), _f("fuel", "Electric", "Gas"),
          _f("capacity_l", 40, 60, 70, 90)),
    _type("microwave", "Microwave", "Cuisson", _f("microwave_type"),
          _f("capacity_l", 20, 23, 25, 30), _f("power_w", 700, 800, 900, 1000)),
    _type("hood", "Cooker hood", "Cuisson", _f("hood_type"), _f("width_cm", 60, 90),
          _f("airflow_m3h")),
    # --- Chauffage ---
    _type("water_heater", "Water heater", "Chauffage", _f("fuel", "Electric", "Gas"),
          _f("capacity_l", 30, 50, 80, 100, 150), _f("energy_class")),
    _type("heater", "Heater", "Chauffage", _f("heater_type"),
          _f("fuel", "Gas", "Electric", "Wood", "Fuel oil"), _f("power_w")),
    # --- Petit électroménager ---
    _type("blender", "Blender", "Petit électroménager", _f("blender_type"), _f("power_w"),
          _f("capacity_l")),
    _type("vacuum_cleaner", "Vacuum cleaner", "Petit électroménager", _f("vacuum_type"),
          _f("power_w"), _f("dust_capacity_l")),
    _type("coffee_machine", "Coffee machine", "Petit électroménager", _f("coffee_type"),
          _f("pressure_bar"), _f("capacity_l", 0.6, 1, 1.5, 1.8), _f("power_w")),
    _type("air_fryer", "Air fryer", "Petit électroménager", _f("capacity_l", 3, 4, 5, 6, 8),
          _f("power_w", 1200, 1500, 1700, 2000)),
    _type("iron", "Iron", "Petit électroménager", _f("iron_type"), _f("power_w")),
)

TYPES_BY_KEY: dict[str, ProductType] = {t.key: t for t in PRODUCT_TYPES}


def type_label(category: str) -> str:
    product_type = TYPES_BY_KEY.get(category.strip().lower())
    return product_type.label if product_type else category


def types_for_group(name: str) -> tuple[str, ...]:
    """Product type keys that belong to a store group such as "Lavage" (case-insensitive)."""
    wanted = name.strip().casefold()
    return tuple(t.key for t in PRODUCT_TYPES if t.group.casefold() == wanted)


def humanize_key(key: str) -> str:
    return key.replace("_", " ").strip().capitalize()


def spec_label(key: str) -> str:
    field = REGISTRY.get(key)
    return field.label if field else humanize_key(key)


def catalog_schema(assistant_categories: frozenset[str]) -> dict[str, Any]:
    """JSON structure consumed by the admin product form."""
    return {
        "groups": [
            {
                "name": group,
                "types": [
                    {
                        "key": t.key,
                        "label": t.label,
                        "assistant_supported": t.key in assistant_categories,
                        "fields": [f.to_dict() for f in t.fields],
                    }
                    for t in PRODUCT_TYPES
                    if t.group == group
                ],
            }
            for group in GROUPS
        ]
    }

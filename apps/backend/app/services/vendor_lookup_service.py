class VendorLookupService:
    _vendors = {
        "00:1a:2b": "Ubiquiti",
        "00:1f:90": "Cisco",
        "00:25:9c": "Apple",
        "00:26:bb": "Apple",
        "00:50:56": "VMware",
        "00:0c:29": "VMware",
        "00:15:5d": "Microsoft",
        "3c:5a:b4": "Google",
        "40:16:7e": "Samsung",
        "44:65:0d": "Xiaomi",
        "58:ef:68": "TP-Link",
        "60:45:cb": "Dell",
        "70:4d:7b": "HP",
        "74:da:38": "Intel",
        "8c:85:90": "Huawei",
        "9c:b6:d0": "ASUS",
        "b8:27:eb": "Raspberry Pi",
        "d8:3a:dd": "Google",
        "dc:a6:32": "Roku",
        "e4:95:6e": "Amazon",
        "f4:f5:d8": "Google",
        "fc:fb:fb": "Cisco Meraki",
    }

    def lookup(self, mac_address: str) -> str:
        if not mac_address or mac_address == "Unknown":
            return "Unknown"

        normalized = mac_address.lower().replace("-", ":")
        prefix = ":".join(normalized.split(":")[:3])
        return self._vendors.get(prefix, "Unknown")
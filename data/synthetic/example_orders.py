"""The two example orders for Dante's review (D24).

SYNTHETIC — NOT REAL DATA. All companies, people, addresses, phone numbers
and identifiers are fictional. Email domains use the reserved .example TLD.

truth: the correct value of every critical field.
    None            -> the field does not apply to this order
    "__PENDING__"   -> awaited, not yet known
defects: what is seeded on purpose.
    mismatch -> one document shows a different value than the others
    omit     -> the value is left blank in every document
    A defect with a "finding" is expected to be reported by the agent.
"""

NA = None
PENDING = "__PENDING__"

TENANT = "Carrier Alfa (synthetic)"


def end(prefix: str, **values) -> dict:
    return {f"{prefix}.{key}": value for key, value in values.items()}


# ----------------------------------------------------------------------------- EPL
# One enterprise EPL order with two seeded defects (mandatory cases 1 and 3).

EPL_EXAMPLE = {
    "product": "EPL",
    "tenant": TENANT,
    "customer_type": "enterprise",
    "project": None,
    "split": "dev",
    "truth": {
        "order_id": "SYN-EPL-0001",
        "customer_name": "Bravo Logistics (synthetic)",
        "product": "EPL",
        "order_version": "1",
        "carrier_circuit_id": "ALFA-EPL-000101",
        "signature.signatory_name": "Jordan Sample",
        "signature.signatory_title": "Director of IT Infrastructure",
        "signature.date": "2026-10-28",
        "signature.contract_reference": "MSA-SYN-2026-014 / Order Form OF-SYN-0001",
        "port_speed": "10 Gbps",
        "cir": "10 Gbps",
        "mtu": "9100",
        "vlan": NA,
        "l2cp_transparency": "LACP pass-through required",
        "acceptance.required_tests": "ITU-T Y.1564",
        "acceptance.deemed_acceptance_clause": "Yes",
        "acceptance.deemed_acceptance_period": "5 business days",
        "dates.requested": "2027-01-15",
        "dates.forecast": PENDING,
        "dates.committed": PENDING,
        "escalation_contact": "Morgan Placeholder, Head of Network, morgan.placeholder@bravo-logistics.example, +1 555 0101",
        **end(
            "a_end",
            address="100 Example Avenue, Synthetic City, SC 00001",
            building="Building A",
            floor="2",
            suite_or_room="Suite 210",
            rack="R-14",
            demarcation_point="Patch panel PP-2, ports 5-6",
            data_center_operator="DC Operator Delta (synthetic)",
            meet_me_room="MMR-1",
            **{
                "cross_connect.required": "Yes",
                "cross_connect.responsibility": "customer",
                "cross_connect.loa_cfa_reference": "LOA-SYN-0001-A",
                "site_access.hours": "24x7",
                "site_access.notice_lead_time": "48 hours",
                "site_access.escort_required": "Yes",
                "interface.type": "10GBASE-LR",
                "interface.optic": "SFP+ LR",
                "interface.connector": "LC/UPC duplex",
                "interface.fiber_type": "single-mode",
                "interface.optic_wavelength_nm": "1310",
            },
            technical_contact="Casey Example, Network Engineer, casey.example@bravo-logistics.example, +1 555 0100",
        ),
        **end(
            "z_end",
            address="250 Placeholder Road, Sample Town, ST 00002",
            building="Main building",
            floor="1",
            suite_or_room="Room 1.07",
            rack="R-03",
            demarcation_point="Patch panel PP-1, ports 1-2",
            data_center_operator="DC Operator Foxtrot (synthetic)",
            meet_me_room="MMR-B",
            **{
                "cross_connect.required": "Yes",
                "cross_connect.responsibility": "carrier",
                "cross_connect.loa_cfa_reference": "LOA-SYN-0001-Z",
                "site_access.hours": "Monday to Friday, 08:00-18:00 local time",
                "site_access.notice_lead_time": "72 hours",
                "site_access.escort_required": "Yes",
                "interface.type": "10GBASE-LR",
                "interface.optic": "SFP+ LR",
                "interface.connector": "LC/UPC duplex",
                "interface.fiber_type": "single-mode",
                "interface.optic_wavelength_nm": "1310",
            },
            technical_contact="Riley Specimen, Site Engineer, riley.specimen@bravo-logistics.example, +1 555 0102",
        ),
    },
    "defects": [
        {
            "type": "mismatch",
            "field": "cir",
            "doc": "order_form",
            "value": "1 Gbps",
            "description": "The signed order form shows CIR 1 Gbps; the quote and the technical annex show 10 Gbps. "
                           "Both are valid on a 10 Gbps port, so only a cross-document comparison catches it.",
            "finding": {
                "rule_id": "G1-CONSISTENCY",
                "severity": "critical",
                "mandatory_case": 1,
                "description": "CIR differs between the signed order form and the quote / technical annex. "
                               "Contractual error if provisioned at either value without confirmation.",
            },
        },
        {
            "type": "omit",
            "field": "z_end.demarcation_point",
            "description": "The Z-end demarcation point is blank in the technical annex and in the LOA-CFA.",
            "finding": {
                "rule_id": "G1-REQUIRED",
                "severity": "critical",
                "mandatory_case": 3,
                "description": "Z-end demarcation point is missing. Provisioning cannot place the handoff.",
            },
        },
    ],
    "emails": [
        {
            "from": "Casey Example <casey.example@bravo-logistics.example>",
            "to": "Service Delivery <delivery@carrier-alfa.example>",
            "sent": "2026-10-30 14:12 UTC",
            "subject": "SYN-EPL-0001 — kick-off and timing",
            "body": [
                "Hello,",
                "The order form for SYN-EPL-0001 was signed on 28 October. Could you confirm who our delivery contact is and when we can expect a delivery plan?",
                "As stated in the order, we need the service by 15 January 2027 because the warehouse system migration starts the following week.",
                "Thanks,\n\nCasey Example\n\nNetwork Engineer, Bravo Logistics (synthetic)",
            ],
            "date_mentions": [
                {"location": "body, paragraph 3", "raw_value": "15 January 2027", "type": "requested",
                 "note": "Customer restates the requested date. It is a need, not a carrier commitment."},
            ],
        },
    ],
}


# ---------------------------------------------------------------------- WAVELENGTH
# Circuit 1 of 3 in a hyperscaler project. Seeded: route diversity without a
# reference (D19) and a tentative supplier date in an email (mandatory case 5).

AURORA_ORDERS = ["SYN-WAV-0001", "SYN-WAV-0002", "SYN-WAV-0003"]

WAVELENGTH_EXAMPLE = {
    "product": "WAVELENGTH",
    "tenant": TENANT,
    "customer_type": "hyperscaler",
    "project": "Project Aurora (synthetic)",
    "split": "dev",
    "truth": {
        "order_id": "SYN-WAV-0001",
        "customer_name": "Hyperscaler X (synthetic)",
        "product": "WAVELENGTH",
        "order_version": "1",
        "carrier_circuit_id": "ALFA-WAV-000201",
        "signature.signatory_name": "Taylor Demo",
        "signature.signatory_title": "Senior Manager, Network Acquisition",
        "signature.date": "2026-11-02",
        "signature.contract_reference": "MSA-SYN-2025-003 / Order Form OF-SYN-0201",
        "rate": "100 Gbps",
        "client_protocol": "OTN",
        "fec": "GFEC (ITU-T G.709)",
        "protection.type": "unprotected",
        "protection.switching_time": NA,
        "route_diversity.required": "Yes",
        "route_diversity.reference_circuit_ids": "ALFA-WAV-000202, ALFA-WAV-000203",
        "route_diversity.required_evidence": "Route map (KMZ) for each circuit, showing no shared conduit or building entry",
        "latency.max": "12 ms",
        "latency.definition": "round-trip",
        "latency.measurement_method": "OTN delay measurement (ITU-T G.709), averaged over 24 hours",
        "acceptance.ber_test": "BER no worse than 1E-12",
        "acceptance.ber_test_duration": "24 hours",
        "acceptance.deemed_acceptance_clause": "Yes",
        "acceptance.deemed_acceptance_period": "10 business days",
        "dates.requested": "2027-02-01",
        "dates.forecast": PENDING,
        "dates.committed": PENDING,
        "escalation_contact": "Avery Mockup, Director of Network Delivery, avery.mockup@hyperscaler-x.example, +1 555 0200",
        **end(
            "a_end",
            address="500 Fictional Parkway, Synthetic City, SC 00003",
            building="DC-1",
            floor="3",
            suite_or_room="Cage C-12",
            rack="C12-R07",
            demarcation_point="ODF-3, ports 11-12",
            data_center_operator="DC Operator Delta (synthetic)",
            meet_me_room="MMR-2",
            **{
                "cross_connect.required": "Yes",
                "cross_connect.responsibility": "customer",
                "cross_connect.loa_cfa_reference": "LOA-SYN-0201-A",
                "site_access.hours": "24x7",
                "site_access.notice_lead_time": "24 hours",
                "site_access.escort_required": "No",
                "interface.client_interface": "OTU4",
                "interface.optic": "QSFP28",
                "interface.optic_reach": "LR4",
                "interface.connector": "LC/UPC duplex",
            },
            technical_contact="Sam Fixture, Optical Engineer, sam.fixture@hyperscaler-x.example, +1 555 0201",
        ),
        **end(
            "z_end",
            address="75 Specimen Street, Sample Town, ST 00004",
            building="DC-West",
            floor="1",
            suite_or_room="Hall 2, Cage H2-04",
            rack="H2-04-R02",
            demarcation_point="ODF-1, ports 3-4",
            data_center_operator="DC Operator Foxtrot (synthetic)",
            meet_me_room="MMR-A",
            **{
                "cross_connect.required": "Yes",
                "cross_connect.responsibility": "carrier",
                "cross_connect.loa_cfa_reference": "LOA-SYN-0201-Z",
                "site_access.hours": "24x7",
                "site_access.notice_lead_time": "48 hours",
                "site_access.escort_required": "Yes",
                "interface.client_interface": "OTU4",
                "interface.optic": "QSFP28",
                "interface.optic_reach": "LR4",
                "interface.connector": "LC/UPC duplex",
            },
            technical_contact="Drew Template, Data Center Operations, drew.template@hyperscaler-x.example, +1 555 0202",
        ),
    },
    "defects": [
        {
            "type": "omit",
            "field": "route_diversity.reference_circuit_ids",
            "description": "Route diversity is required, but the order form does not say which circuits "
                           "this one must be diverse from.",
            "finding": {
                "rule_id": "WAV-DIVERSITY-REFERENCE",
                "severity": "critical",
                "mandatory_case": None,
                "description": "Route diversity is required without a reference circuit. The design cannot be "
                               "validated and the diversity commitment cannot be evidenced.",
            },
        },
        {
            "type": "tentative_date",
            "field": "dates.committed",
            "description": "A supplier email gives a tentative date. It must be recorded as a forecast, "
                           "never as a committed date.",
        },
    ],
    "emails": [
        {
            "from": "Sam Fixture <sam.fixture@hyperscaler-x.example>",
            "to": "Service Delivery <delivery@carrier-alfa.example>",
            "sent": "2026-11-03 09:40 UTC",
            "subject": "Project Aurora (synthetic) — SYN-WAV-0001 to 0003, A-end cross-connects",
            "body": [
                "Hi team,",
                "For the three Aurora wavelengths (SYN-WAV-0001, SYN-WAV-0002 and SYN-WAV-0003) we are ordering the A-end cross-connects as a single request to the data center operator, reference XC-SYN-AURORA-A, all terminating in MMR-2.",
                "The operator has not yet accepted the request because the LOA-CFA for the batch is under review on their side. I will update you when it moves.",
                "Regards,\n\nSam Fixture\n\nOptical Engineer, Hyperscaler X (synthetic)",
            ],
        },
        {
            "from": "Provisioning Desk <provisioning@supplier-echo.example>",
            "to": "Supplier Management <suppliers@carrier-alfa.example>",
            "sent": "2026-11-05 16:05 UTC",
            "subject": "RE: Z-end fiber tail for ALFA-WAV-000201",
            "body": [
                "Hello,",
                "Regarding the fiber tail into DC-West for ALFA-WAV-000201: we are tentatively targeting 22 January 2027 for handover. This is not confirmed; it depends on the building entry permit, which has not been issued yet.",
                "We will send a firm date once the permit is granted.",
                "Provisioning Desk\n\nSupplier Echo Fiber (synthetic)",
            ],
            "date_mentions": [
                {"location": "body, paragraph 2", "raw_value": "22 January 2027", "type": "forecast",
                 "mandatory_case": 5,
                 "note": "Tentative supplier date, conditional on a permit. Forecast with that assumption; "
                         "not a commitment and not the order's committed date."},
            ],
        },
    ],
    "shared_resources": [
        {
            "shared_resource_id": "XC-SYN-AURORA-A",
            "kind": "cross_connect",
            "description": "Single A-end cross-connect request in MMR-2 covering the three Project Aurora wavelengths; "
                           "not yet accepted by the data center operator.",
            "is_blocked": True,
            "linked_order_ids": AURORA_ORDERS,
        },
    ],
}

EXAMPLE_ORDERS = [EPL_EXAMPLE, WAVELENGTH_EXAMPLE]

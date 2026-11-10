"""Simulated event files (SPEC 11.1): not orders, but inputs for robustness tests.

SYNTHETIC — NOT REAL DATA. Each set lists events in the order they are received
and the outcome the system must show. They are exercised in Phase 7 (cases 13
and 14) and post-demo (case 10).
"""

EVENT_SETS = [
    {
        "event_set_id": "repeated_update",
        "mandatory_case": 13,
        "title": "Repeated update",
        "description": "The same supplier status update for SYN-WAV-0010 is delivered three times (a retry and a "
                       "replay), and an older update arrives late.",
        "events": [
            {"event_id": "EVT-SYN-0001", "idempotency_key": "supplier-sierra:ALFA-WAV-000210:status:2",
             "type": "supplier_status_update", "service_order": "SYN-WAV-0010", "source": "supplier_portal",
             "occurred_at": "2026-11-12T10:00:00Z", "received_at": "2026-11-12T10:00:05Z",
             "payload": {"sequence": 2, "status": "survey_scheduled", "supplier_date": None}},
            {"event_id": "EVT-SYN-0002", "idempotency_key": "supplier-sierra:ALFA-WAV-000210:status:2",
             "type": "supplier_status_update", "service_order": "SYN-WAV-0010", "source": "supplier_portal",
             "occurred_at": "2026-11-12T10:00:00Z", "received_at": "2026-11-12T10:00:35Z",
             "payload": {"sequence": 2, "status": "survey_scheduled", "supplier_date": None}},
            {"event_id": "EVT-SYN-0003", "idempotency_key": "supplier-sierra:ALFA-WAV-000210:status:1",
             "type": "supplier_status_update", "service_order": "SYN-WAV-0010", "source": "supplier_portal",
             "occurred_at": "2026-11-10T09:00:00Z", "received_at": "2026-11-12T10:05:00Z",
             "payload": {"sequence": 1, "status": "order_acknowledged", "supplier_date": None}},
            {"event_id": "EVT-SYN-0004", "idempotency_key": "supplier-sierra:ALFA-WAV-000210:status:2",
             "type": "supplier_status_update", "service_order": "SYN-WAV-0010", "source": "supplier_portal",
             "occurred_at": "2026-11-12T10:00:00Z", "received_at": "2026-11-13T08:00:00Z",
             "payload": {"sequence": 2, "status": "survey_scheduled", "supplier_date": None}},
        ],
        "expected": {
            "state_changes": 1,
            "final_state": {"status": "survey_scheduled", "sequence": 2},
            "duplicate_event_ids": ["EVT-SYN-0002", "EVT-SYN-0004"],
            "out_of_order_event_ids": ["EVT-SYN-0003"],
            "max_drafts_created": 1,
            "duplicated_external_effects": 0,
            "notes": "Duplicates are recognized by idempotency key and logged, not applied again. The late older "
                     "update is recorded with both timestamps and does not overwrite the newer state.",
        },
    },
    {
        "event_set_id": "integration_down",
        "mandatory_case": 14,
        "title": "Integration down",
        "description": "The order-source integration times out and returns errors while SYN-EPL-0002 is being "
                       "refreshed, then recovers.",
        "events": [
            {"event_id": "EVT-SYN-0101", "idempotency_key": "order-source:SYN-EPL-0002:poll:1",
             "type": "integration_call", "service_order": "SYN-EPL-0002", "source": "order_source",
             "occurred_at": "2026-11-15T12:00:00Z", "received_at": "2026-11-15T12:00:30Z",
             "payload": {"attempt": 1, "outcome": "timeout", "http_status": None}},
            {"event_id": "EVT-SYN-0102", "idempotency_key": "order-source:SYN-EPL-0002:poll:1",
             "type": "integration_call", "service_order": "SYN-EPL-0002", "source": "order_source",
             "occurred_at": "2026-11-15T12:01:00Z", "received_at": "2026-11-15T12:01:01Z",
             "payload": {"attempt": 2, "outcome": "error", "http_status": 503}},
            {"event_id": "EVT-SYN-0103", "idempotency_key": "order-source:SYN-EPL-0002:poll:1",
             "type": "integration_call", "service_order": "SYN-EPL-0002", "source": "order_source",
             "occurred_at": "2026-11-15T12:03:00Z", "received_at": "2026-11-15T12:03:01Z",
             "payload": {"attempt": 3, "outcome": "error", "http_status": 503}},
            {"event_id": "EVT-SYN-0104", "idempotency_key": "order-source:SYN-EPL-0002:poll:2",
             "type": "integration_call", "service_order": "SYN-EPL-0002", "source": "order_source",
             "occurred_at": "2026-11-15T13:00:00Z", "received_at": "2026-11-15T13:00:01Z",
             "payload": {"attempt": 1, "outcome": "ok", "http_status": 200}},
        ],
        "expected": {
            "retries_are_limited": True,
            "failure_visible_to_user": True,
            "data_marked_stale_between": ["2026-11-15T12:00:30Z", "2026-11-15T13:00:01Z"],
            "status_reported_during_outage": "stale",
            "duplicated_external_effects": 0,
            "notes": "During the outage the order shows its last known data with its age and an integration error; "
                     "nothing is presented as current. After recovery the refresh is applied once.",
        },
    },
    {
        "event_set_id": "missing_telemetry",
        "mandatory_case": 10,
        "title": "Missing telemetry",
        "description": "After acceptance, the telemetry feed for SYN-WAV-0004 delivers no samples for part of the "
                       "observation window.",
        "events": [
            {"event_id": "EVT-SYN-0201", "idempotency_key": "telemetry:ALFA-WAV-000204:2027-03-01",
             "type": "telemetry_window", "service_order": "SYN-WAV-0004", "source": "telemetry",
             "occurred_at": "2027-03-01T00:00:00Z", "received_at": "2027-03-02T00:05:00Z",
             "payload": {"window_hours": 24, "samples_expected": 288, "samples_received": 288, "alarms": 0}},
            {"event_id": "EVT-SYN-0202", "idempotency_key": "telemetry:ALFA-WAV-000204:2027-03-02",
             "type": "telemetry_window", "service_order": "SYN-WAV-0004", "source": "telemetry",
             "occurred_at": "2027-03-02T00:00:00Z", "received_at": "2027-03-03T00:05:00Z",
             "payload": {"window_hours": 24, "samples_expected": 288, "samples_received": 0, "alarms": 0}},
            {"event_id": "EVT-SYN-0203", "idempotency_key": "telemetry:ALFA-WAV-000204:2027-03-03",
             "type": "telemetry_window", "service_order": "SYN-WAV-0004", "source": "telemetry",
             "occurred_at": "2027-03-03T00:00:00Z", "received_at": "2027-03-04T00:05:00Z",
             "payload": {"window_hours": 24, "samples_expected": 288, "samples_received": 0, "alarms": 0}},
        ],
        "expected": {
            "coverage": "unknown",
            "windows_without_data": ["2027-03-02", "2027-03-03"],
            "stability_claim_allowed": False,
            "duplicated_external_effects": 0,
            "notes": "Zero alarms with zero samples is unknown coverage, not a stable service. The gap is reported "
                     "and stability is not asserted for those days.",
        },
    },
]

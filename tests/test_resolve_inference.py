import pandas as pd

from src.datacenter_layerA.resolve import compute_status, resolve_project_drivers


def test_resolve_infers_from_square_footage():
    observations = pd.DataFrame(
        [
            {
                "datacenter_id": "dc1",
                "spec_name": "square_ft",
                "value_num": 100000.0,
                "unit": "sqft",
                "value_text": "100,000 square feet",
                "source_url": "http://example.com",
                "snippet": "100,000 square feet",
                "date_accessed": "2024-01-01",
                "confidence": 0.9,
                "method": "scrape_html",
            }
        ]
    )
    drivers, inferred = resolve_project_drivers(observations)
    assert not drivers.empty
    row = drivers.iloc[0]
    assert row["rack_count_est"] is not None
    assert row["power_mw_est"] is not None
    assert not inferred.empty
    assert (inferred["spec_name"] == "kw_per_rack").any()


def test_status_computed_complete_when_requirements_met():
    site_list = pd.DataFrame(
        [
            {
                "datacenter_id": "dc1",
                "provider_name": "Test",
                "provider_url_primary": "http://example.com",
                "datacenter_building_name": "Building",
                "datacenter_campus_name": "Campus",
                "campus_or_property_url": "http://example.com/facility",
                "status": "planned",
                "notes": "City, ST",
            }
        ]
    )
    drivers = pd.DataFrame(
        [
            {
                "datacenter_id": "dc1",
                "power_mw_est": 10,
                "square_ft_est": 100000,
                "kw_per_rack_est": 12,
                "rack_count_est": 800,
                "cooling_type_est": "air cooled",
            }
        ]
    )
    geo = pd.DataFrame(
        [
            {
                "datacenter_id": "dc1",
                "city": "City",
                "region_state": "ST",
                "country_code": "US",
                "latitude": 1.0,
                "longitude": 1.0,
            }
        ]
    )
    result = compute_status(site_list, drivers, geo)
    assert result.iloc[0]["status_computed"] == "Complete"

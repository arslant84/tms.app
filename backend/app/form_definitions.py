"""
Form definitions for different travel request types.
These structures define the expected fields for each travel type.
"""

# Common fields across all travel types
COMMON_FIELDS = {
    "employee_details": {
        "full_name": str,
        "staff_id": str,
        "department": str,
        "position": str,
        "tel_ext_email": str,
        "dept_cost_center": str,
    },
    "purpose_of_travel": str,
    "prepared_by": {
        "name": str,
        "signature": str,
        "position": str,
        "date": str,
    },
    "reviewed_by": {
        "name": str,
        "signature": str,
        "position": str,
        "date": str,
    },
    "approved_by": {
        "name": str,
        "signature": str,
        "position": str,
        "date": str,
    },
}

# Domestic Travel Form Fields
DOMESTIC_TRAVEL_FIELDS = {
    **COMMON_FIELDS,
    "itinerary": [
        {
            "date": str,
            "day": str,
            "from_location": str,
            "to_location": str,
            "etd": str,  # Estimated Time of Departure
            "eta": str,  # Estimated Time of Arrival
            "flight_ref": str,
            "remarks": str,
        }
    ],
    "meal_provision": [
        {
            "date": str,
            "breakfast": int,  # Count or cost
            "lunch": int,
            "dinner": int,
            "supper": int,
            "refreshment": int,
        }
    ],
    "accommodation": [
        {
            "type": str,  # Hotel/Motel, Staff House, PKC Kampung, Other
            "check_in_date": str,
            "check_in_time": str,
            "check_out_date": str,
            "check_out_time": str,
            "remarks": str,
        }
    ],
    "company_transportation": [
        {
            "date": str,
            "day": str,
            "from_location": str,
            "to_location": str,
            "etd_eta": str,
            "accommodation_type": str,
            "address": str,
            "remarks": str,
        }
    ],
}

# Overseas Travel Form Fields
OVERSEAS_TRAVEL_FIELDS = {
    **COMMON_FIELDS,
    "itinerary": [
        {
            "date": str,
            "day": str,
            "from_location": str,
            "to_location": str,
            "etd": str,
            "eta": str,
            "flight_ref": str,
            "remarks": str,
        }
    ],
    "advance_form": {
        "bank_name": str,
        "account_number": str,
        "amount_details": [
            {
                "date": str,
                "from_to": str,
                "lil": float,  # Local currency amounts
                "ma": float,
                "oa": float,
                "tr": float,
                "oe": float,
                "usd": float,
                "trmm": float,
                "remarks": str,
            }
        ],
        "accommodation_total": float,
        "transport_total": float,
        "meal_allowance_total": float,
        "other_expenses_total": float,
        "total_usd": float,
        "total_trmm": float,
        "signature": str,
        "date": str,
    },
}

# Overseas Travel (HLP #1) Form Fields
# Similar to overseas but with HLP specific fields
OVERSEAS_HLP_FIELDS = {
    **OVERSEAS_TRAVEL_FIELDS,
    "hlp_number": str,  # HLP #1 identifier
    # Any other HLP-specific fields would go here
}

# External Parties Travel Form Fields
EXTERNAL_TRAVEL_FIELDS = {
    "requestor_details": {
        "full_name": str,
        "organization": str,
        "authority_letter_no": str,  # Required reference to authority letter
        "cost_center": str,
    },
    "purpose_of_travel": str,
    "itinerary": [
        {
            "date": str,
            "day": str,
            "from_location": str,
            "to_location": str,
            "etd": str,
            "eta": str,
            "flight_ref": str,
            "remarks": str,
        }
    ],
    "accommodation": [
        {
            "date": str,
            "check_in": str,
            "check_out": str,
            "place_of_stay": str,
            "est_cost_per_night": float,
            "remarks": str,
        }
    ],
    "meal_provision": [
        {
            "date": str,
            "breakfast": int,
            "lunch": int,
            "dinner": int,
            "supper": int,
            "refreshment": int,
        }
    ],
    "requested_by": {
        "name": str,
        "signature": str,
        "position": str,
        "date": str,
    },
    "reviewed_by": {
        "name": str,
        "signature": str,
        "position": str,
        "date": str,
    },
    "approved_by": {
        "name": str,
        "signature": str,
        "position": str,
        "date": str,
    },
    "cost_controller": {
        "name": str,
        "signature": str,
        "cost_center": str,
        "date": str,
    },
    "remarks": str,
}

# Field validation rules for each travel type
VALIDATION_RULES = {
    "domestic": {
        "required_fields": [
            "employee_details.full_name",
            "employee_details.department",
            "employee_details.dept_cost_center",
            "purpose_of_travel",
            "itinerary",
        ],
        "conditional_fields": [],
    },
    "overseas": {
        "required_fields": [
            "employee_details.full_name",
            "employee_details.department",
            "employee_details.dept_cost_center",
            "purpose_of_travel",
            "itinerary",
        ],
        "conditional_fields": [
            # If advance form is included, these fields are required
            {"if": "advance_form", "then": [
                "advance_form.bank_name",
                "advance_form.account_number"
            ]}
        ],
    },
    "overseas_hlp": {
        "required_fields": [
            "employee_details.full_name",
            "employee_details.department",
            "employee_details.dept_cost_center",
            "purpose_of_travel",
            "itinerary",
            "hlp_number",
        ],
        "conditional_fields": [],
    },
    "external": {
        "required_fields": [
            "requestor_details.full_name",
            "requestor_details.organization",
            "requestor_details.authority_letter_no",
            "requestor_details.cost_center",
            "purpose_of_travel",
            "itinerary",
        ],
        "conditional_fields": [],
    },
}

# Example form data for each travel type (for testing)
EXAMPLE_FORMS = {
    "domestic": {
        "employee_details": {
            "full_name": "John Doe",
            "staff_id": "123456",
            "department": "IT",
            "position": "Developer",
            "tel_ext_email": "123/john.doe@example.com",
            "dept_cost_center": "IT-001",
        },
        "purpose_of_travel": "Technical support for field office",
        "itinerary": [
            {
                "date": "2025-06-01",
                "day": "Monday",
                "from_location": "Headquarters",
                "to_location": "Field Office",
                "etd": "08:00",
                "eta": "10:00",
                "flight_ref": "N/A",
                "remarks": "Company car",
            }
        ],
        "meal_provision": [
            {
                "date": "2025-06-01",
                "breakfast": 0,
                "lunch": 1,
                "dinner": 1,
                "supper": 0,
                "refreshment": 1,
            }
        ],
        "accommodation": [
            {
                "type": "Hotel",
                "check_in_date": "2025-06-01",
                "check_in_time": "14:00",
                "check_out_date": "2025-06-03",
                "check_out_time": "12:00",
                "remarks": "Standard room",
            }
        ],
        "company_transportation": [
            {
                "date": "2025-06-01",
                "day": "Monday",
                "from_location": "Airport",
                "to_location": "Hotel",
                "etd_eta": "11:00-12:00",
                "accommodation_type": "Hotel",
                "address": "123 Main St",
                "remarks": "Company car",
            }
        ],
        "prepared_by": {
            "name": "John Doe",
            "signature": "JDoe",
            "position": "Developer",
            "date": "2025-05-15",
        },
        "reviewed_by": {
            "name": "Jane Smith",
            "signature": "JSmith",
            "position": "Team Lead",
            "date": "2025-05-16",
        },
        "approved_by": {
            "name": "Mike Johnson",
            "signature": "MJohnson",
            "position": "Department Head",
            "date": "2025-05-17",
        },
    },
    "overseas": {
        "employee_details": {
            "full_name": "Santizah Binti Samat",
            "staff_id": "129666",
            "department": "TPM",
            "position": "Lead TPM",
            "tel_ext_email": "186/santizah_samat@petronas.com",
            "dept_cost_center": "083100-078",
        },
        "purpose_of_travel": "PROCUREMENT INTERNATIONAL LEADERS CONNECT AND MEETING WITH GROUP PROCUREMENT KL",
        "itinerary": [
            {
                "date": "2025-02-20",
                "day": "Thursday",
                "from_location": "Ashgabat",
                "to_location": "Kuala Lumpur",
                "etd": "05:30",
                "eta": "16:20",
                "flight_ref": "Business Class",
                "remarks": "T-5",
            },
            {
                "date": "2025-02-27",
                "day": "Thursday",
                "from_location": "Kuala Lumpur",
                "to_location": "Ashgabat",
                "etd": "18:20",
                "eta": "23:50",
                "flight_ref": "Business Class",
                "remarks": "T-5",
            }
        ],
        "advance_form": {
            "bank_name": "Bank Negara",
            "account_number": "1234567890",
            "amount_details": [
                {
                    "date": "2025-02-20",
                    "from_to": "7",
                    "lil": 0,
                    "ma": 0,
                    "oa": 0,
                    "tr": 0,
                    "oe": 0,
                    "usd": 0,
                    "trmm": 0,
                    "remarks": "",
                }
            ],
            "accommodation_total": 0,
            "transport_total": 0,
            "meal_allowance_total": 0,
            "other_expenses_total": 0,
            "total_usd": 0,
            "total_trmm": 0,
            "signature": "Santizah",
            "date": "2025-01-15",
        },
        "prepared_by": {
            "name": "Santizah Binti Samat",
            "signature": "Santizah",
            "position": "Lead TPM",
            "date": "2025-01-15",
        },
        "reviewed_by": {
            "name": "Olga K",
            "signature": "OlgaK",
            "position": "Clerk TAD",
            "date": "2025-01-16",
        },
        "approved_by": {
            "name": "Nurfathia Bt Abu Samad",
            "signature": "Nurfathia",
            "position": "Acting CRO KGTGB",
            "date": "2025-01-17",
        },
    },
    "overseas_hlp": {
        "employee_details": {
            "full_name": "Santizah Binti Samat",
            "staff_id": "129666",
            "department": "TPM",
            "position": "Lead TPM",
            "tel_ext_email": "186/santizah_samat@petronas.com",
            "dept_cost_center": "083100-078",
        },
        "purpose_of_travel": "HLP #1",
        "hlp_number": "HLP-2025-001",
        "itinerary": [
            {
                "date": "2025-03-20",
                "day": "Thursday",
                "from_location": "Ashgabat",
                "to_location": "Kuala Lumpur",
                "etd": "05:30",
                "eta": "16:20",
                "flight_ref": "Business Class",
                "remarks": "T-5",
            },
            {
                "date": "2025-03-30",
                "day": "Thursday",
                "from_location": "Kuala Lumpur",
                "to_location": "Ashgabat",
                "etd": "18:20",
                "eta": "23:50",
                "flight_ref": "Business Class",
                "remarks": "T-5",
            }
        ],
        "advance_form": {
            "bank_name": "Bank Negara",
            "account_number": "1234567890",
            "amount_details": [],
            "accommodation_total": 0,
            "transport_total": 0,
            "meal_allowance_total": 0,
            "other_expenses_total": 0,
            "total_usd": 0,
            "total_trmm": 0,
            "signature": "Santizah",
            "date": "2025-02-15",
        },
        "prepared_by": {
            "name": "Santizah Binti Samat",
            "signature": "Santizah",
            "position": "Lead TPM",
            "date": "2025-02-15",
        },
        "reviewed_by": {
            "name": "Olga K",
            "signature": "OlgaK",
            "position": "Clerk TAD",
            "date": "2025-02-16",
        },
        "approved_by": {
            "name": "Nurfathia Bt Abu Samad",
            "signature": "Nurfathia",
            "position": "Acting CRO KGTGB",
            "date": "2025-02-17",
        },
    },
    "external": {
        "requestor_details": {
            "full_name": "Alex Johnson",
            "organization": "ABC Consulting",
            "authority_letter_no": "AUTH-2025-123",
            "cost_center": "EXT-001",
        },
        "purpose_of_travel": "Technical consultation for new project",
        "itinerary": [
            {
                "date": "2025-07-10",
                "day": "Thursday",
                "from_location": "New York",
                "to_location": "Kuala Lumpur",
                "etd": "08:00",
                "eta": "22:00",
                "flight_ref": "Business Class",
                "remarks": "Direct flight",
            }
        ],
        "accommodation": [
            {
                "date": "2025-07-10",
                "check_in": "2025-07-10",
                "check_out": "2025-07-15",
                "place_of_stay": "Grand Hotel",
                "est_cost_per_night": 150.00,
                "remarks": "Standard room",
            }
        ],
        "meal_provision": [
            {
                "date": "2025-07-11",
                "breakfast": 1,
                "lunch": 1,
                "dinner": 1,
                "supper": 0,
                "refreshment": 1,
            }
        ],
        "requested_by": {
            "name": "Alex Johnson",
            "signature": "AJohnson",
            "position": "Senior Consultant",
            "date": "2025-06-15",
        },
        "reviewed_by": {
            "name": "Maria Garcia",
            "signature": "MGarcia",
            "position": "Project Manager",
            "date": "2025-06-16",
        },
        "approved_by": {
            "name": "Robert Chen",
            "signature": "RChen",
            "position": "Director",
            "date": "2025-06-17",
        },
        "cost_controller": {
            "name": "Susan Wong",
            "signature": "SWong",
            "cost_center": "FIN-001",
            "date": "2025-06-18",
        },
        "remarks": "Visitor requires special access to R&D facilities.",
    },
}

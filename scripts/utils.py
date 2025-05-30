# scripts/utils.py

# Contract ABIs
FALCON_KEY_REGISTRY_ABI = [
    {
        "type": "impl",
        "name": "FalconPublicKeyRegistryImpl",
        "interface_name": "moosh_id::keyregistry::FalconPublicKeyRegistry::IFalconPublicKeyRegistry",
    },
    {
        "type": "struct",
        "name": "core::array::Span::<core::integer::u16>",
        "members": [
            {"name": "snapshot", "type": "@core::array::Array::<core::integer::u16>"}
        ],
    },
    {
        "type": "enum",
        "name": "core::bool",
        "variants": [{"name": "False", "type": "()"}, {"name": "True", "type": "()"}],
    },
    {
        "type": "interface",
        "name": "moosh_id::keyregistry::FalconPublicKeyRegistry::IFalconPublicKeyRegistry",
        "items": [
            {
                "type": "function",
                "name": "register_public_key",
                "inputs": [
                    {
                        "name": "pk_coefficients_span",
                        "type": "core::array::Span::<core::integer::u16>",
                    }
                ],
                "outputs": [{"type": "core::bool"}],
                "state_mutability": "external",
            },
            {
                "type": "function",
                "name": "get_public_key",
                "inputs": [{"name": "key_hash", "type": "core::felt252"}],
                "outputs": [{"type": "core::array::Array::<core::integer::u16>"}],
                "state_mutability": "view",
            },
            {
                "type": "function",
                "name": "get_key_owner",
                "inputs": [{"name": "key_hash", "type": "core::felt252"}],
                "outputs": [
                    {"type": "core::starknet::contract_address::ContractAddress"}
                ],
                "state_mutability": "view",
            },
            {
                "type": "function",
                "name": "get_registry_owner",
                "inputs": [],
                "outputs": [
                    {"type": "core::starknet::contract_address::ContractAddress"}
                ],
                "state_mutability": "view",
            },
        ],
    },
    {"type": "constructor", "name": "constructor", "inputs": []},
    {
        "type": "event",
        "name": "moosh_id::keyregistry::FalconPublicKeyRegistry::PublicKeyRegisteredEventData",
        "kind": "struct",
        "members": [
            {"name": "key_hash", "type": "core::felt252", "kind": "key"},
            {
                "name": "pk_coefficient_count",
                "type": "core::integer::u32",
                "kind": "data",
            },
            {
                "name": "registrant",
                "type": "core::starknet::contract_address::ContractAddress",
                "kind": "data",
            },
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::keyregistry::FalconPublicKeyRegistry::Event",
        "kind": "enum",
        "variants": [
            {
                "name": "PublicKeyRegistered",
                "type": "moosh_id::keyregistry::FalconPublicKeyRegistry::PublicKeyRegisteredEventData",
                "kind": "nested",
            }
        ],
    },
]
FALCON_VERIFIER_ABI = [
    {
        "type": "impl",
        "name": "FalconSignatureVerifierImpl",
        "interface_name": "moosh_id::addressverifier::FalconSignatureVerifier::IFalconSignatureVerifier",
    },
    {
        "type": "struct",
        "name": "core::array::Span::<core::integer::u16>",
        "members": [
            {"name": "snapshot", "type": "@core::array::Array::<core::integer::u16>"}
        ],
    },
    {
        "type": "enum",
        "name": "core::bool",
        "variants": [{"name": "False", "type": "()"}, {"name": "True", "type": "()"}],
    },
    {
        "type": "interface",
        "name": "moosh_id::addressverifier::FalconSignatureVerifier::IFalconSignatureVerifier",
        "items": [
            {
                "type": "function",
                "name": "verify_signature_for_key_hash",
                "inputs": [
                    {"name": "key_hash", "type": "core::felt252"},
                    {
                        "name": "s1_coeffs_span",
                        "type": "core::array::Span::<core::integer::u16>",
                    },
                    {
                        "name": "msg_point_span",
                        "type": "core::array::Span::<core::integer::u16>",
                    },
                ],
                "outputs": [{"type": "core::bool"}],
                "state_mutability": "view",
            }
        ],
    },
    {
        "type": "impl",
        "name": "FalconSignatureVerifierEventsImpl",
        "interface_name": "moosh_id::addressverifier::FalconSignatureVerifier::IFalconSignatureVerifierEvents",
    },
    {
        "type": "interface",
        "name": "moosh_id::addressverifier::FalconSignatureVerifier::IFalconSignatureVerifierEvents",
        "items": [
            {
                "type": "function",
                "name": "emit_success",
                "inputs": [
                    {"name": "key_hash", "type": "core::felt252"},
                    {"name": "msg_hash_part", "type": "core::felt252"},
                ],
                "outputs": [],
                "state_mutability": "external",
            },
            {
                "type": "function",
                "name": "emit_failure",
                "inputs": [
                    {"name": "key_hash", "type": "core::felt252"},
                    {"name": "msg_hash_part", "type": "core::felt252"},
                    {"name": "reason", "type": "core::felt252"},
                ],
                "outputs": [],
                "state_mutability": "external",
            },
        ],
    },
    {
        "type": "constructor",
        "name": "constructor",
        "inputs": [
            {
                "name": "key_registry_addr",
                "type": "core::starknet::contract_address::ContractAddress",
            }
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::addressverifier::Events::VerificationSuccess",
        "kind": "struct",
        "members": [
            {"name": "key_hash", "type": "core::felt252", "kind": "key"},
            {"name": "msg_hash_part", "type": "core::felt252", "kind": "data"},
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::addressverifier::Events::VerificationFailed",
        "kind": "struct",
        "members": [
            {"name": "key_hash", "type": "core::felt252", "kind": "key"},
            {"name": "msg_hash_part", "type": "core::felt252", "kind": "data"},
            {"name": "reason", "type": "core::felt252", "kind": "data"},
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::addressverifier::FalconSignatureVerifier::Event",
        "kind": "enum",
        "variants": [
            {
                "name": "VerificationSuccess",
                "type": "moosh_id::addressverifier::Events::VerificationSuccess",
                "kind": "nested",
            },
            {
                "name": "VerificationFailed",
                "type": "moosh_id::addressverifier::Events::VerificationFailed",
                "kind": "nested",
            },
        ],
    },
]
FALCON_ESCROW_ABI = [
    {
        "type": "impl",
        "name": "EscrowImpl",
        "interface_name": "moosh_id::escrow::Escrow::IEscrow",
    },
    {
        "type": "enum",
        "name": "core::bool",
        "variants": [{"name": "False", "type": "()"}, {"name": "True", "type": "()"}],
    },
    {
        "type": "struct",
        "name": "moosh_id::escrow::Escrow::EscrowDetails",
        "members": [
            {"name": "provider_key_hash", "type": "core::felt252"},
            {"name": "total_amount", "type": "core::integer::u128"},
            {"name": "service_period_blocks", "type": "core::integer::u64"},
            {"name": "service_start_block", "type": "core::integer::u64"},
            {"name": "is_completed", "type": "core::bool"},
            {"name": "is_claimed", "type": "core::bool"},
            {"name": "is_disputed", "type": "core::bool"},
            {"name": "is_deposited", "type": "core::bool"},
            {
                "name": "client",
                "type": "core::starknet::contract_address::ContractAddress",
            },
            {
                "name": "provider",
                "type": "core::starknet::contract_address::ContractAddress",
            },
        ],
    },
    {
        "type": "struct",
        "name": "core::array::Span::<core::integer::u16>",
        "members": [
            {"name": "snapshot", "type": "@core::array::Array::<core::integer::u16>"}
        ],
    },
    {
        "type": "struct",
        "name": "core::integer::u256",
        "members": [
            {"name": "low", "type": "core::integer::u128"},
            {"name": "high", "type": "core::integer::u128"},
        ],
    },
    {
        "type": "interface",
        "name": "moosh_id::escrow::Escrow::IEscrow",
        "items": [
            {
                "type": "function",
                "name": "get_escrow_details",
                "inputs": [],
                "outputs": [{"type": "moosh_id::escrow::Escrow::EscrowDetails"}],
                "state_mutability": "view",
            },
            {
                "type": "function",
                "name": "deposit",
                "inputs": [],
                "outputs": [{"type": "core::bool"}],
                "state_mutability": "external",
            },
            {
                "type": "function",
                "name": "claim",
                "inputs": [
                    {
                        "name": "s1_coeffs",
                        "type": "core::array::Span::<core::integer::u16>",
                    }
                ],
                "outputs": [{"type": "core::bool"}],
                "state_mutability": "external",
            },
            {
                "type": "function",
                "name": "dispute",
                "inputs": [],
                "outputs": [{"type": "core::bool"}],
                "state_mutability": "external",
            },
            {
                "type": "function",
                "name": "get_client_allowance",
                "inputs": [],
                "outputs": [{"type": "core::integer::u256"}],
                "state_mutability": "view",
            },
            {
                "type": "function",
                "name": "set_message_points",
                "inputs": [
                    {
                        "name": "msg_point_span",
                        "type": "core::array::Span::<core::integer::u16>",
                    }
                ],
                "outputs": [{"type": "core::bool"}],
                "state_mutability": "external",
            },
        ],
    },
    {
        "type": "constructor",
        "name": "constructor",
        "inputs": [
            {"name": "provider_key_hash", "type": "core::felt252"},
            {"name": "total_amount", "type": "core::integer::u128"},
            {"name": "service_period_blocks", "type": "core::integer::u64"},
            {
                "name": "verifier",
                "type": "core::starknet::contract_address::ContractAddress",
            },
            {
                "name": "key_registry",
                "type": "core::starknet::contract_address::ContractAddress",
            },
            {
                "name": "strk_token",
                "type": "core::starknet::contract_address::ContractAddress",
            },
            {
                "name": "client_address",
                "type": "core::starknet::contract_address::ContractAddress",
            },
            {
                "name": "provider_address",
                "type": "core::starknet::contract_address::ContractAddress",
            },
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::escrow::Escrow::EscrowCreated",
        "kind": "struct",
        "members": [
            {
                "name": "client",
                "type": "core::starknet::contract_address::ContractAddress",
                "kind": "data",
            },
            {"name": "provider_key_hash", "type": "core::felt252", "kind": "data"},
            {"name": "total_amount", "type": "core::integer::u128", "kind": "data"},
            {
                "name": "service_period_blocks",
                "type": "core::integer::u64",
                "kind": "data",
            },
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::escrow::Escrow::EscrowDeposited",
        "kind": "struct",
        "members": [
            {
                "name": "client",
                "type": "core::starknet::contract_address::ContractAddress",
                "kind": "data",
            },
            {"name": "amount", "type": "core::integer::u128", "kind": "data"},
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::escrow::Escrow::EscrowClaimed",
        "kind": "struct",
        "members": [
            {
                "name": "provider",
                "type": "core::starknet::contract_address::ContractAddress",
                "kind": "data",
            },
            {"name": "amount", "type": "core::integer::u128", "kind": "data"},
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::escrow::Escrow::EscrowDisputed",
        "kind": "struct",
        "members": [
            {
                "name": "client",
                "type": "core::starknet::contract_address::ContractAddress",
                "kind": "data",
            },
            {"name": "provider_key_hash", "type": "core::felt252", "kind": "data"},
            {"name": "blocks_served", "type": "core::integer::u64", "kind": "data"},
            {"name": "provider_amount", "type": "core::integer::u128", "kind": "data"},
            {"name": "client_refund", "type": "core::integer::u128", "kind": "data"},
        ],
    },
    {
        "type": "event",
        "name": "moosh_id::escrow::Escrow::Event",
        "kind": "enum",
        "variants": [
            {
                "name": "EscrowCreated",
                "type": "moosh_id::escrow::Escrow::EscrowCreated",
                "kind": "nested",
            },
            {
                "name": "EscrowDeposited",
                "type": "moosh_id::escrow::Escrow::EscrowDeposited",
                "kind": "nested",
            },
            {
                "name": "EscrowClaimed",
                "type": "moosh_id::escrow::Escrow::EscrowClaimed",
                "kind": "nested",
            },
            {
                "name": "EscrowDisputed",
                "type": "moosh_id::escrow::Escrow::EscrowDisputed",
                "kind": "nested",
            },
        ],
    },
]
MSG_POINT = [
    5967,
    8532,
    7161,
    4312,
    8067,
    153,
    1395,
    8108,
    7450,
    4091,
    7909,
    8472,
    9960,
    486,
    4380,
    9291,
    9332,
    9069,
    5751,
    8392,
    11791,
    928,
    11542,
    779,
    5614,
    3694,
    10476,
    4454,
    11654,
    1115,
    5980,
    12032,
    8005,
    10666,
    6441,
    12133,
    10420,
    2247,
    1906,
    9883,
    3863,
    5489,
    5626,
    5083,
    3059,
    7405,
    2621,
    3760,
    11596,
    1729,
    6633,
    753,
    11380,
    11301,
    3551,
    2759,
    9805,
    1317,
    8184,
    10710,
    1724,
    7892,
    9868,
    4731,
    1712,
    7945,
    2993,
    5276,
    6892,
    3116,
    4442,
    10813,
    3229,
    6467,
    10156,
    2916,
    910,
    600,
    8287,
    2285,
    2612,
    6359,
    4389,
    5038,
    5880,
    3003,
    3036,
    11130,
    1194,
    7753,
    641,
    4126,
    6768,
    11507,
    11306,
    8675,
    765,
    531,
    11593,
    2049,
    9409,
    7405,
    12067,
    9078,
    12213,
    6507,
    1685,
    1177,
    962,
    3483,
    1695,
    7688,
    1338,
    4847,
    9969,
    11363,
    12267,
    7835,
    5226,
    202,
    2205,
    8977,
    8096,
    9396,
    8234,
    2238,
    7916,
    3414,
    7403,
    8580,
    2150,
    12197,
    8921,
    1670,
    10797,
    11249,
    5126,
    9946,
    3874,
    3496,
    9848,
    3882,
    4035,
    645,
    10746,
    10029,
    12008,
    6376,
    1452,
    9287,
    1968,
    8904,
    3710,
    12144,
    9778,
    2083,
    6559,
    188,
    3356,
    5009,
    4957,
    5735,
    11282,
    5552,
    7726,
    304,
    2375,
    5892,
    1155,
    8782,
    1909,
    8774,
    10885,
    9069,
    1997,
    763,
    4550,
    3229,
    4825,
    1588,
    9508,
    9346,
    6944,
    3714,
    4451,
    1151,
    744,
    345,
    2327,
    3710,
    6473,
    2529,
    9234,
    389,
    1348,
    6893,
    9607,
    1423,
    11163,
    9263,
    808,
    10502,
    8149,
    3164,
    3147,
    5019,
    7046,
    1754,
    1990,
    4503,
    3177,
    10299,
    405,
    11735,
    200,
    5650,
    3366,
    11587,
    1297,
    10817,
    10705,
    4799,
    530,
    10841,
    11694,
    11572,
    8927,
    4499,
    8558,
    10499,
    5402,
    985,
    9145,
    4355,
    3759,
    3950,
    8868,
    8316,
    12085,
    2744,
    1259,
    8809,
    6575,
    7862,
    8297,
    3708,
    593,
    2106,
    8445,
    5838,
    6286,
    2371,
    7026,
    3466,
    9051,
    10198,
    5620,
    3297,
    9808,
    1265,
    448,
    7955,
    9682,
    1984,
    2818,
    630,
    761,
    7308,
    5795,
    10820,
    3818,
    1155,
    9666,
    815,
    1742,
    10237,
    6627,
    7661,
    11987,
    10877,
    5134,
    11284,
    1061,
    2807,
    4736,
    3523,
    10696,
    8540,
    6764,
    5092,
    5001,
    65,
    1107,
    2290,
    9848,
    4653,
    8629,
    1954,
    5820,
    9488,
    7849,
    1099,
    1005,
    10182,
    420,
    4779,
    9832,
    2897,
    9273,
    8013,
    6628,
    5959,
    6589,
    8275,
    1215,
    8627,
    6243,
    12098,
    154,
    7855,
    8077,
    12230,
    8784,
    5155,
    3727,
    10780,
    5718,
    1209,
    1117,
    1253,
    2184,
    4779,
    715,
    5204,
    8253,
    10757,
    10775,
    7176,
    10571,
    2757,
    11691,
    5894,
    3320,
    9761,
    7336,
    6196,
    10156,
    10647,
    3626,
    9490,
    4872,
    9613,
    1348,
    169,
    9844,
    1829,
    1735,
    1609,
    2876,
    4466,
    6455,
    1896,
    9399,
    10368,
    7360,
    3570,
    8147,
    11588,
    668,
    2770,
    9442,
    7708,
    12143,
    11965,
    266,
    6268,
    6055,
    5042,
    8739,
    1434,
    10984,
    3131,
    2770,
    2836,
    9148,
    3453,
    2761,
    8348,
    7774,
    4751,
    11749,
    11245,
    4476,
    4370,
    2722,
    477,
    3762,
    3142,
    4610,
    238,
    5370,
    2387,
    977,
    10900,
    610,
    9208,
    11461,
    3112,
    6488,
    10039,
    10234,
    965,
    3737,
    8977,
    5071,
    8056,
    7795,
    12183,
    3404,
    6527,
    2005,
    8401,
    9674,
    11011,
    10390,
    2630,
    1888,
    32,
    10650,
    1034,
    9470,
    86,
    10834,
    952,
    3754,
    1484,
    997,
    4913,
    2169,
    9954,
    4705,
    8699,
    9915,
    2351,
    4272,
    5591,
    8652,
    903,
    3750,
    2393,
    6889,
    6195,
    1211,
    1974,
    1679,
    10503,
    4628,
    4209,
    544,
    9108,
    3433,
    8208,
    9397,
    230,
    1976,
    12253,
    253,
    6433,
    2582,
    1065,
    10458,
    1215,
    11029,
    6826,
    7661,
    10692,
    134,
    11062,
    161,
    8528,
    2798,
    6097,
    5974,
    2806,
    96,
    9946,
    1515,
    7417,
    1133,
    6048,
    2260,
    496,
    258,
    9187,
    8849,
    1914,
    3504,
    11106,
    3576,
    282,
    11449,
    5891,
    10069,
    2683,
    3933,
    10034,
    6622,
    5721,
    6744,
    2590,
    7952,
    7200,
]

# Contract ABIs
FALCON_KEY_REGISTRY_ABI = [
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

FALCON_VERIFIER_ABI = {
    "constructor": {
        "inputs": [
            {
                "name": "key_registry_addr",
                "type": "core::starknet::contract_address::ContractAddress",
            }
        ]
    },
    "interface": {"name": "IFalconSignatureVerifier", "type": "interface"},
    "functions": [
        {
            "name": "verify_signature_for_key_hash",
            "type": "function",
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
            "state_mutability": "external",
        }
    ],
    "events": [
        {
            "name": "VerificationSuccess",
            "type": "event",
            "inputs": [
                {"name": "key_hash", "type": "core::felt252"},
                {"name": "msg_hash_part", "type": "core::felt252"},
            ],
        },
        {
            "name": "VerificationFailed",
            "type": "event",
            "inputs": [
                {"name": "key_hash", "type": "core::felt252"},
                {"name": "msg_hash_part", "type": "core::felt252"},
                {"name": "reason", "type": "core::felt252"},
            ],
        },
    ],
}
